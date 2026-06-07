from datetime import datetime

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from accounts.models import Profile
from dormitory.models import Room, RoomAssignment


class RoomAssignmentService:
    @staticmethod
    def _validate_student_user(user: User) -> None:
        profile = getattr(user, 'profile', None)
        if not profile or profile.role != Profile.ROLE_STUDENT:
            raise ValueError('仅学生账户可绑定房间。')

    @staticmethod
    def _validate_room_available(room: Room) -> None:
        if not room.is_active:
            raise ValueError('该房间已停用，不可绑定住户。')
        if room.is_full:
            raise ValueError(f'房间容量已满（{room.current_occupancy}/{room.capacity}），不可再绑入。')

    @staticmethod
    def get_user_current_assignment(user: User) -> RoomAssignment | None:
        return (
            user.room_assignments.filter(unbound_at__isnull=True)
            .select_related('room', 'room__building')
            .first()
        )

    @staticmethod
    def get_room_active_assignments(room: Room):
        return (
            room.assignments.filter(unbound_at__isnull=True)
            .select_related('user', 'user__profile')
            .order_by('bound_at')
        )

    @classmethod
    @transaction.atomic
    def bind_user_to_room(
        cls,
        user: User,
        room: Room,
        operator: str,
        remark: str = '',
    ) -> RoomAssignment:
        cls._validate_student_user(user)
        cls._validate_room_available(room)

        existing = cls.get_user_current_assignment(user)
        if existing is not None:
            raise ValueError('该学生已绑定其他房间，请先解绑或使用换房功能。')

        assignment = RoomAssignment.objects.create(
            user=user,
            room=room,
            operator=operator,
            remark=remark,
        )
        return assignment

    @classmethod
    @transaction.atomic
    def unbind_user(
        cls,
        user: User,
        operator: str,
        remark: str = '',
    ) -> RoomAssignment:
        assignment = cls.get_user_current_assignment(user)
        if assignment is None:
            raise ValueError('该学生当前未绑定任何房间。')

        assignment.unbound_at = datetime.now()
        if remark:
            assignment.remark = (assignment.remark + ' | ' if assignment.remark else '') + remark
        if operator and not assignment.operator:
            assignment.operator = operator
        assignment.save(update_fields=['unbound_at', 'remark', 'operator'])
        return assignment

    @classmethod
    @transaction.atomic
    def change_room(
        cls,
        user: User,
        new_room: Room,
        operator: str,
        remark: str = '',
    ) -> RoomAssignment:
        cls._validate_student_user(user)
        cls._validate_room_available(new_room)

        old_assignment = cls.get_user_current_assignment(user)
        if old_assignment is None:
            raise ValueError('该学生当前未绑定任何房间，请使用绑定功能。')

        if old_assignment.room_id == new_room.id:
            raise ValueError('新房间与当前房间相同，无需换房。')

        old_assignment.unbound_at = datetime.now()
        old_assignment.save(update_fields=['unbound_at'])

        new_assignment = RoomAssignment.objects.create(
            user=user,
            room=new_room,
            operator=operator,
            remark=remark or f'由 {old_assignment.room} 换至 {new_room}',
        )
        return new_assignment
