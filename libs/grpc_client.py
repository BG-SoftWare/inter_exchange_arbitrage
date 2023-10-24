import logging
import time
import traceback
from decimal import Decimal

import grpc

import definitions
import proto.adapter_pb2 as service_entities
import proto.adapter_pb2_grpc as rpc
from libs.misc import custom_logging as log
from libs.misc import timeit_info, timeit_debug
from libs.objects.balance import Balance
from libs.objects.extended_trade import ExtendedTrade
from libs.objects.open_order import OpenOrder
from libs.objects.order import Order
from libs.objects.order_book import OrderBook
from libs.objects.trade import Trade


class GRPCClient:
    def __init__(self, address):
        channel = grpc.insecure_channel(address)
        self.connection = rpc.AdapterStub(channel)

    def get_order_book(self):
        return self.get_depth()

    @timeit_debug
    def get_depth(self):
        for attempt in range(definitions.RETRY_COUNT):
            try:
                data = self.connection.get_depth(service_entities.Empty())
                symbol = ""
                bids = []
                asks = []
                if data.error == "":
                    for i in data.bids:
                        bids.append([Decimal(i.price), Decimal(i.amount)])
                    for i in data.asks:
                        asks.append([Decimal(i.price), Decimal(i.amount)])
                    timestamp = data.timestamp
                    return OrderBook(symbol, bids, asks, timestamp)
            except BaseException:
                traceback_message = traceback.format_exc()
                log(logging.critical, "[GRPCClient]{0}".format(traceback_message))
            log(logging.debug,
                "[GRPCClient] get_depth retry after {0} secs".format(definitions.RETRY_TIMEOUT))
            time.sleep(definitions.RETRY_TIMEOUT)
        raise ConnectionError

    @timeit_info
    def place_order(self, route, token_amount, token_price):
        data = self.connection.place_order(
            service_entities.RequestCreateOrder(route=route, token_amount=str(token_amount),
                                                token_price=str(token_price)))
        if data.error == "":
            log(logging.info, "[GRPC] order with id {0} placed successful".format(data.id))
            return Order(order_id=data.id, time=data.time, ticker=data.ticker, status=data.status, route=data.route)
        else:
            raise ConnectionError(data.error)

    @timeit_debug
    def cancel_order(self, order):
        service_entity_order = service_entities.Order(id=order.id, time=order.time, ticker=order.ticker,
                                                      status=order.status, route=order.route)
        data = self.connection.cancel_order(service_entities.RequestCancelOrder(order=service_entity_order))
        if data.error == "":
            return True
        else:
            raise ConnectionError(data.error)

    @timeit_debug
    def get_balances(self):
        balances = {}
        error_message = ""
        for attempt in range(definitions.RETRY_COUNT):
            try:
                data = self.connection.get_balances(service_entities.Empty())
                if data.error == "":
                    for balance in data.balances:
                        balances[balance.asset] = Balance(balance.asset, Decimal(balance.free), Decimal(balance.locked))
                    log(logging.debug,
                        "[GRPCClient] get_balances request was processed successfully after {0} attempts".format(
                            attempt))
                    return balances
                else:
                    error_message = data.error
                    log(logging.critical, "[GRPCClient]{0}".format(error_message))
            except BaseException:
                traceback_message = traceback.format_exc()
                log(logging.critical, "[GRPCClient]{0}".format(traceback_message))
                error_message = traceback_message
            log(logging.debug,
                "[GRPCClient] get_balances retry after {0} secs".format(definitions.RETRY_TIMEOUT))
            time.sleep(definitions.RETRY_TIMEOUT)
        raise ConnectionError(error_message)

    @timeit_debug
    def get_trade_info(self, order):
        error_message = ""
        for attempt in range(definitions.RETRY_COUNT):
            try:
                service_entity_order = service_entities.Order(id=order.id, time=order.time, ticker=order.ticker,
                                                              status=order.status, route=order.route)
                data = self.connection.get_trade_info(service_entities.RequestTradeInfo(order=service_entity_order))
                if data.error == "":
                    log(logging.debug,
                        "[GRPCClient] get_trade_info request was processed successfully after {0} attempts".format(
                            attempt))
                    return Trade(data.id, data.time, data.ticker, data.status, data.route, Decimal(data.fee_amount),
                                 data.fee_currency,
                                 Decimal(data.order_price), Decimal(data.order_total), Decimal(data.token_amount))
                else:
                    error_message = data.error
                    log(logging.critical, "[GRPCClient]{0}".format(error_message))
            except:
                traceback_message = traceback.format_exc()
                log(logging.critical, "[GRPCClient]{0}".format(traceback_message))
                error_message = traceback_message
            log(logging.debug,
                "[GRPCClient] get_trade_info retry after {0} secs".format(definitions.RETRY_TIMEOUT))
            time.sleep(definitions.RETRY_TIMEOUT)
        raise ConnectionError(error_message)

    @timeit_debug
    def get_order_status(self, order):
        error_message = ""
        for attempt in range(definitions.RETRY_COUNT):
            try:
                service_entity_order = service_entities.Order(id=order.id, time=order.time, ticker=order.ticker,
                                                              status=order.status, route=order.route)
                data = self.connection.get_order_status(service_entity_order)
                if data.error == "":
                    log(logging.debug,
                        "[GRPCClient] get_order_status request was processed successfully after {0} attempts".format(
                            attempt))
                    return Order(data.id, data.time, data.ticker, data.status, data.route)
                else:
                    error_message = data.error
                    log(logging.critical, "[GRPCClient]{0}".format(error_message))
            except BaseException:
                traceback_message = traceback.format_exc()
                log(logging.critical, "[GRPCClient]{0}".format(traceback_message))
                error_message = traceback_message
            log(logging.debug,
                "[GRPCClient] get_order_status retry after {0} secs".format(definitions.RETRY_TIMEOUT))
            time.sleep(definitions.RETRY_TIMEOUT)
        raise ConnectionError(error_message)

    @timeit_info
    def buy_fee_token_on_market_for_usdt(self, amount_usdt):
        data = self.connection.buy_fee_token_on_market_for_usdt(
            service_entities.BuyFeeTokenRequest(usdt_amount=str(amount_usdt)))
        if data.error == "":
            return Decimal(data.token_amount), Decimal(data.token_price)
        else:
            raise ConnectionError(data.error)

    @timeit_info
    def place_market_order(self, route, token_amount):
        data = self.connection.place_market_order(
            service_entities.MarketOrderRequest(route=route, token_amount=str(token_amount)))
        if data.error == "":
            log(logging.info, "[GRPC] order with id {0} placed successful".format(data.id))
            return Order(data.id, data.time, data.ticker, data.status, data.route)
        else:
            return ConnectionError(data.error)

    @timeit_debug
    def ping(self):
        data = self.connection.ping(service_entities.Empty())
        return int(time.time() * 1000) - data.time

    @timeit_debug
    def get_unresolved_orders(self):
        data = self.connection.get_open_orders(service_entities.Empty())
        if data.error == "":
            orders = []
            for order in data.orders:
                orders.append(OpenOrder(order.id, order.time, order.ticker, order.status, order.route, order.left))
            return orders
        else:
            raise ConnectionError(data.error)

    @timeit_debug
    def get_extended_trade_info(self, order):
        error_message = ""
        for attempt in range(definitions.RETRY_COUNT):
            try:
                service_entity_order = service_entities.Order(id=order.id, time=order.time, ticker=order.ticker,
                                                              status=order.status, route=order.route)
                data = self.connection.get_trade_info_extended(
                    service_entities.RequestTradeInfo(order=service_entity_order))
                if data.error == "":
                    log(logging.debug,
                        "[GRPCClient] get_trade_info request was processed successfully after {0} attempts".format(
                            attempt))
                    return ExtendedTrade(data.id, data.time, data.ticker, data.status, data.route, data.fee_amount,
                                         data.fee_currency,
                                         Decimal(data.order_price), Decimal(data.order_total),
                                         Decimal(data.token_amount))
                else:
                    error_message = data.error
                    log(logging.critical, "[GRPCClient]{0}".format(error_message))
            except:
                traceback_message = traceback.format_exc()
                log(logging.critical, "[GRPCClient]{0}".format(traceback_message))
                error_message = traceback_message
            log(logging.debug,
                "[GRPCClient] get_trade_info retry after {0} secs".format(definitions.RETRY_TIMEOUT))
            time.sleep(definitions.RETRY_TIMEOUT)
        raise ConnectionError(error_message)
