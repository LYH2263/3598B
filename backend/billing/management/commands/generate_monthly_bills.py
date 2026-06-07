from calendar import monthrange
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from billing.services.utility_bill_service import UtilityBillService


class Command(BaseCommand):
    help = '按周期（默认上月）批量生成水电账单'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='指定年份（默认为上年或本年）',
        )
        parser.add_argument(
            '--month',
            type=int,
            help='指定月份（1-12，默认为上月）',
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['water', 'electricity', ''],
            default='',
            help='费用类型：water/electricity，默认全部',
        )

    def handle(self, *args, **options):
        today = date.today()
        year = options.get('year')
        month = options.get('month')
        category = options.get('category') or None

        if year and month:
            pass
        elif month:
            year = today.year if month <= today.month else today.year - 1
        elif year:
            raise CommandError('指定年份时必须同时指定月份。')
        else:
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        last_day = monthrange(year, month)[1]
        period_start = date(year, month, 1)
        period_end = date(year, month, last_day)

        self.stdout.write(f'开始生成 {period_start} ~ {period_end} 的账单...')

        bills = UtilityBillService.generate_bills_for_period(
            period_start=period_start,
            period_end=period_end,
            category=category,
            operator='cron',
        )

        self.stdout.write(self.style.SUCCESS(f'成功生成 {len(bills)} 张账单。'))
