from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from book.models import Book
from book.serializers import BookSerializer, BookListSerializer

BOOKS_URL = reverse("book:book-list")


def detail_url(book_id: int):
    return reverse("book:book-detail", args=[book_id])


def sample_book(**params):
    defaults = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "cover": Book.CoverType.HARD,
        "inventory": 10,
        "daily_fee": Decimal("1.50"),
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


class UnauthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_books_allowed(self):
        sample_book()
        sample_book(title="Refactoring")

        response = self.client.get(BOOKS_URL)
        books = Book.objects.all().order_by("title")
        serializer = BookListSerializer(books, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_retrieve_book_detail_allowed(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.get(url)
        serializer = BookSerializer(book)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_book_forbidden(self):
        payload = {
            "title": "Unauthorized Book",
            "author": "Unknown",
            "cover": Book.CoverType.SOFT,
            "inventory": 5,
            "daily_fee": Decimal("0.99"),
        }
        response = self.client.post(BOOKS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRegularUserBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

    def test_create_book_forbidden(self):
        payload = {
            "title": "User Created Book",
            "author": "Test Author",
            "cover": Book.CoverType.HARD,
            "inventory": 3,
            "daily_fee": Decimal("2.00"),
        }
        response = self.client.post(BOOKS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.admin)

    def test_create_book_success(self):
        payload = {
            "title": "Domain-Driven Design",
            "author": "Eric Evans",
            "cover": Book.CoverType.HARD,
            "inventory": 7,
            "daily_fee": "3.50",
        }
        response = self.client.post(BOOKS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(id=response.data["id"])
        for key in payload:
            if key == "daily_fee":
                self.assertEqual(getattr(book, key), Decimal(payload[key]))
            else:
                self.assertEqual(getattr(book, key), payload[key])

    def test_update_book(self):
        book = sample_book()
        payload = {"title": "Updated Title"}
        url = detail_url(book.id)

        response = self.client.patch(url, payload)
        book.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(book.title, payload["title"])

    def test_delete_book(self):
        book = sample_book()
        url = detail_url(book.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())