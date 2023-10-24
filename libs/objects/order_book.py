import json
from decimal import Decimal

from libs.misc import timeit_debug as timeit


class OrderBook:
    def __init__(self, symbol, bids, asks, timestamp):
        self.bids = bids
        self.asks = asks
        self.symbol = symbol
        self.timestamp = timestamp

    @timeit
    def calculate(self, route, amount=0):
        amount_orig = amount
        if route == "BUY":
            if amount > 0:
                buy_price, avg_buy_price, usdt_amount, is_first = 0, 0, 0, True
                for ask in self.asks:
                    if Decimal(ask[1]) >= amount and is_first:
                        return Decimal(ask[0]), Decimal(ask[0]), amount * Decimal(ask[0])
                    elif Decimal(ask[1]) < amount and is_first:
                        is_first = False
                        usdt_amount += Decimal(ask[1]) * Decimal(ask[0])
                        amount -= Decimal(ask[1])
                        continue
                    if not is_first:
                        if Decimal(ask[1]) <= amount:
                            usdt_amount += Decimal(ask[1]) * Decimal(ask[0])
                            amount -= Decimal(ask[1])
                            if amount == 0:
                                return Decimal(ask[0]), usdt_amount / amount_orig, usdt_amount
                        else:
                            usdt_amount += amount * Decimal(ask[0])
                            return Decimal(ask[0]), usdt_amount / amount_orig, usdt_amount
        elif route == "SELL":
            if amount > 0:
                sell_price, avg_sell_price, usdt_amount, is_first = 0, 0, 0, True
                for bid in self.bids:
                    if Decimal(bid[1]) >= amount and is_first:
                        return Decimal(bid[0]), Decimal(bid[0]), amount * Decimal(bid[0])
                    elif Decimal(bid[1]) < amount and is_first:
                        is_first = False
                        usdt_amount += Decimal(bid[1]) * Decimal(bid[0])
                        amount -= Decimal(bid[1])
                        continue
                    if not is_first:
                        if Decimal(bid[1]) <= amount:
                            usdt_amount += Decimal(bid[1]) * Decimal(bid[0])
                            amount -= Decimal(bid[1])
                            if amount == 0:
                                return Decimal(bid[0]), usdt_amount / amount_orig, usdt_amount
                        else:
                            usdt_amount += amount * Decimal(bid[0])
                            return Decimal(bid[0]), usdt_amount / amount_orig, usdt_amount

    @timeit
    def calculate_for_usdt(self, route, amount=0):
        amount_orig = amount
        if route == "BUY":
            if amount > 0:
                buy_price, avg_buy_price, usdt_amount, is_first = 0, 0, 0, True
                for i in self.asks:
                    if Decimal(i[1]) * Decimal(i[0]) >= amount and is_first:
                        return Decimal(i[0]), Decimal(i[0]), amount / Decimal(i[0])
                    elif Decimal(i[1]) * Decimal(i[0]) < amount and is_first:
                        is_first = False
                        usdt_amount += Decimal(i[1])
                        amount -= Decimal(i[1]) * Decimal(i[0])
                        continue
                    if not is_first:
                        if Decimal(i[1]) * Decimal(i[0]) <= amount:
                            usdt_amount += Decimal(i[1])
                            amount -= Decimal(i[1]) * Decimal(i[0])
                            if amount == 0:
                                return Decimal(i[0]), amount_orig / usdt_amount, usdt_amount
                        else:
                            usdt_amount += amount / Decimal(i[0])
                            return Decimal(i[0]), amount_orig / usdt_amount, usdt_amount
        elif route == "SELL":
            if amount > 0:
                sell_price, avg_sell_price, usdt_amount, is_first = 0, 0, 0, True
                for i in self.bids:
                    if Decimal(i[1]) * Decimal(i[0]) >= amount and is_first:
                        return Decimal(i[0]), Decimal(i[0]), amount / Decimal(i[0])
                    elif Decimal(i[1]) * Decimal(i[0]) < amount and is_first:
                        is_first = False
                        usdt_amount += Decimal(i[1])
                        amount -= Decimal(i[1]) * Decimal(i[0])
                        continue
                    if not is_first:
                        if Decimal(i[1]) * Decimal(i[0]) <= amount:
                            usdt_amount += Decimal(i[1])
                            amount -= Decimal(i[1]) * Decimal(i[0])
                            if amount == 0:
                                return Decimal(i[0]), amount_orig / usdt_amount, usdt_amount
                        else:
                            usdt_amount += amount / Decimal(i[0])
                            return Decimal(i[0]), amount_orig / usdt_amount, usdt_amount

    def get_bid(self):
        return self.bids[0]

    def get_ask(self):
        return self.asks[0]

    def to_json(self):
        return json.dumps({"bids": self.bids[:25], "asks": self.asks[:25], "timestamp": self.timestamp}, default=str)

    @timeit
    def order_fork(self, price, route, step):
        if route == "SELL":
            for i in range(len(self.bids)):
                if Decimal(self.bids[i][0]) == price:
                    if i + step >= len(self.bids) - 1:
                        return Decimal(self.bids[-1][0]), Decimal(self.bids[-1][0])
                    return price, Decimal(self.bids[i + step][0])
        elif route == "BUY":
            for i in range(len(self.asks)):
                if Decimal(self.asks[i][0]) == price:
                    if i + step >= len(self.asks) - 1:
                        return Decimal(self.asks[-1][0]), Decimal(self.asks[-1][0])
                    return price, Decimal(self.asks[i + step][0])

    def order_with_max_price(self, price_threshold, route):
        if route == "SELL":
            for bid in range(len(self.bids)):
                if self.bids[bid][0] < price_threshold:
                    return self.bids[bid - 1][0]
            return self.bids[-1][0]
        elif route == "BUY":
            for ask in range(len(self.asks)):
                if self.asks[ask][0] > price_threshold:
                    return self.asks[ask - 1][0]
            return self.asks[-1][0]
