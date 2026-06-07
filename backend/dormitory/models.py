from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Building(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name='楼栋名称')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='备注说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'buildings'
        ordering = ['name']
        verbose_name = '楼栋'
        verbose_name_plural = '楼栋'

    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name='所属楼栋',
    )
    room_number = models.CharField(max_length=32, verbose_name='房间号')
    capacity = models.PositiveIntegerField(default=4, verbose_name='房间容量')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='备注说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rooms'
        ordering = ['building__name', 'room_number']
        unique_together = [('building', 'room_number')]
        verbose_name = '房间'
        verbose_name_plural = '房间'

    def __str__(self) -> str:
        return f'{self.building.name} {self.room_number}'

    @property
    def current_occupancy(self) -> int:
        return self.assignments.filter(unbound_at__isnull=True).count()

    @property
    def is_full(self) -> bool:
        return self.current_occupancy >= self.capacity

    def has_active_residents(self) -> bool:
        return self.assignments.filter(unbound_at__isnull=True).exists()

    def clean(self):
        super().clean()
        if self.capacity <= 0:
            raise ValidationError({'capacity': '房间容量必须大于 0。'})


class RoomAssignment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='room_assignments',
        verbose_name='学生用户',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='房间',
    )
    bound_at = models.DateTimeField(auto_now_add=True, verbose_name='绑定时间')
    unbound_at = models.DateTimeField(null=True, blank=True, verbose_name='解绑时间')
    operator = models.CharField(max_length=64, blank=True, default='', verbose_name='操作人')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')

    class Meta:
        db_table = 'room_assignments'
        ordering = ['-bound_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(unbound_at__isnull=True),
                name='unique_active_assignment_per_user',
            ),
        ]
        verbose_name = '房间绑定记录'
        verbose_name_plural = '房间绑定记录'

    def __str__(self) -> str:
        status = '当前' if self.unbound_at is None else '历史'
        return f'{self.user.username} - {self.room} ({status})'

    @property
    def is_active(self) -> bool:
        return self.unbound_at is None
