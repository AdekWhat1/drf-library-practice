from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from book.models import Book
from borrowing.models import Borrowing
from payment.models import Payment

PAYMENTS_URL = reverse("payment:payment-list")


def detail_url(payment_id: int):
    return reverse("payment:payment-detail", args=[payment_id])


def sample_book():
    return Book.objects.create(
        title="Test Book",
        author="Author",
        cover=Book.CoverType.HARD,
        inventory=5,
        daily_fee=Decimal("2.00"),
    )


def sample_borrowing(user, book=None):
    if book is None:
        book = sample_book()
    return Borrowing.objects.create(
        expected_return_date=timezone.now().date() + timedelta(days=5),
        book=book,
        user=user,
    )


def sample_payment(borrowing, **params):
    defaults = {
        "status": Payment.Status.PENDING,
        "type": Payment.Type.PAYMENT,
        "borrowing": borrowing,
        "session_url": "https://checkout.stripe.com/pay/cs_test_123",
        "session_id": "cs_test_123",
        "money_to_pay": Decimal("10.00"),
    }
    defaults.update(params)
    return Payment.objects.create(**defaults)


class UnauthenticatedPaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(PAYMENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPaymentApiTests(TestCase):
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

    def test_list_payments_limited_to_user(self):
        borrowing_user = sample_borrowing(user=self.user)
        borrowing_other = sample_borrowing(user=self.other_user)

        sample_payment(borrowing=borrowing_user)
        sample_payment(borrowing=borrowing_other)

        response = self.client.get(PAYMENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user_email"], self.user.email)

    def test_retrieve_payment_detail(self):
        borrowing = sample_borrowing(user=self.user)
        payment = sample_payment(borrowing=borrowing)

        response = self.client.get(detail_url(payment.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_id"], payment.session_id)
        self.assertEqual(Decimal(response.data["money_to_pay"]), payment.money_to_pay)

    @patch("payment.views.send_telegram_message")
    @patch("stripe.checkout.Session.retrieve")
    def test_payment_success_endpoint_marks_as_paid(self, mock_stripe_retrieve, mock_send_telegram):
        borrowing = sample_borrowing(user=self.user)
        payment = sample_payment(borrowing=borrowing, session_id="test_session_id")

        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_stripe_retrieve.return_value = mock_session

        url = reverse("payment:payment-success")
        response = self.client.get(url, {"session_id": "test_session_id"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)
        mock_send_telegram.assert_called_once()

    def test_payment_cancel_endpoint(self):
        url = reverse("payment:payment-cancel")
        response = self.client.get(url, {"session_id": "test_session_id"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)