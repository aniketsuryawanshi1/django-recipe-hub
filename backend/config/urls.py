"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        "status": "healthy",
        "message": "API is running",
        "version": getattr(settings, 'API_VERSION', 'v1')
    })

@require_http_methods(["GET"])
def api_info(request):
    """API information endpoint"""
    return JsonResponse({
        "api_name": "Recipe API",
        "version": getattr(settings, 'API_VERSION', 'v1'),
        "endpoints": {
            "authentication": "/auth/",
            "health": "/health/",
            "admin": f"/{getattr(settings, 'ADMIN_URL', 'admin')}/",
        },
        "documentation": "Add your API documentation URL here",
    })

urlpatterns = [
    # Admin interface
    path(getattr(settings, 'ADMIN_URL', 'admin/'), admin.site.urls),
    
    # API endpoints
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/recipes/', include('recipes.urls')),
    
    # Health check and info endpoints
    path('health/', health_check, name='health_check'),
    path('api/', api_info, name='api_info'),
    path('', api_info, name='root'),  # Root URL shows API info
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar if available
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

# Custom error handlers
def custom_404_view(request, exception=None):
    """Custom 404 error handler"""
    return JsonResponse({
        "error": "Not Found",
        "message": "The requested resource was not found.",
        "status_code": 404
    }, status=404)

def custom_500_view(request):
    """Custom 500 error handler"""
    logger.error(f"Internal server error: {request.path}")
    return JsonResponse({
        "error": "Internal Server Error",
        "message": "An internal server error occurred. Please try again later.",
        "status_code": 500
    }, status=500)

# Set custom error handlers
handler404 = custom_404_view
handler500 = custom_500_view