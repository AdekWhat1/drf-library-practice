from decimal import Decimal
import stripe
from django.conf import settings
from django.urls import reverse

from borrowing.models import Borrowing
from payment.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

FINE_MULTIPLIER = 2


def calculate_borrowing_price(borrowing: Borrowing) -> Decimal:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    total_days = max(days, 1)
    return Decimal(total_days) * borrowing.book.daily_fee


def calculate_fine_price(borrowing: Borrowing) -> Decimal:
    if (
        not borrowing.actual_return_date
        or borrowing.actual_return_date <= borrowing.expected_return_date
    ):
        return Decimal("0.00")

    overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
    return Decimal(overdue_days) * borrowing.book.daily_fee * FINE_MULTIPLIER


def create_stripe_checkout_session(
    borrowing: Borrowing,
    request,
    payment_type: Payment.Type = Payment.Type.PAYMENT,
) -> Payment:
    if payment_type == Payment.Type.FINE:
        money_to_pay = calculate_fine_price(borrowing)
        product_name = f"Fine for late return: {borrowing.book.title}"
        product_description = (
            f"Overdue period: expected {borrowing.expected_return_date}, "
            f"returned {borrowing.actual_return_date}"
        )
    else:
        money_to_pay = calculate_borrowing_price(borrowing)
        product_name = f"Borrowing: {borrowing.book.title}"
        product_description = (
            f"Period: {borrowing.borrow_date} - {borrowing.expected_return_date}"
        )

    price_in_cents = int(money_to_pay * 100)

    success_url = (
        request.build_absolute_uri(reverse("payment:payment-success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("payment:payment-cancel"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price_in_cents,
                    "product_data": {
                        "name": product_name,
                        "description": product_description,
                    },
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    payment = Payment.objects.create(
        status=Payment.Status.PENDING,
        type=payment_type,
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=money_to_pay,
    )

    return payment
