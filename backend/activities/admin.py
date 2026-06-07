from django.contrib import admin

from activities.models import Activity, ActivityRegistration, ActivityReview


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'status',
        'location',
        'start_time',
        'end_time',
        'max_participants',
        'publisher',
    )
    list_filter = ('status', 'require_approval', 'require_payment')
    search_fields = ('title', 'location', 'description')
    readonly_fields = ('created_at', 'updated_at', 'published_at')


@admin.register(ActivityRegistration)
class ActivityRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'activity',
        'user',
        'status',
        'paid_amount',
        'registered_at',
        'check_in_time',
    )
    list_filter = ('status',)
    search_fields = ('activity__title', 'user__username')
    readonly_fields = ('registered_at', 'check_in_time', 'reviewed_at')


@admin.register(ActivityReview)
class ActivityReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('activity__title', 'user__username', 'content')
    readonly_fields = ('created_at',)
