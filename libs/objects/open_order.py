from libs.objects.order import Order


class OpenOrder(Order):
    def __init__(self, order_id, time, ticker, status, route, left):
        super().__init__(order_id, time, ticker, status, route)
        self.left = left
