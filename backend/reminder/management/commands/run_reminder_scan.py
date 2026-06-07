from django.core.management.base import BaseCommand

from reminder.services import ReminderService


class Command(BaseCommand):
    help = '执行催缴提醒全流程扫描：检测触发条件、推进升级链、自动解决已处理的提醒'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-scan',
            action='store_true',
            help='跳过触发条件检测',
        )
        parser.add_argument(
            '--skip-escalate',
            action='store_true',
            help='跳过升级链推进',
        )
        parser.add_argument(
            '--skip-resolve',
            action='store_true',
            help='跳过自动解决',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('开始执行催缴提醒扫描...'))

        result = {}

        if not options.get('skip_scan'):
            self.stdout.write('  [1/3] 检测触发条件...')
            scan_result = ReminderService.scan_all_students()
            result['scan'] = scan_result
            self.stdout.write(self.style.SUCCESS(
                f'  完成：扫描 {scan_result["scanned"]} 人，'
                f'免除 {scan_result["exempted"]} 人，'
                f'新建提醒 {scan_result["created"]} 条'
            ))
        else:
            self.stdout.write('  [1/3] 跳过触发条件检测')

        if not options.get('skip_escalate'):
            self.stdout.write('  [2/3] 推进升级链...')
            esc_result = ReminderService.escalate_reminders()
            result['escalate'] = esc_result
            self.stdout.write(self.style.SUCCESS(
                f'  完成：升级 {esc_result["escalated"]} 条，'
                f'已达最高级 {esc_result["already_max"]} 条'
            ))
        else:
            self.stdout.write('  [2/3] 跳过升级链推进')

        if not options.get('skip_resolve'):
            self.stdout.write('  [3/3] 自动解决已处理的提醒...')
            resolve_result = ReminderService.auto_resolve_reminders()
            result['resolve'] = resolve_result
            self.stdout.write(self.style.SUCCESS(
                f'  完成：自动解决 {resolve_result["resolved"]} 条'
            ))
        else:
            self.stdout.write('  [3/3] 跳过自动解决')

        self.stdout.write(self.style.SUCCESS('催缴提醒扫描全部完成。'))
        return result
