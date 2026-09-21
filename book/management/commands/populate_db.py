from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from book.models import Book


class Command(BaseCommand):
    help = "Populate database with sample books and test users"

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            email="user@example.com",
            defaults={"is_staff": False},
        )
        if created:
            user.set_password("user12345")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {user.email} (password: user12345)"))
        else:
            self.stdout.write(f"User {user.email} already exists.")

        sample_books = [
            {
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "author": "Robert C. Martin",
                "cover": Book.CoverType.HARD,
                "inventory": 5,
                "daily_fee": Decimal("1.50"),
            },
            {
                "title": "The Pragmatic Programmer: Your Journey to Mastery",
                "author": "Andrew Hunt, David Thomas",
                "cover": Book.CoverType.SOFT,
                "inventory": 3,
                "daily_fee": Decimal("1.75"),
            },
            {
                "title": "Design Patterns: Elements of Reusable Object-Oriented Software",
                "author": "Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides",
                "cover": Book.CoverType.HARD,
                "inventory": 2,
                "daily_fee": Decimal("2.00"),
            },
            {
                "title": "Refactoring: Improving the Design of Existing Code",
                "author": "Martin Fowler",
                "cover": Book.CoverType.HARD,
                "inventory": 4,
                "daily_fee": Decimal("1.80"),
            },
            {
                "title": "Designing Data-Intensive Applications",
                "author": "Martin Kleppmann",
                "cover": Book.CoverType.SOFT,
                "inventory": 1,
                "daily_fee": Decimal("2.50"),
            },
            {
                "title": "Rare Collector's Book (Out of Stock)",
                "author": "Unknown Author",
                "cover": Book.CoverType.HARD,
                "inventory": 0,  # Для тестування помилки нестачі примірників
                "daily_fee": Decimal("5.00"),
            },
        ]

        for book_data in sample_books:
            book, created = Book.objects.get_or_create(
                title=book_data["title"],
                defaults=book_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created book: {book.title}"))
            else:
                self.stdout.write(f"Book '{book.title}' already exists.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))