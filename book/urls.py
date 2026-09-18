from django.urls import include, path
from rest_framework.routers import DefaultRouter

from book.views import BookViewSet

router = DefaultRouter()
router.register("", BookViewSet, basename="book")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "book"