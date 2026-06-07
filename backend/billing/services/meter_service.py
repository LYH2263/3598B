from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from billing.models import MeterReading
from dormitory.models import Room, RoomAssignment


class MeterService:
    @staticmethod
    def get_previous_reading(room: Room, category: str, period_start) -> Decimal:
        last_reading = (
            MeterReading.objects.filter(room=room, category=category, period_end__lt=period_start)
            .order_by('-period_end')
            .first()
        )
        if last_reading:
            return last_reading.current_reading
        return Decimal('0')

    @staticmethod
    @transaction.atomic
    def create_reading(
        *,
        room_id: int,
        category: str,
        period_start,
        period_end,
        current_reading: Decimal,
        previous_reading: Decimal | None = None,
        source: str = MeterReading.SOURCE_ADMIN,
        operator: str = '',
        remark: str = '',
    ) -> MeterReading:
        room = Room.objects.filter(id=room_id).first()
        if not room:
            raise ValidationError({'room_id': '房间不存在。'})

        if period_start >= period_end:
            raise ValidationError({'period_start': '周期开始日期必须早于结束日期。'})

        if previous_reading is None:
            previous_reading = MeterService.get_previous_reading(room, category, period_start)

        if current_reading < previous_reading:
            raise ValidationError({'current_reading': '本期表底不能小于上期表底。'})

        usage = current_reading - previous_reading

        reading = MeterReading.objects.create(
            room=room,
            category=category,
            period_start=period_start,
            period_end=period_end,
            previous_reading=previous_reading,
            current_reading=current_reading,
            usage=usage,
            source=source,
            operator=operator,
            remark=remark,
        )
        return reading

    @staticmethod
    def get_room_active_users(room: Room):
        return list(
            RoomAssignment.objects.filter(room=room, unbound_at__isnull=True)
            .select_related('user')
            .values_list('user', flat=True)
        )
