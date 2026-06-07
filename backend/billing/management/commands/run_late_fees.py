from django.core.management.base import BaseCommand

from billing.services.utility_bill_service import UtilityBillService


class Command(BaseCommand):
    help = '计算所有逾期账单的滞纳金'

    def handle(self, *args, **options):
        count = UtilityBillService.run_late_fee_batch()
        self.stdout.write(self.style.SUCCESS(f'成功处理 {count} 张逾期账单的滞纳金计算。'))
