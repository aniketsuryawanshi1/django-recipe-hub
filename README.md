# django-recipe-hub

Django REST Framework backend for a recipe-sharing hub with Customers & Sellers. Features JWT authentication, recipe uploads, ratings, Celery for async tasks, scheduled jobs, PostgreSQL, and local file storage. Clean, scalable, and assignment-ready implementation.

## API Endpoints

### Authentication

- `POST   /api/v1/auth/register/` — Register a new user
- `POST   /api/v1/auth/login/` — Obtain JWT token
- `POST   /api/v1/auth/logout/` — Logout (blacklist token)
- `POST   /api/v1/auth/token/refresh/` — Refresh JWT token
- `GET    /api/v1/auth/profile/` — Get current user profile
- `PUT    /api/v1/auth/profile/update/` — Update user profile

### Recipes

- `GET    /api/v1/recipes/` — List/search recipes
- `POST   /api/v1/recipes/create/` — Create a new recipe (Seller only)
- `GET    /api/v1/recipes/my-recipes/` — List my recipes (Seller only)
- `GET    /api/v1/recipes/featured/` — List featured recipes
- `GET    /api/v1/recipes/popular/` — List popular recipes
- `GET    /api/v1/recipes/stats/` — Recipe statistics
- `GET    /api/v1/recipes/categories/` — List categories
- `GET    /api/v1/recipes/<uuid:id>/` — Retrieve recipe details
- `PUT    /api/v1/recipes/<uuid:id>/update/` — Update recipe (Seller only)
- `DELETE /api/v1/recipes/<uuid:id>/delete/` — Delete recipe (Seller only)

### Recipe Images

- `POST   /api/v1/recipes/images/upload/` — Upload recipe image (Seller only)

### Ratings

- `POST   /api/v1/recipes/ratings/create/` — Rate a recipe (Customer only)

### Favorites

- `POST   /api/v1/recipes/<uuid:recipe_id>/favorite/` — Toggle favorite (Customer only)
- `GET    /api/v1/recipes/favorites/` — List my favorites

### Health & Info

- `GET    /health/` — Health check
- `GET    /api/` — API info

### Admin

- `/admin/` — Django admin (or as set in your `.env`)

---

## Setup

1. **Clone the repository**
2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
3. **Configure environment variables**
   - Copy `.env.example` to `.env` and fill in your secrets (see `.env` in this repo)
4. **Apply migrations**
   ```
   python manage.py migrate
   ```
5. **Create a superuser**
   ```
   python manage.py createsuperuser
   ```
6. **Run the development server**
   ```
   python manage.py runserver
   ```
7. **Start Celery worker and beat**
   ```
   celery -A config worker -l info
   celery -A config beat -l info
   ```

## Technologies

- Django 5.x
- Django REST Framework
- PostgreSQL
- Celery + Redis
- Pillow (image processing)
- JWT Authentication

## Notes

- Ensure Redis and PostgreSQL are running.
- Do **not** commit your `.env` file to version control.
- For production, set `DEBUG=False` and configure allowed hosts and secure settings.

## License

MIT
