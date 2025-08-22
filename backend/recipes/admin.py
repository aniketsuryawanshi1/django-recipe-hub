from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Avg, Count
from .models import (
    Category, Recipe, RecipeImage, Rating, 
    Favorite, RecipeView, Tag, RecipeTag
)
import logging

logger = logging.getLogger(__name__)

class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 1
    readonly_fields = ('created_at',)

class RecipeTagInline(admin.TabularInline):
    model = RecipeTag
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    
    def recipe_count(self, obj):
        return obj.recipes.count()
    recipe_count.short_description = 'Recipes'

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'difficulty', 
        'total_time', 'average_rating', 'view_count',
        'is_published', 'is_featured', 'created_at'
    )
    list_filter = (
        'difficulty', 'is_published', 'is_featured', 
        'category', 'created_at', 'author__role'
    )
    search_fields = ('title', 'description', 'author__email', 'author__username')
    readonly_fields = ('id', 'view_count', 'average_rating', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [RecipeImageInline, RecipeTagInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'author', 'category')
        }),
        ('Recipe Details', {
            'fields': ('ingredients', 'instructions', 'prep_time', 'cook_time', 'servings', 'difficulty')
        }),
        ('Status', {
            'fields': ('is_published', 'is_featured', 'view_count', 'average_rating')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'author', 'category'
        ).annotate(
            avg_rating=Avg('ratings__rating')
        )
    
    def average_rating(self, obj):
        return obj.average_rating or 0
    average_rating.short_description = 'Avg Rating'
    
    def total_time(self, obj):
        return f"{obj.total_time} min"
    total_time.short_description = 'Total Time'

@admin.register(RecipeImage)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'caption', 'is_primary', 'order', 'image_preview', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('recipe__title', 'caption')
    readonly_fields = ('id', 'image_preview', 'created_at')
    ordering = ('recipe', 'order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating', 'has_review', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('recipe__title', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def has_review(self, obj):
        return bool(obj.review)
    has_review.boolean = True
    has_review.short_description = 'Has Review'

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'recipe__title')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)

@admin.register(RecipeView)
class RecipeViewAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user_display', 'ip_address', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('recipe__title', 'user__email', 'ip_address')
    readonly_fields = ('id', 'viewed_at')
    ordering = ('-viewed_at',)
    
    def user_display(self, obj):
        return obj.user.username if obj.user else 'Anonymous'
    user_display.short_description = 'User'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'recipe_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at')
    ordering = ('name',)
    
    def recipe_count(self, obj):
        return obj.recipe_tags.count()
    recipe_count.short_description = 'Recipes'