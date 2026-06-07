from django.contrib import admin

from dormitory.models import Building, Room, RoomAssignment


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'building', 'room_number', 'capacity', 'is_active', 'current_occupancy_display', 'description')
    list_filter = ('building', 'is_active')
    search_fields = ('room_number', 'building__name', 'description')
    readonly_fields = ('current_occupancy',)

    def current_occupancy_display(self, obj) -> str:
        return f'{obj.current_occupancy}/{obj.capacity}'

    current_occupancy_display.short_description = '入住情况'


@admin.register(RoomAssignment)
class RoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'room', 'bound_at', 'unbound_at', 'is_active_display', 'operator')
    list_filter = ('room__building',)
    search_fields = ('user__username', 'user__profile__student_id', 'room__room_number', 'room__building__name')

    def is_active_display(self, obj) -> str:
        return '当前' if obj.is_active else '历史'

    is_active_display.short_description = '状态'
