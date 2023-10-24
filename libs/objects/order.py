class Order:
    def __init__(self, order_id, time, ticker, status, route):
        self.id = order_id
        self.time = time
        self.ticker = ticker
        self.status = status
        self.route = route
