from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.models import Borrowing
from borrowing.serializers import (
    BorrowingCreateSerializer,
    BorrowingListSerializer,
    BorrowingSerializer,
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
        serializer.save(user=self.request.user)

    @action(methods=["POST"], detail=True, url_path="return")
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"error": "This borrowing has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            borrowing.actual_return_date = timezone.now().date()
            borrowing.save()

            borrowing.book.inventory += 1
            borrowing.book.save()

        serializer = BorrowingSerializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)
