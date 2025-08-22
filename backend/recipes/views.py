from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from authentication.permissions import IsSellerUser, IsOwnerOrReadOnly
from authentication.throttling import CustomerRateThrottle, SellerRateThrottle
from .models import (
    Category, Recipe,  Rating, 
    Favorite, RecipeView, 
)
from .serializers import (
    CategorySerializer, RecipeListSerializer, RecipeDetailSerializer,
    RecipeCreateSerializer, RecipeImageSerializer, RatingSerializer,
    FavoriteSerializer
)
from .filters import RecipeFilter
from .utils import get_client_ip, get_user_agent, validate_image
import logging

logger = logging.getLogger(__name__)

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class RecipeListView(generics.ListAPIView):
    serializer_class = RecipeListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RecipeFilter
    search_fields = ['title', 'description', 'ingredients']
    ordering_fields = ['created_at', 'view_count', 'title']
    ordering = ['-created_at']
    throttle_classes = [CustomerRateThrottle]
    
    def get_queryset(self):
        return Recipe.objects.filter(is_published=True).with_related()

class RecipeDetailView(generics.RetrieveAPIView):
    serializer_class = RecipeDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'
    throttle_classes = [CustomerRateThrottle]
    
    def get_queryset(self):
        return Recipe.objects.filter(is_published=True).with_related()
    
    def retrieve(self, request, *args, **kwargs):
        try:
            recipe = self.get_object()
            self.track_recipe_view(request, recipe)
            recipe.increment_view_count()
            serializer = self.get_serializer(recipe)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving recipe: {str(e)}")
            return Response(
                {"error": "Recipe not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def track_recipe_view(self, request, recipe):
        try:
            RecipeView.objects.create(
                recipe=recipe,
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)
            )
        except Exception as e:
            logger.error(f"Error tracking recipe view: {str(e)}")

class RecipeCreateView(generics.CreateAPIView):
    serializer_class = RecipeCreateSerializer
    permission_classes = [IsAuthenticated, IsSellerUser]
    throttle_classes = [SellerRateThrottle]
    
    def perform_create(self, serializer):
        serializer.save()

class RecipeUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = RecipeCreateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'id'
    throttle_classes = [SellerRateThrottle]
    
    def get_queryset(self):
        return Recipe.objects.filter(author=self.request.user)

class RecipeDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'id'
    throttle_classes = [SellerRateThrottle]
    
    def get_queryset(self):
        return Recipe.objects.filter(author=self.request.user)

class MyRecipesView(generics.ListAPIView):
    serializer_class = RecipeListSerializer
    permission_classes = [IsAuthenticated, IsSellerUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'view_count', 'title']
    ordering = ['-created_at']
    throttle_classes = [SellerRateThrottle]
    
    def get_queryset(self):
        return Recipe.objects.filter(author=self.request.user).with_related()

class RecipeImageUploadView(generics.CreateAPIView):
    serializer_class = RecipeImageSerializer
    permission_classes = [IsAuthenticated, IsSellerUser]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [SellerRateThrottle]
    
    def create(self, request, *args, **kwargs):
        try:
            recipe_id = request.data.get('recipe_id')
            image_file = request.FILES.get('image')
            if not recipe_id:
                return Response(
                    {"error": "recipe_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not image_file:
                return Response(
                    {"error": "image file is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                validate_image(image_file)
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                recipe = Recipe.objects.get(id=recipe_id, author=request.user)
            except Recipe.DoesNotExist:
                return Response(
                    {"error": "Recipe not found or not owned by user"},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            recipe_image = serializer.save(recipe=recipe)
            from .tasks import process_recipe_image
            process_recipe_image.delay(str(recipe_image.id))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error uploading recipe image: {str(e)}")
            return Response(
                {"error": "Failed to upload image"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RatingCreateView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle]
    
    def create(self, request, *args, **kwargs):
        try:
            recipe_id = request.data.get('recipe_id')
            if not recipe_id:
                return Response(
                    {"error": "recipe_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                recipe = Recipe.objects.get(id=recipe_id, is_published=True)
            except Recipe.DoesNotExist:
                return Response(
                    {"error": "Recipe not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            if recipe.author == request.user:
                return Response(
                    {"error": "You cannot rate your own recipe"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rating, created = Rating.objects.update_or_create(
                recipe=recipe,
                user=request.user,
                defaults={
                    'rating': serializer.validated_data['rating'],
                    'review': serializer.validated_data.get('review', '')
                }
            )
            response_serializer = RatingSerializer(rating)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            if created:
                logger.info(f"Rating created for recipe {recipe.id} by {request.user.email}")
            else:
                logger.info(f"Rating updated for recipe {recipe.id} by {request.user.email}")
            return Response(response_serializer.data, status=status_code)
        except Exception as e:
            logger.error(f"Error creating/updating rating: {str(e)}")
            return Response(
                {"error": "Failed to save rating"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FavoriteToggleView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle]
    
    def post(self, request, recipe_id):
        try:
            recipe = Recipe.objects.get(id=recipe_id, is_published=True)
            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )
            if not created:
                favorite.delete()
                return Response({
                    "message": "Recipe removed from favorites",
                    "is_favorited": False
                })
            else:
                return Response({
                    "message": "Recipe added to favorites",
                    "is_favorited": True
                })
        except Recipe.DoesNotExist:
            return Response(
                {"error": "Recipe not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error toggling favorite: {str(e)}")
            return Response(
                {"error": "Failed to update favorite status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MyFavoritesView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle]
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            'recipe', 'recipe__author', 'recipe__category'
        ).prefetch_related('recipe__images')

class FeaturedRecipesView(generics.ListAPIView):
    serializer_class = RecipeListSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(cache_page(60 * 30))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return Recipe.objects.filter(
            is_published=True, 
            is_featured=True
        ).with_related()[:10]

class PopularRecipesView(generics.ListAPIView):
    serializer_class = RecipeListSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return Recipe.objects.filter(is_published=True).annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings')
        ).order_by('-view_count', '-avg_rating')[:20]

@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_stats(request):
    try:
        cache_key = 'recipe_stats'
        stats = cache.get(cache_key)
        if not stats:
            stats = {
                'total_recipes': Recipe.objects.filter(is_published=True).count(),
                'total_categories': Category.objects.filter(is_active=True).count(),
                'total_ratings': Rating.objects.count(),
                'featured_recipes': Recipe.objects.filter(is_published=True, is_featured=True).count(),
            }
            cache.set(cache_key, stats, 60 * 30)
        return Response(stats)
    except Exception as e:
        logger.error(f"Error getting recipe stats: {str(e)}")
        return Response(
            {"error": "Failed to get statistics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )