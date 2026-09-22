from django.contrib import admin
from payment.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "type",
        "borrowing",
        "money_to_pay",
        "session_id",
    )
    list_filter = ("status", "type")
    search_fields = ("session_id", "borrowing__user__email")
    readonly_fields = ("session_url", "session_id")
