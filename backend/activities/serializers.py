from django.utils import timezone
from rest_framework import serializers

from activities.models import Activity, ActivityRegistration, ActivityReview


class ActivityListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    publisher_name = serializers.CharField(source='publisher.username', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_register = serializers.BooleanField(read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = (
            'id',
            'title',
            'cover_image',
            'location',
            'start_time',
            'end_time',
            'max_participants',
            'registered_count',
            'is_full',
            'can_register',
            'require_approval',
            'require_payment',
            'fee_amount',
            'status',
            'status_display',
            'publisher_name',
            'published_at',
            'average_rating',
        )

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return None
        total = sum(r.rating for r in reviews)
        return round(total / reviews.count(), 1)


class ActivityDetailSerializer(ActivityListSerializer):
    class Meta:
        model = Activity
        fields = ActivityListSerializer.Meta.fields + ('description', 'check_in_code')


class ActivityCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=10000)
    cover_image = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    location = serializers.CharField(max_length=200)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    max_participants = serializers.IntegerField(min_value=1)
    require_approval = serializers.BooleanField(default=False)
    require_payment = serializers.BooleanField(default=False)
    fee_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = serializers.ChoiceField(
        choices=[('draft', '草稿'), ('published', '已发布')],
        default='draft',
        required=False,
    )

    def validate(self, attrs):
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError({'start_time': '开始时间必须早于结束时间。'})
        if attrs.get('require_payment') and attrs.get('fee_amount', 0) <= 0:
            raise serializers.ValidationError({'fee_amount': '需要扣费时费用必须大于 0。'})
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        status = validated_data.get('status', Activity.STATUS_DRAFT)
        activity = Activity.objects.create(
            title=validated_data['title'].strip(),
            description=validated_data['description'].strip(),
            cover_image=validated_data.get('cover_image', ''),
            location=validated_data['location'].strip(),
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            max_participants=validated_data['max_participants'],
            require_approval=validated_data.get('require_approval', False),
            require_payment=validated_data.get('require_payment', False),
            fee_amount=validated_data.get('fee_amount', 0),
            status=status,
            publisher=request.user,
            published_at=timezone.now() if status == Activity.STATUS_PUBLISHED else None,
        )
        return activity

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title).strip()
        instance.description = validated_data.get('description', instance.description).strip()
        instance.cover_image = validated_data.get('cover_image', instance.cover_image)
        instance.location = validated_data.get('location', instance.location).strip()
        instance.start_time = validated_data.get('start_time', instance.start_time)
        instance.end_time = validated_data.get('end_time', instance.end_time)
        instance.max_participants = validated_data.get('max_participants', instance.max_participants)
        instance.require_approval = validated_data.get('require_approval', instance.require_approval)
        instance.require_payment = validated_data.get('require_payment', instance.require_payment)
        instance.fee_amount = validated_data.get('fee_amount', instance.fee_amount)
        new_status = validated_data.get('status')
        if new_status and new_status != instance.status:
            instance.status = new_status
            if new_status == Activity.STATUS_PUBLISHED and not instance.published_at:
                instance.published_at = timezone.now()
        instance.save()
        return instance


class ActivityRegistrationListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    student_id = serializers.CharField(source='user.profile.student_id', read_only=True)
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    activity_start_time = serializers.DateTimeField(source='activity.start_time', read_only=True)
    activity_end_time = serializers.DateTimeField(source='activity.end_time', read_only=True)
    activity_location = serializers.CharField(source='activity.location', read_only=True)
    activity_cover = serializers.CharField(source='activity.cover_image', read_only=True)

    class Meta:
        model = ActivityRegistration
        fields = (
            'id',
            'activity',
            'activity_title',
            'activity_start_time',
            'activity_end_time',
            'activity_location',
            'activity_cover',
            'user',
            'user_name',
            'student_id',
            'status',
            'status_display',
            'paid_amount',
            'check_in_time',
            'review_remark',
            'registered_at',
        )


class ActivityReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)

    class Meta:
        model = ActivityReview
        fields = (
            'id',
            'activity',
            'user',
            'user_name',
            'rating',
            'rating_display',
            'content',
            'created_at',
        )


class ActivityReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    content = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')

    def create(self, validated_data):
        request = self.context['request']
        activity = self.context['activity']
        registration = self.context['registration']
        return ActivityReview.objects.create(
            activity=activity,
            user=request.user,
            registration=registration,
            rating=validated_data['rating'],
            content=validated_data.get('content', ''),
        )


class CheckInSerializer(serializers.Serializer):
    check_in_code = serializers.CharField(max_length=16)
