from django.core.management.base import BaseCommand
from django.utils import timezone

from borrowing.models import Borrowing
from borrowing.telegram_bot import send_telegram_message


class Command(BaseCommand):
    help = "Check all overdue borrowings and notify via Telegram"

    def handle(self, *args, **options):
        today = timezone.now().date()

        overdue_borrowings = Borrowing.objects.filter(
            expected_return_date__lte=today,
            actual_return_date__isnull=True,
        ).select_related("book", "user")

        if not overdue_borrowings.exists():
            message = "✅ <b>No borrowings overdue today!</b>"
            send_telegram_message(message)
            self.stdout.write(self.style.SUCCESS("No overdue borrowings found. Notification sent."))
            return

        message_lines = ["⚠️ <b>Attention! Overdue Borrowings:</b>\n"]
        for borrowing in overdue_borrowings:
            message_lines.append(
                f"• <b>User:</b> {borrowing.user.email} | "
                f"<b>Book:</b> {borrowing.book.title} | "
                f"<b>Expected:</b> {borrowing.expected_return_date}"
            )

        full_message = "\n".join(message_lines)
        send_telegram_message(full_message)
        self.stdout.write(
            self.style.WARNING(
                f"Found {overdue_borrowings.count()} overdue borrowings. Notification sent."
            )
        )
