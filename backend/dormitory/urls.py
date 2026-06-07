from django.urls import path

from dormitory.views import (
    AssignmentBindAPIView,
    AssignmentChangeRoomAPIView,
    AssignmentListAPIView,
    AssignmentUnbindAPIView,
    AvailableStudentsAPIView,
    BuildingDetailAPIView,
    BuildingListCreateAPIView,
    MyRoomAPIView,
    RoomDetailAPIView,
    RoomListCreateAPIView,
)

urlpatterns = [
    path('my-room/', MyRoomAPIView.as_view(), name='my-room'),
    path('buildings/', BuildingListCreateAPIView.as_view(), name='buildings'),
    path('buildings/<int:building_id>/', BuildingDetailAPIView.as_view(), name='building-detail'),
    path('rooms/', RoomListCreateAPIView.as_view(), name='rooms'),
    path('rooms/<int:room_id>/', RoomDetailAPIView.as_view(), name='room-detail'),
    path('assignments/', AssignmentListAPIView.as_view(), name='assignments'),
    path('assignments/bind/', AssignmentBindAPIView.as_view(), name='assignment-bind'),
    path('assignments/unbind/', AssignmentUnbindAPIView.as_view(), name='assignment-unbind'),
    path('assignments/change-room/', AssignmentChangeRoomAPIView.as_view(), name='assignment-change-room'),
    path('students/available/', AvailableStudentsAPIView.as_view(), name='available-students'),
]
