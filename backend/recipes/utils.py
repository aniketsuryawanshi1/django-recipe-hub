import uuid
from PIL import Image, ImageOps
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')

def resize_image(image_path, max_size=(800, 600), quality=85):
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img = ImageOps.exif_transpose(img)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            base_name = image_path.rsplit('.', 1)[0]
            new_path = f"{base_name}_resized.jpg"
            img.save(new_path, 'JPEG', quality=quality, optimize=True)
            logger.info(f"Image resized: {image_path} -> {new_path}")
            return new_path
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {str(e)}")
        return image_path

def generate_unique_filename(filename):
    ext = filename.split('.')[-1] if '.' in filename else 'jpg'
    return f"{uuid.uuid4()}.{ext}"

def validate_image(image):
    max_size = 10 * 1024 * 1024
    if image.size > max_size:
        raise ValueError("Image size cannot exceed 10MB")
    allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
    ext = image.name.lower().split('.')[-1] if '.' in image.name else ''
    if ext not in allowed_extensions:
        raise ValueError(f"Allowed image formats: {', '.join(allowed_extensions)}")
    try:
        with Image.open(image) as img:
            img.verify()
    except Exception:
        raise ValueError("Invalid image file")
    return True