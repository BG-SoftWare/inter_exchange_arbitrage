from decimal import Decimal

from libs.objects.trade import Trade


class ExtendedTrade(Trade):
    def __init__(self, trade_id, time, ticker, status, side, fee_amount, fee_currency, order_price, order_total,
                 token_amount):
        super().__init__(trade_id, time, ticker, status, side, fee_amount, fee_currency, order_price, order_total,
                         token_amount)

    def calculate_fee(self, fee_token_exchange_rate, token_price_when_buy, fee_token_ticker, token_ticker):
        fee, is_fee_token = 0, True
        for currency_idx in range(len(self.fee_currency)):
            if self.fee_currency[currency_idx] == fee_token_ticker:
                fee += Decimal(self.fee_amount[currency_idx]) * fee_token_exchange_rate
            elif self.fee_currency[currency_idx] == token_ticker:
                fee += Decimal(self.fee_amount[currency_idx]) * token_price_when_buy
                is_fee_token = False
            else:
                fee += Decimal(self.fee_amount[currency_idx]) * 1
                is_fee_token = False
        return fee, is_fee_token
