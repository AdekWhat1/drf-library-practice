from decimal import Decimal
import stripe
from django.conf import settings
from django.urls import reverse

from borrowing.models import Borrowing
from payment.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_borrowing_price(borrowing: Borrowing) -> Decimal:
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    total_days = max(days, 1)
    return Decimal(total_days) * borrowing.book.daily_fee


def create_stripe_checkout_session(
    borrowing: Borrowing,
    request,
    payment_type: Payment.Type = Payment.Type.PAYMENT,
) -> Payment:
    money_to_pay = calculate_borrowing_price(borrowing)
    price_in_cents = int(money_to_pay * 100)

    success_url = request.build_absolute_uri(
        reverse("payment:payment-success")
    ) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri(
        reverse("payment:payment-cancel")
    ) + "?session_id={CHECKOUT_SESSION_ID}"

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price_in_cents,
                    "product_data": {
                        "name": f"Borrowing: {borrowing.book.title}",
                        "description": f"Period: {borrowing.borrow_date} - {borrowing.expected_return_date}",
                    },
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    # Зберігаємо платіж у стані PENDING
    payment = Payment.objects.create(
        status=Payment.Status.PENDING,
        type=payment_type,
        borrowing=borrowing,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=money_to_pay,
    )

    return payment