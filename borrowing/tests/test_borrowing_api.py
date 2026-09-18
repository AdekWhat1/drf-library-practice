from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from book.models import Book
from borrowing.models import Borrowing

BORROWINGS_URL = reverse("borrowing:borrowing-list")


def detail_url(borrowing_id: int):
    return reverse("borrowing:borrowing-detail", args=[borrowing_id])


def return_url(borrowing_id: int):
    return reverse("borrowing:borrowing-return-borrowing", args=[borrowing_id])


def sample_book(**params):
    defaults = {
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "cover": Book.CoverType.HARD,
        "inventory": 5,
        "daily_fee": Decimal("2.00"),
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def sample_borrowing(user, book=None, **params):
    if book is None:
        book = sample_book()
    defaults = {
        "expected_return_date": timezone.now().date() + timedelta(days=7),
        "book": book,
        "user": user,
    }
    defaults.update(params)
    return Borrowing.objects.create(**defaults)


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(BORROWINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="password123",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

    def test_list_borrowings_limited_to_user(self):
        sample_borrowing(user=self.user)
        sample_borrowing(user=self.other_user)

        response = self.client.get(BORROWINGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user_email"], self.user.email)

    def test_create_borrowing_success_and_inventory_decreased(self):
        book = sample_book(inventory=3)
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=5),
        }

        response = self.client.post(BORROWINGS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        book.refresh_from_db()
        self.assertEqual(book.inventory, 2)

        borrowing = Borrowing.objects.get(id=response.data["id"])
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.book, book)

    def test_create_borrowing_out_of_stock_fails(self):
        book = sample_book(inventory=0)
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() + timedelta(days=5),
        }

        response = self.client.post(BORROWINGS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book", response.data)

    def test_create_borrowing_invalid_date_fails(self):
        book = sample_book(inventory=2)
        payload = {
            "book": book.id,
            "expected_return_date": timezone.now().date() - timedelta(days=1),
        }

        response = self.client.post(BORROWINGS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expected_return_date", response.data)

    def test_return_borrowing_success_and_inventory_restored(self):
        book = sample_book(inventory=2)
        borrowing = sample_borrowing(user=self.user, book=book)

        response = self.client.post(return_url(borrowing.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        borrowing.refresh_from_db()
        book.refresh_from_db()

        self.assertEqual(borrowing.actual_return_date, timezone.now().date())
        self.assertEqual(book.inventory, 3)

    def test_return_already_returned_borrowing_fails(self):
        borrowing = sample_borrowing(
            user=self.user,
            actual_return_date=timezone.now().date(),
        )

        response = self.client.post(return_url(borrowing.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_see_all_borrowings(self):
        sample_borrowing(user=self.admin)
        sample_borrowing(user=self.user)

        response = self.client.get(BORROWINGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_admin_filter_borrowings_by_user(self):
        b1 = sample_borrowing(user=self.admin)
        sample_borrowing(user=self.user)

        response = self.client.get(BORROWINGS_URL, {"user_id": self.admin.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], b1.id)

    def test_admin_filter_borrowings_by_is_active(self):
        active_borrowing = sample_borrowing(user=self.user)
        sample_borrowing(
            user=self.user,
            actual_return_date=timezone.now().date(),
        )

        response = self.client.get(BORROWINGS_URL, {"is_active": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], active_borrowing.id)