from rest_framework import serializers
from payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
        )
        read_only_fields = fields


class PaymentListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(
        source="borrowing.book.title", read_only=True
    )
    user_email = serializers.CharField(
        source="borrowing.user.email", read_only=True
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "book_title",
            "user_email",
            "money_to_pay",
        )