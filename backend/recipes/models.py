from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image
import uuid
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# ---------------------------
# Custom QuerySets for N+1 optimization
# ---------------------------

class RecipeQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("author", "category") \
                   .prefetch_related("images", "ratings", "recipe_tags__tag", "favorited_by")

class RatingQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("user", "recipe", "recipe__author")

class FavoriteQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("user", "recipe", "recipe__author")

class RecipeViewQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("recipe", "user")

# ---------------------------
# Models
# ---------------------------

class Category(models.Model):
    """Recipe categories (e.g., Italian, Indian, Desserts, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True, max_length=500)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate category data"""
        super().clean()
        if self.name:
            self.name = self.name.strip().title()
            if len(self.name) < 2:
                raise ValidationError({'name': 'Category name must be at least 2 characters long.'})

class Recipe(models.Model):
    """Main recipe model"""
    DIFFICULTY_CHOICES = [
        ('easy', _('Easy')),
        ('medium', _('Medium')),
        ('hard', _('Hard')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(max_length=2000)
    ingredients = models.TextField(help_text="List ingredients, one per line")
    instructions = models.TextField(help_text="Step-by-step cooking instructions")
    
    # Recipe details
    prep_time = models.PositiveIntegerField(help_text="Preparation time in minutes")
    cook_time = models.PositiveIntegerField(help_text="Cooking time in minutes")
    servings = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    
    # Relationships
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='recipes',
        limit_choices_to={'role': 'seller'}
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='recipes'
    )
    
    # Status and metrics
    is_published = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    objects = RecipeQuerySet.as_manager()
    
    class Meta:
        verbose_name = _('Recipe')
        verbose_name_plural = _('Recipes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['is_published']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['view_count']),
            models.Index(fields=['created_at']),
            models.Index(fields=['author', 'is_published']),
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['is_featured', 'is_published']),
        ]
    
    def __str__(self):
        return self.title
    
    def clean(self):
        """Validate recipe data"""
        super().clean()
        
        # Validate author is a seller
        if self.author and not self.author.is_seller:
            raise ValidationError({'author': 'Only sellers can create recipes.'})
        
        # Validate times
        if self.prep_time and self.prep_time < 0:
            raise ValidationError({'prep_time': 'Preparation time cannot be negative.'})
        if self.cook_time and self.cook_time < 0:
            raise ValidationError({'cook_time': 'Cooking time cannot be negative.'})
        
        # Clean text fields
        if self.title:
            self.title = self.title.strip()
        if self.description:
            self.description = self.description.strip()
        if self.ingredients:
            self.ingredients = self.ingredients.strip()
        if self.instructions:
            self.instructions = self.instructions.strip()
    
    def save(self, *args, **kwargs):
        """Override save to include validation"""
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving recipe {self.title}: {str(e)}")
            raise
    
    @property
    def total_time(self):
        """Calculate total cooking time"""
        return self.prep_time + self.cook_time
    
    @property
    def average_rating(self):
        """Calculate average rating"""
        try:
            ratings = self.ratings.all()
            if ratings.exists():
                return round(ratings.aggregate(models.Avg('rating'))['rating__avg'], 2)
            return 0
        except Exception as e:
            logger.error(f"Error calculating average rating for recipe {self.id}: {str(e)}")
            return 0
    
    @property
    def rating_count(self):
        """Get total number of ratings"""
        try:
            return self.ratings.count()
        except Exception as e:
            logger.error(f"Error getting rating count for recipe {self.id}: {str(e)}")
            return 0
    
    def increment_view_count(self):
        """Increment view count"""
        try:
            self.view_count = models.F('view_count') + 1
            self.save(update_fields=['view_count'])
        except Exception as e:
            logger.error(f"Error incrementing view count for recipe {self.id}: {str(e)}")

class RecipeImage(models.Model):
    """Recipe images model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='recipes/images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Recipe Image')
        verbose_name_plural = _('Recipe Images')
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['recipe']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"Image for {self.recipe.title}"
    
    def clean(self):
        """Validate image data"""
        super().clean()
        
        # Ensure only one primary image per recipe
        if self.is_primary:
            existing_primary = RecipeImage.objects.filter(
                recipe=self.recipe, is_primary=True
            ).exclude(pk=self.pk)
            
            if existing_primary.exists():
                # Remove primary status from other images
                existing_primary.update(is_primary=False)
    
    def save(self, *args, **kwargs):
        """Override save to process image"""
        try:
            self.full_clean()
            super().save(*args, **kwargs)
            
            # Process image asynchronously after saving
            if self.image:
                from .tasks import process_recipe_image
                process_recipe_image.delay(self.id)
                
        except Exception as e:
            logger.error(f"Error saving recipe image: {str(e)}")
            raise

class Rating(models.Model):
    """Recipe ratings model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review = models.TextField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = RatingQuerySet.as_manager()
    
    class Meta:
        verbose_name = _('Rating')
        verbose_name_plural = _('Ratings')
        ordering = ['-created_at']
        unique_together = ['recipe', 'user']  # One rating per user per recipe
        indexes = [
            models.Index(fields=['recipe']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
            models.Index(fields=['recipe', 'rating']),
        ]
    
    def __str__(self):
        return f"{self.user.username} rated {self.recipe.title} - {self.rating} stars"
    
    def clean(self):
        """Validate rating data"""
        super().clean()
        
        # Prevent self-rating
        if self.recipe.author == self.user:
            raise ValidationError({'user': 'You cannot rate your own recipe.'})
        
        # Clean review text
        if self.review:
            self.review = self.review.strip()
    
    def save(self, *args, **kwargs):
        """Override save to include validation"""
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving rating: {str(e)}")
            raise

class Favorite(models.Model):
    """User favorite recipes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = FavoriteQuerySet.as_manager()
    
    class Meta:
        verbose_name = _('Favorite')
        verbose_name_plural = _('Favorites')
        ordering = ['-created_at']
        unique_together = ['user', 'recipe']  # One favorite per user per recipe
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['recipe']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} favorited {self.recipe.title}"

class RecipeView(models.Model):
    """Track recipe views for analytics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_views')
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='recipe_views'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = RecipeViewQuerySet.as_manager()
    
    class Meta:
        verbose_name = _('Recipe View')
        verbose_name_plural = _('Recipe Views')
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['recipe']),
            models.Index(fields=['user']),
            models.Index(fields=['viewed_at']),
            models.Index(fields=['recipe', 'viewed_at']),
        ]
    
    def __str__(self):
        user_info = self.user.username if self.user else f"Anonymous ({self.ip_address})"
        return f"{user_info} viewed {self.recipe.title}"

class Tag(models.Model):
    """Tags for recipes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Clean tag name"""
        super().clean()
        if self.name:
            self.name = self.name.strip().lower()

class RecipeTag(models.Model):
    """Many-to-many relationship between recipes and tags"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='recipe_tags')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['recipe', 'tag']
        indexes = [
            models.Index(fields=['recipe']),
            models.Index(fields=['tag']),
        ]
    
    def __str__(self):
        return f"{self.recipe.title} - {self.tag.name}"