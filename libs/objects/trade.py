from libs.objects.order import Order


class Trade(Order):
    def __init__(self, trade_id, time, ticker, status, side, fee_amount, fee_currency, order_price, order_total,
                 token_amount):
        super().__init__(trade_id, time, ticker, status, side)
        self.fee_amount = fee_amount
        self.fee_currency = fee_currency
        self.order_price = order_price
        self.order_total = order_total
        self.token_amount = token_amount

    def calculate_fee(self, fee_token_exchange_rate, token_price_when_buy, fee_token_ticker, token_ticker):
        return self.fee_amount, True
