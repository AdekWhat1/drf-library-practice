from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from book.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )

    class Meta:
        ordering = ["-borrow_date"]

    @property
    def is_active(self) -> bool:
        return self.actual_return_date is None

    @staticmethod
    def validate_dates(borrow_date, expected_return_date, error_to_raise):
        if expected_return_date < borrow_date:
            raise error_to_raise(
                {"expected_return_date": "Expected return date cannot be in the past."}
            )

    def clean(self):
        Borrowing.validate_dates(
            borrow_date=self.borrow_date or timezone.now().date(),
            expected_return_date=self.expected_return_date,
            error_to_raise=ValidationError,
        )

    def __str__(self):
        return (
            f"{self.user.email} borrowed {self.book.title} on {self.borrow_date} "
            f"(expected: {self.expected_return_date})"
        )