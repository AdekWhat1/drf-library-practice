from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.telegram_bot import send_telegram_message
from borrowing.models import Borrowing
from borrowing.serializers import (
    BorrowingCreateSerializer,
    BorrowingListSerializer,
    BorrowingSerializer,
)
from payment.models import Payment
from payment.stripe_helper import create_stripe_checkout_session


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            description="Filter borrowings by active status (true: not returned yet, false: returned)",
            required=False,
        ),
        OpenApiParameter(
            name="user_id",
            type=OpenApiTypes.INT,
            description="Filter borrowings by user ID (admin only)",
            required=False,
        ),
    ]
)
class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.all().select_related("book", "user")
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        user_id = self.request.query_params.get("user_id")
        if user.is_staff and user_id:
            queryset = queryset.filter(user_id=user_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        borrowing = serializer.save(user=self.request.user)

        payment = create_stripe_checkout_session(borrowing, self.request)

        message = (
            f"📚 <b>New Borrowing Created!</b>\n\n"
            f"• <b>User:</b> {borrowing.user.email}\n"
            f"• <b>Book:</b> {borrowing.book.title}\n"
            f"• <b>Borrow Date:</b> {borrowing.borrow_date}\n"
            f"• <b>Expected Return:</b> {borrowing.expected_return_date}\n"
            f"• <b>Amount to pay:</b> ${payment.money_to_pay}\n"
            f'• <b>Payment Link:</b> <a href="{payment.session_url}">Pay here</a>'
        )
        send_telegram_message(message)

    @extend_schema(
        summary="Return a borrowed book",
        description=(
            "Marks the book as returned, restores inventory stock, "
            "and creates a fine payment session if returned after the expected date."
        ),
        responses={
            200: OpenApiResponse(
                description="Book returned successfully (or fine generated)."
            ),
            400: OpenApiResponse(description="Book has already been returned."),
        },
    )
    @action(methods=["POST"], detail=True, url_path="return")
    @action(methods=["POST"], detail=True, url_path="return")
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"error": "This book has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            borrowing.actual_return_date = timezone.now().date()
            borrowing.save()

            book = borrowing.book
            book.inventory += 1
            book.save()

            if borrowing.actual_return_date > borrowing.expected_return_date:
                fine_payment = create_stripe_checkout_session(
                    borrowing=borrowing,
                    request=request,
                    payment_type=Payment.Type.FINE,
                )

                message = (
                    f"⚠️ <b>Book Returned Late! Fine Required!</b>\n\n"
                    f"• <b>User:</b> {borrowing.user.email}\n"
                    f"• <b>Book:</b> {borrowing.book.title}\n"
                    f"• <b>Expected Return:</b> {borrowing.expected_return_date}\n"
                    f"• <b>Actual Return:</b> {borrowing.actual_return_date}\n"
                    f"• <b>Fine Amount:</b> ${fine_payment.money_to_pay}\n"
                    f'• <b>Pay Fine:</b> <a href="{fine_payment.session_url}">Pay here</a>'
                )
                send_telegram_message(message)

                return Response(
                    {
                        "message": "Book returned with overdue. Fine payment created.",
                        "fine_payment_url": fine_payment.session_url,
                        "fine_amount": fine_payment.money_to_pay,
                    },
                    status=status.HTTP_200_OK,
                )

            message = (
                f"📖 <b>Book Successfully Returned!</b>\n\n"
                f"• <b>User:</b> {borrowing.user.email}\n"
                f"• <b>Book:</b> {borrowing.book.title}\n"
                f"• <b>Return Date:</b> {borrowing.actual_return_date}"
            )
            send_telegram_message(message)

            return Response(
                {"message": "Book successfully returned on time."},
                status=status.HTTP_200_OK,
            )
