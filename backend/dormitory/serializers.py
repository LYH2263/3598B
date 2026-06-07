from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from dormitory.models import Building, Room, RoomAssignment
from dormitory.services.assignment_service import RoomAssignmentService


class BuildingSerializer(serializers.ModelSerializer):
    room_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Building
        fields = ('id', 'name', 'description', 'created_at', 'room_count')
        read_only_fields = ('id', 'created_at', 'room_count')


class RoomSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source='building.name', read_only=True)
    current_occupancy = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    has_residents = serializers.BooleanField(read_only=True)

    class Meta:
        model = Room
        fields = (
            'id',
            'building',
            'building_name',
            'room_number',
            'capacity',
            'is_active',
            'description',
            'current_occupancy',
            'is_full',
            'has_residents',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'building_name', 'current_occupancy', 'is_full', 'has_residents', 'created_at', 'updated_at')

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError('房间容量必须大于 0。')
        return value


class RoomAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    student_id = serializers.CharField(source='user.profile.student_id', read_only=True, default='')
    room_display = serializers.SerializerMethodField()
    building_name = serializers.CharField(source='room.building.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = RoomAssignment
        fields = (
            'id',
            'user',
            'user_name',
            'student_id',
            'room',
            'room_display',
            'building_name',
            'room_number',
            'bound_at',
            'unbound_at',
            'is_active',
            'operator',
            'remark',
        )
        read_only_fields = ('id', 'bound_at', 'unbound_at', 'is_active', 'operator')

    def get_room_display(self, obj):
        return str(obj.room)


class UserRoomSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source='room.building.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    capacity = serializers.IntegerField(source='room.capacity', read_only=True)
    current_occupancy = serializers.SerializerMethodField()
    bound_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = RoomAssignment
        fields = (
            'building_name',
            'room_number',
            'capacity',
            'current_occupancy',
            'bound_at',
        )

    def get_current_occupancy(self, obj):
        return obj.room.current_occupancy


class AssignmentBindSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    room_id = serializers.IntegerField()
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_user_id(self, value):
        user = User.objects.filter(id=value).first()
        if user is None:
            raise serializers.ValidationError('用户不存在。')
        profile = getattr(user, 'profile', None)
        if not profile or profile.role != Profile.ROLE_STUDENT:
            raise serializers.ValidationError('仅学生账户可绑定房间。')
        return value

    def validate_room_id(self, value):
        room = Room.objects.filter(id=value).first()
        if room is None:
            raise serializers.ValidationError('房间不存在。')
        return value

    def validate(self, attrs):
        user = User.objects.get(id=attrs['user_id'])
        room = Room.objects.get(id=attrs['room_id'])

        existing = RoomAssignmentService.get_user_current_assignment(user)
        if existing is not None:
            raise serializers.ValidationError({'user_id': '该学生已绑定其他房间，请先解绑或使用换房功能。'})

        if not room.is_active:
            raise serializers.ValidationError({'room_id': '该房间已停用，不可绑定住户。'})
        if room.is_full:
            raise serializers.ValidationError({'room_id': f'房间容量已满（{room.current_occupancy}/{room.capacity}），不可再绑入。'})

        attrs['user'] = user
        attrs['room'] = room
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return RoomAssignmentService.bind_user_to_room(
            user=validated_data['user'],
            room=validated_data['room'],
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )


class AssignmentUnbindSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_user_id(self, value):
        user = User.objects.filter(id=value).first()
        if user is None:
            raise serializers.ValidationError('用户不存在。')
        existing = RoomAssignmentService.get_user_current_assignment(user)
        if existing is None:
            raise serializers.ValidationError('该学生当前未绑定任何房间。')
        return value

    def validate(self, attrs):
        attrs['user'] = User.objects.get(id=attrs['user_id'])
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return RoomAssignmentService.unbind_user(
            user=validated_data['user'],
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )


class AssignmentChangeRoomSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    new_room_id = serializers.IntegerField()
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_user_id(self, value):
        user = User.objects.filter(id=value).first()
        if user is None:
            raise serializers.ValidationError('用户不存在。')
        existing = RoomAssignmentService.get_user_current_assignment(user)
        if existing is None:
            raise serializers.ValidationError('该学生当前未绑定任何房间，请使用绑定功能。')
        return value

    def validate_new_room_id(self, value):
        room = Room.objects.filter(id=value).first()
        if room is None:
            raise serializers.ValidationError('房间不存在。')
        return value

    def validate(self, attrs):
        user = User.objects.get(id=attrs['user_id'])
        new_room = Room.objects.get(id=attrs['new_room_id'])

        existing = RoomAssignmentService.get_user_current_assignment(user)
        if existing and existing.room_id == new_room.id:
            raise serializers.ValidationError({'new_room_id': '新房间与当前房间相同，无需换房。'})

        if not new_room.is_active:
            raise serializers.ValidationError({'new_room_id': '该房间已停用，不可绑定住户。'})
        if new_room.is_full:
            raise serializers.ValidationError({'new_room_id': f'房间容量已满（{new_room.current_occupancy}/{new_room.capacity}），不可再绑入。'})

        attrs['user'] = user
        attrs['new_room'] = new_room
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return RoomAssignmentService.change_room(
            user=validated_data['user'],
            new_room=validated_data['new_room'],
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )
