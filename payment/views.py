import stripe
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.telegram_bot import send_telegram_message
from payment.models import Payment
from payment.serializers import PaymentListSerializer, PaymentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Payment.objects.all().select_related(
        "borrowing__book", "borrowing__user"
    )
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(borrowing__user=user)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        return PaymentSerializer

    @extend_schema(
        summary="Handle successful Stripe payment callback",
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=OpenApiTypes.STR,
                description="Stripe checkout session ID (cs_test_...)",
                required=True,
            )
        ],
        responses={
            200: OpenApiResponse(description="Payment verified and marked as PAID."),
            400: OpenApiResponse(
                description="Missing session_id or payment not completed."
            ),
            404: OpenApiResponse(description="Payment record not found."),
        },
    )
    @action(methods=["GET"], detail=False, url_path="success")
    def success(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"error": "Missing session_id query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payment.objects.get(session_id=session_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment with this session_id not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            payment.status = Payment.Status.PAID
            payment.save()

            message = (
                f"💳 <b>Payment Successful!</b>\n\n"
                f"• <b>Payment ID:</b> #{payment.id}\n"
                f"• <b>Amount:</b> ${payment.money_to_pay}\n"
                f"• <b>User:</b> {payment.borrowing.user.email}\n"
                f"• <b>Book:</b> {payment.borrowing.book.title}"
            )
            send_telegram_message(message)

            return Response(
                {"message": f"Payment #{payment.id} was successfully processed!"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "Payment has not been completed yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(methods=["GET"], detail=False, url_path="cancel")
    def cancel(self, request):
        return Response(
            {
                "message": (
                    "Payment was cancelled. You can complete the payment within 24 hours "
                    "using the link from your payment details."
                )
            },
            status=status.HTTP_200_OK,
        )
