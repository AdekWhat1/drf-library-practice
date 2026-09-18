from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from book.serializers import BookSerializer
from borrowing.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "is_active",
        )
        read_only_fields = ("id", "borrow_date", "actual_return_date", "user", "is_active")


class BorrowingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book_title",
            "user_email",
            "is_active",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date")

    def validate(self, attrs):
        data = super().validate(attrs)

        Borrowing.validate_dates(
            borrow_date=timezone.now().date(),
            expected_return_date=attrs["expected_return_date"],
            error_to_raise=serializers.ValidationError,
        )

        if attrs["book"].inventory < 1:
            raise serializers.ValidationError(
                {"book": "This book is currently out of stock."}
            )

        return data

    def create(self, validated_data):
        with transaction.atomic():
            book = validated_data["book"]
            book.inventory -= 1
            book.save()

            return super().create(validated_data)