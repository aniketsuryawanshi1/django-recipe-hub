from rest_framework import serializers
from django.db import transaction
from .models import (
    Category, Recipe, RecipeImage, Rating, 
    Favorite, Tag, RecipeTag
)
from authentication.serializers import UserSerializer
import logging

logger = logging.getLogger(__name__)

class CategorySerializer(serializers.ModelSerializer):
    recipe_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image', 'is_active', 'recipe_count', 'created_at']
        read_only_fields = ['id', 'recipe_count', 'created_at']
    
    def get_recipe_count(self, obj):
        return obj.recipes.filter(is_published=True).count()

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']
        read_only_fields = ['id']

class RecipeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeImage
        fields = ['id', 'image', 'caption', 'is_primary', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']

class RatingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'user', 'rating', 'review', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class RecipeListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    total_time = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'author', 'category',
            'prep_time', 'cook_time', 'total_time', 'servings', 
            'difficulty', 'primary_image', 'average_rating', 
            'rating_count', 'view_count', 'is_published', 
            'is_featured', 'is_favorited', 'tags', 'created_at'
        ]
        read_only_fields = ['id', 'view_count', 'created_at']
    
    def get_primary_image(self, obj):
        try:
            primary_image = obj.images.filter(is_primary=True).first()
            if primary_image:
                return RecipeImageSerializer(primary_image).data
            return None
        except Exception as e:
            logger.error(f"Error getting primary image for recipe {obj.id}: {str(e)}")
            return None
    
    def get_average_rating(self, obj):
        return obj.average_rating
    
    def get_rating_count(self, obj):
        return obj.rating_count
    
    def get_total_time(self, obj):
        return obj.total_time
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False
    
    def get_tags(self, obj):
        try:
            tags = [rt.tag for rt in obj.recipe_tags.select_related('tag')]
            return TagSerializer(tags, many=True).data
        except Exception as e:
            logger.error(f"Error getting tags for recipe {obj.id}: {str(e)}")
            return []

class RecipeDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = RecipeImageSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    total_time = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'ingredients', 'instructions',
            'prep_time', 'cook_time', 'total_time', 'servings', 
            'difficulty', 'author', 'category', 'images', 'ratings',
            'average_rating', 'rating_count', 'user_rating', 'view_count',
            'is_published', 'is_featured', 'is_favorited', 'tags',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'view_count', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        return obj.average_rating
    
    def get_rating_count(self, obj):
        return obj.rating_count
    
    def get_total_time(self, obj):
        return obj.total_time
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False
    
    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rating = obj.ratings.get(user=request.user)
                return RatingSerializer(rating).data
            except Rating.DoesNotExist:
                return None
        return None
    
    def get_tags(self, obj):
        try:
            tags = [rt.tag for rt in obj.recipe_tags.select_related('tag')]
            return TagSerializer(tags, many=True).data
        except Exception as e:
            logger.error(f"Error getting tags for recipe {obj.id}: {str(e)}")
            return []

class RecipeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        write_only=True
    )
    
    class Meta:
        model = Recipe
        fields = [
            'title', 'description', 'ingredients', 'instructions',
            'prep_time', 'cook_time', 'servings', 'difficulty',
            'category', 'is_published', 'is_featured', 'tags'
        ]
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value.strip()
    
    def validate_prep_time(self, value):
        if value < 0:
            raise serializers.ValidationError("Preparation time cannot be negative.")
        return value
    
    def validate_cook_time(self, value):
        if value < 0:
            raise serializers.ValidationError("Cooking time cannot be negative.")
        return value
    
    def validate_servings(self, value):
        if value < 1:
            raise serializers.ValidationError("Servings must be at least 1.")
        return value
    
    def create(self, validated_data):
        try:
            tags_data = validated_data.pop('tags', [])
            with transaction.atomic():
                validated_data['author'] = self.context['request'].user
                recipe = Recipe.objects.create(**validated_data)
                for tag_name in tags_data:
                    tag_name = tag_name.strip().lower()
                    if tag_name:
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        RecipeTag.objects.get_or_create(recipe=recipe, tag=tag)
                logger.info(f"Recipe created: {recipe.title} by {recipe.author.email}")
                return recipe
        except Exception as e:
            logger.error(f"Error creating recipe: {str(e)}")
            raise serializers.ValidationError("Failed to create recipe. Please try again.")

class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeListSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'recipe', 'created_at']
        read_only_fields = ['id', 'created_at']