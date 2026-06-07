from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from billing.models import ConsumptionRecord, PriceStrategy


class PriceService:
    DEFAULT_WATER_PRICE = Decimal('3.50')
    DEFAULT_ELECTRICITY_PRICE = Decimal('0.60')

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _price4(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    @staticmethod
    def get_active_strategy(category: str) -> PriceStrategy | None:
        return PriceStrategy.objects.filter(category=category, is_active=True).first()

    @staticmethod
    def get_unit_price(category: str) -> Decimal:
        strategy = PriceService.get_active_strategy(category)
        if strategy:
            return PriceService._price4(strategy.unit_price)
        if category == ConsumptionRecord.CATEGORY_WATER:
            return PriceService._price4(PriceService.DEFAULT_WATER_PRICE)
        return PriceService._price4(PriceService.DEFAULT_ELECTRICITY_PRICE)

    @staticmethod
    def calculate_cost(category: str, usage: Decimal) -> Tuple[Decimal, Decimal, dict]:
        usage = Decimal(usage)
        if usage <= 0:
            return Decimal('0.00'), PriceService.get_unit_price(category), {}

        strategy = PriceService.get_active_strategy(category)

        if not strategy or strategy.strategy_type == PriceStrategy.TYPE_FLAT:
            unit_price = PriceService.get_unit_price(category)
            total = PriceService._money(usage * unit_price)
            return total, unit_price, {'type': 'flat', 'unit_price': str(unit_price)}

        return PriceService._calculate_tiered_cost(usage, strategy)

    @staticmethod
    def _calculate_tiered_cost(usage: Decimal, strategy: PriceStrategy) -> Tuple[Decimal, Decimal, dict]:
        tiers = strategy.tiers
        total = Decimal('0')
        remaining = usage
        tier_details = []

        for tier in tiers:
            start = Decimal(str(tier.get('start', 0)))
            end = tier.get('end')
            price = PriceService._price4(tier.get('price', strategy.unit_price))

            if end is None:
                tier_usage = remaining
            else:
                tier_end = Decimal(str(end))
                tier_start = Decimal(str(start))
                tier_usage = min(remaining, max(Decimal('0'), tier_end - tier_start))

            if tier_usage <= 0:
                continue

            tier_cost = PriceService._money(tier_usage * price)
            total += tier_cost
            remaining -= tier_usage

            tier_details.append(
                {
                    'start': str(start),
                    'end': str(end) if end is not None else None,
                    'usage': str(tier_usage),
                    'price': str(price),
                    'cost': str(tier_cost),
                }
            )

            if remaining <= 0:
                break

        if remaining > 0:
            unit_price = PriceService._price4(strategy.unit_price)
            tier_cost = PriceService._money(remaining * unit_price)
            total += tier_cost
            tier_details.append(
                {
                    'start': 'overflow',
                    'end': None,
                    'usage': str(remaining),
                    'price': str(unit_price),
                    'cost': str(tier_cost),
                }
            )

        avg_price = PriceService._price4(total / usage) if usage > 0 else Decimal('0')
        return (
            PriceService._money(total),
            avg_price,
            {'type': 'tiered', 'tiers': tier_details, 'avg_price': str(avg_price)},
        )
