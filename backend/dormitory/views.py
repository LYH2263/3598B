from django.contrib.auth.models import User
from django.db.models import Case, Count, Q, When
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import IsAdminRole
from dormitory.models import Building, Room, RoomAssignment
from dormitory.serializers import (
    AssignmentBindSerializer,
    AssignmentChangeRoomSerializer,
    AssignmentUnbindSerializer,
    BuildingSerializer,
    RoomAssignmentSerializer,
    RoomSerializer,
    UserRoomSerializer,
)
from dormitory.services.assignment_service import RoomAssignmentService


class MyRoomAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        assignment = RoomAssignmentService.get_user_current_assignment(user)
        if assignment is None:
            return Response({'room': None, 'history': []})

        history = list(
            user.room_assignments.filter(unbound_at__isnull=False)
            .select_related('room', 'room__building')
            .order_by('-bound_at')[:10]
        )
        return Response(
            {
                'room': UserRoomSerializer(assignment).data,
                'history': RoomAssignmentSerializer(history, many=True).data,
            }
        )


class BuildingListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        queryset = Building.objects.annotate(room_count=Count('rooms')).order_by('name')
        return Response(BuildingSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = BuildingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        building = serializer.save()
        return Response(BuildingSerializer(building).data, status=status.HTTP_201_CREATED)


class BuildingDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _get_building(self, building_id: int):
        return Building.objects.filter(id=building_id).first()

    def put(self, request, building_id: int):
        building = self._get_building(building_id)
        if not building:
            return Response({'detail': '楼栋不存在。'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BuildingSerializer(building, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        building = serializer.save()
        return Response(BuildingSerializer(building).data)

    def delete(self, request, building_id: int):
        building = self._get_building(building_id)
        if not building:
            return Response({'detail': '楼栋不存在。'}, status=status.HTTP_404_NOT_FOUND)
        if building.rooms.filter(assignments__unbound_at__isnull=True).exists():
            return Response(
                {'detail': '该楼栋下仍有房间存在住户，请先处理住户再删除。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        building.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_queryset(self, request):
        active_assignments = Count('assignments', filter=Q(assignments__unbound_at__isnull=True))
        queryset = Room.objects.select_related('building').annotate(
            current_occupancy=active_assignments,
            has_residents=Case(
                When(current_occupancy__gt=0, then=True),
                default=False,
            ),
        )
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get(self, request):
        queryset = self._get_queryset(request)
        building_id = request.query_params.get('building_id', '').strip()
        keyword = request.query_params.get('keyword', '').strip()
        only_active = request.query_params.get('only_active', '').strip()

        if building_id:
            queryset = queryset.filter(building_id=building_id)
        if keyword:
            queryset = queryset.filter(
                Q(room_number__icontains=keyword) | Q(building__name__icontains=keyword)
            )
        if only_active == 'true':
            queryset = queryset.filter(is_active=True)

        return Response(RoomSerializer(queryset[:500], many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_ADMIN:
            return Response({'detail': '仅管理员可创建房间。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class RoomDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _get_room(self, room_id: int):
        active_assignments = Count('assignments', filter=Q(assignments__unbound_at__isnull=True))
        return (
            Room.objects.select_related('building')
            .annotate(
                current_occupancy=active_assignments,
                has_residents=Case(
                    When(current_occupancy__gt=0, then=True),
                    default=False,
                ),
            )
            .filter(id=room_id)
            .first()
        )

    def get(self, request, room_id: int):
        room = self._get_room(room_id)
        if not room:
            return Response({'detail': '房间不存在。'}, status=status.HTTP_404_NOT_FOUND)

        residents = RoomAssignmentService.get_room_active_assignments(room)
        history = list(
            room.assignments.filter(unbound_at__isnull=False)
            .select_related('user', 'user__profile')
            .order_by('-bound_at')[:50]
        )
        return Response(
            {
                'room': RoomSerializer(room).data,
                'residents': RoomAssignmentSerializer(residents, many=True).data,
                'history': RoomAssignmentSerializer(history, many=True).data,
            }
        )

    def put(self, request, room_id: int):
        room = self._get_room(room_id)
        if not room:
            return Response({'detail': '房间不存在。'}, status=status.HTTP_404_NOT_FOUND)

        new_is_active = request.data.get('is_active')
        if new_is_active is False and room.has_active_residents():
            return Response(
                {'detail': '该房间仍有住户，不可停用。请先解绑所有住户。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RoomSerializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        return Response(RoomSerializer(self._get_room(room.id)).data)

    def delete(self, request, room_id: int):
        room = Room.objects.filter(id=room_id).first()
        if not room:
            return Response({'detail': '房间不存在。'}, status=status.HTTP_404_NOT_FOUND)
        if room.has_active_residents():
            return Response(
                {'detail': '该房间仍有住户，请先解绑所有住户再删除。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignmentListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        queryset = RoomAssignment.objects.select_related('user', 'user__profile', 'room', 'room__building')

        only_active = request.query_params.get('only_active', '').strip()
        room_id = request.query_params.get('room_id', '').strip()
        user_id = request.query_params.get('user_id', '').strip()
        keyword = request.query_params.get('keyword', '').strip()

        if only_active == 'true':
            queryset = queryset.filter(unbound_at__isnull=True)
        elif only_active == 'false':
            queryset = queryset.filter(unbound_at__isnull=False)
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if keyword:
            queryset = queryset.filter(
                Q(user__username__icontains=keyword)
                | Q(user__profile__student_id__icontains=keyword)
                | Q(room__room_number__icontains=keyword)
                | Q(room__building__name__icontains=keyword)
            )

        return Response(RoomAssignmentSerializer(queryset[:300], many=True).data)


class AssignmentBindAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = AssignmentBindSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(RoomAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class AssignmentUnbindAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = AssignmentUnbindSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(RoomAssignmentSerializer(assignment).data)


class AssignmentChangeRoomAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = AssignmentChangeRoomSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(RoomAssignmentSerializer(assignment).data)


class AvailableStudentsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        only_unassigned = request.query_params.get('only_unassigned', 'false').strip().lower() == 'true'

        queryset = (
            User.objects.select_related('profile')
            .filter(profile__role=Profile.ROLE_STUDENT)
            .order_by('username')
        )
        if keyword:
            queryset = queryset.filter(
                Q(username__icontains=keyword)
                | Q(profile__student_id__icontains=keyword)
                | Q(email__icontains=keyword)
            )
        if only_unassigned:
            queryset = queryset.filter(
                ~Q(room_assignments__unbound_at__isnull=True)
            )

        result = []
        for user in queryset[:200]:
            assignment = RoomAssignmentService.get_user_current_assignment(user)
            result.append(
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'student_id': getattr(user.profile, 'student_id', ''),
                    'current_room': str(assignment.room) if assignment else '',
                    'current_room_id': assignment.room_id if assignment else None,
                }
            )
        return Response(result)
