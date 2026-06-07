from django.contrib.auth.models import User

from notices.models import UserNotification


class NotificationService:
    @staticmethod
    def create_user_notification(user, title: str, content: str, notice_type: str = UserNotification.TYPE_SYSTEM, announcement=None):
        return UserNotification.objects.create(
            user=user,
            title=title,
            content=content,
            notice_type=notice_type,
            related_announcement=announcement,
        )

    @staticmethod
    def push_announcement(announcement):
        users = list(User.objects.filter(is_active=True).only('id'))
        if not users:
            return 0

        payloads = [
            UserNotification(
                user=user,
                title=f'系统公告：{announcement.title}',
                content=announcement.content,
                notice_type=UserNotification.TYPE_ANNOUNCEMENT,
                related_announcement=announcement,
            )
            for user in users
        ]
        UserNotification.objects.bulk_create(payloads, batch_size=500)
        return len(payloads)
