import django_filters
from django.db.models import Q
from .models import Recipe, Category

class RecipeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        empty_label="All Categories"
    )
    difficulty = django_filters.ChoiceFilter(choices=Recipe.DIFFICULTY_CHOICES)
    max_prep_time = django_filters.NumberFilter(field_name='prep_time', lookup_expr='lte')
    max_cook_time = django_filters.NumberFilter(field_name='cook_time', lookup_expr='lte')
    max_total_time = django_filters.NumberFilter(method='filter_max_total_time')
    servings = django_filters.NumberFilter()
    min_servings = django_filters.NumberFilter(field_name='servings', lookup_expr='gte')
    max_servings = django_filters.NumberFilter(field_name='servings', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(method='filter_min_rating')
    author = django_filters.CharFilter(field_name='author__username', lookup_expr='icontains')
    featured = django_filters.BooleanFilter(field_name='is_featured')
    tags = django_filters.CharFilter(method='filter_tags')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Recipe
        fields = {
            'title': ['icontains'],
            'prep_time': ['lte', 'gte'],
            'cook_time': ['lte', 'gte'],
            'servings': ['exact', 'lte', 'gte'],
            'difficulty': ['exact'],
        }
    
    def filter_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(ingredients__icontains=value) |
                Q(instructions__icontains=value) |
                Q(author__username__icontains=value)
            )
        return queryset
    
    def filter_max_total_time(self, queryset, name, value):
        if value:
            return queryset.extra(
                where=["prep_time + cook_time <= %s"],
                params=[value]
            )
        return queryset
    
    def filter_min_rating(self, queryset, name, value):
        if value:
            return queryset.filter(ratings__rating__gte=value).distinct()
        return queryset
    
    def filter_tags(self, queryset, name, value):
        if value:
            tag_names = [tag.strip().lower() for tag in value.split(',')]
            return queryset.filter(
                recipe_tags__tag__name__in=tag_names
            ).distinct()
        return queryset