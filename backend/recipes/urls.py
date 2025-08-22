from django.urls import path
from .views import (
    CategoryListView, RecipeListView, RecipeDetailView,
    RecipeCreateView, RecipeUpdateView, RecipeDeleteView,
    MyRecipesView, RecipeImageUploadView, RatingCreateView,
    FavoriteToggleView, MyFavoritesView, FeaturedRecipesView,
    PopularRecipesView, recipe_stats
)

app_name = 'recipes'

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),
    
    # Recipes
    path('', RecipeListView.as_view(), name='recipe-list'),
    path('create/', RecipeCreateView.as_view(), name='recipe-create'),
    path('my-recipes/', MyRecipesView.as_view(), name='my-recipes'),
    path('featured/', FeaturedRecipesView.as_view(), name='featured-recipes'),
    path('popular/', PopularRecipesView.as_view(), name='popular-recipes'),
    path('stats/', recipe_stats, name='recipe-stats'),
    path('<uuid:id>/', RecipeDetailView.as_view(), name='recipe-detail'),
    path('<uuid:id>/update/', RecipeUpdateView.as_view(), name='recipe-update'),
    path('<uuid:id>/delete/', RecipeDeleteView.as_view(), name='recipe-delete'),
    
    # Recipe Images
    path('images/upload/', RecipeImageUploadView.as_view(), name='recipe-image-upload'),
    
    # Ratings
    path('ratings/create/', RatingCreateView.as_view(), name='rating-create'),
    
    # Favorites
    path('<uuid:recipe_id>/favorite/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('favorites/', MyFavoritesView.as_view(), name='my-favorites'),
]