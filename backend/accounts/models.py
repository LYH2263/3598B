from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_STUDENT, '学生'),
        (ROLE_ADMIN, '管理员'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    student_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    security_question = models.CharField(max_length=255, blank=True, default='')
    security_answer_hash = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'profiles'

    def __str__(self) -> str:
        return f'{self.user.username}({self.get_role_display()})'

    def set_security_answer(self, raw_answer: str) -> None:
        normalized = (raw_answer or '').strip().lower()
        self.security_answer_hash = make_password(normalized) if normalized else ''

    def check_security_answer(self, raw_answer: str) -> bool:
        if not self.security_answer_hash:
            return False
        normalized = (raw_answer or '').strip().lower()
        return check_password(normalized, self.security_answer_hash)
