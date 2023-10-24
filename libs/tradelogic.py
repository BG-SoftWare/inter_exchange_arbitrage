import logging
import os
import signal
import time
from copy import deepcopy
from decimal import Decimal
from decimal import ROUND_FLOOR

import definitions
from libs.bot_reporter.reporter import ReportBot
from libs.grpc_client import GRPCClient
from libs.misc import custom_logging as log, timeit_debug, timeit_info
from libs.report_to_db import report_generator as report_to_db
from libs.objects.order import Order
from libs.objects.order_book import OrderBook
from libs.objects.thread_with_return_value import ThreadWithReturnValue
from libs.objects.trade import Trade


class TradeLogic:
    balances_exchange_1 = {}
    balances_exchange_2 = {}
    balance_1_exchange_1 = 0
    balance_2_exchange_1 = 0
    balance_1_exchange_2 = 0
    balance_2_exchange_2 = 0
    last_update_time_exchange_1, last_update_time_exchange_2 = 0, 0
    time_exchange_1, order_book_exchange_1 = -1, None
    time_exchange_2, order_book_exchange_2 = -1, None
    flag_usdt_exchange_1, flag_usdt_exchange_2 = False, False
    filter_order = ["CANCELED", "FILLED"]

    def __init__(self, exchange_1: GRPCClient, exchange_2: GRPCClient, alerts: ReportBot, config: dict) -> None:
        self.exchange_2_price = None
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.alerts = alerts
        self.config = config
        self.state_time = 0
        self.threshold_time = 0
        self.balances_time = 0
        self.failed_order_count = 0
        self.empty_depth_start_time = 0
        self.is_alert_was_send = None
        self.graceful_quit_flag = False

    @timeit_debug
    def calc_buy_amount_for_second_exchange(self, buy_amount: Decimal, additional_percent: Decimal) -> Decimal:
        if additional_percent > 0:
            amount_with_additional = (buy_amount * 100) / (100 - additional_percent)
            amount_with_additional_int, amount_with_additional_fraction = str(amount_with_additional).split(".")
            if len(amount_with_additional_fraction) >= 9:
                if int(amount_with_additional_fraction[7]) == 9:
                    if int(amount_with_additional_fraction[8]) <= 5:
                        amount_with_additional_fraction = amount_with_additional_fraction[:8] + "9"
            return Decimal("{0}.{1}".format(amount_with_additional_int, amount_with_additional_fraction[:9]))
        else:
            return buy_amount

    @timeit_debug
    def wait_to_close_orders(self, order_exchange_1: Order, order_exchange_2: Order) -> tuple[Order, Order]:
        log(logging.info, "[BOT][Exchange 1][Exchange 2] Wait for close orders")
        exchange_1_timestamp, exchange_2_timestamp = time.time(), time.time()
        exchange_1_order_replacement, exchange_2_order_replacement = None, None
        while True:
            order_exchange_1_upd, order_exchange_2_upd = None, None
            if order_exchange_1 is not None:
                order_exchange_1_upd = self.exchange_1.get_order_status(order_exchange_1)
            if order_exchange_2 is not None:
                order_exchange_2_upd = self.exchange_2.get_order_status(order_exchange_2)
            if order_exchange_1_upd is not None:
                if order_exchange_1_upd.status not in self.filter_order:
                    if time.time() - exchange_1_timestamp < definitions.EXCHANGE_1_ORDER_DOWNTIME:
                        log(logging.info, "[BOT][Exchange 1] Wait for close order")
                    else:
                        log(logging.info, "[BOT][Exchange 1] Timestamp exceeded")
                        log(logging.info, "[BOT][Exchange 1] Collecting unresolved orders")
                        orders = self.exchange_1.get_unresolved_orders()
                        amount = 0
                        for order in orders:
                            if order.ticker == order_exchange_1.ticker:
                                amount = order.left
                        log(logging.info, "[BOT][Exchange 1] Cancelling order")
                        self.exchange_1.cancel_order(order_exchange_1)
                        log(logging.info, "[BOT][Exchange 1] Create market order")
                        exchange_1_order_replacement = self.exchange_1.place_market_order(order_exchange_1.route,
                                                                                          amount)
                        open("exchange_1_order_id_replaced.txt", "w").write(exchange_1_order_replacement.id)
                        log(logging.info, "[BOT][Exchange 1] Order placed")
            if order_exchange_2_upd is not None:
                if order_exchange_2_upd.status != "FILLED":
                    if time.time() - exchange_2_timestamp < definitions.EXCHANGE_2_ORDER_DOWNTIME:
                        log(logging.info, "[BOT][Exchange 2] Wait for close order")
                    else:
                        while True:
                            while True:
                                log(logging.info, "[BOT][Exchange 2] get orderbook")
                                order_book = self.get_order_books()
                                if order_book is None:
                                    continue
                                if order_book[0] < 0 and order_book[2] < 0:
                                    continue
                                else:
                                    break
                            if (self.calc_delta_between(self.exchange_2_price, Decimal(
                                    order_book[3].bids[2][0]) if order_exchange_2.route == "sell" else Decimal(
                                order_book[3].asks[2][0]), order_exchange_2.route) <
                                    definitions.ORDER_PRICE_DEVIATION_PERCENT):
                                break
                        log(logging.info, "[BOT][Exchange 2] Timestamp exceeded")
                        log(logging.info, "[BOT][Exchange 2] Collecting unresolved orders")
                        orders = self.exchange_2.get_unresolved_orders()
                        amount = 0
                        for order in orders:
                            if order.ticker == order_exchange_2.ticker:
                                amount = order.left
                        log(logging.info, "[BOT][Exchange 2] Cancelling order")
                        self.exchange_2.cancel_order(order_exchange_2)
                        log(logging.info, "[BOT][Exchange 2] Create market order")
                        log(logging.info, "[BOT][Exchange 2] Place order")
                        price = Decimal(order_book[3].bids[2][0]) if order_exchange_2.route == "sell" else (
                            Decimal(order_book[3].asks[2][0]))
                        exchange_2_order_replacement = self.exchange_2.place_order(order_exchange_2.route,
                                                                                   amount, price)
                        open("exchange_2_order_id_replaced.txt", "w").write(exchange_2_order_replacement.id)
                        log(logging.info, "[BOT][Exchange 2] Order placed")
                        log(logging.info, "[Exchange 2] Wait for close orders")
                        while True:
                            order_exchange_2_upd = self.exchange_2.get_order_status(exchange_2_order_replacement)
                            if order_exchange_2_upd.status == "FILLED":
                                log(logging.info, "[Exchange 2] Orders closed")
                                break

            if order_exchange_1_upd is not None and order_exchange_2_upd is None:
                if order_exchange_1_upd.status == "FILLED" or order_exchange_1_upd.status == "CANCELED":
                    log(logging.info, "[BOT][Exchange 1] Orders closed")
                    break
            elif order_exchange_1_upd is None and order_exchange_2_upd is not None:
                if order_exchange_2_upd.status == "FILLED":
                    log(logging.info, "[BOT][Exchange 2] Orders closed")
                    break

        return exchange_1_order_replacement, exchange_2_order_replacement

    @timeit_debug
    def fetch_balances(self):
        log(logging.info, "[BOT] Fetching balances from exchanges")
        self.balances_exchange_1 = self.exchange_1.get_balances()
        self.balances_exchange_2 = self.exchange_2.get_balances()
        if (self.balances_exchange_1[self.config["token_ticker"]].free +
                self.balances_exchange_2[self.config["token_ticker"]].free < self.balance_2_exchange_1 +
                self.balance_2_exchange_2):
            if (not self.config["sell_tail"] and (self.balances_exchange_1[self.config["token_ticker"]].free +
                                                  self.balances_exchange_2[self.config["token_ticker"]].free) -
                    (self.balance_2_exchange_1 + self.balance_2_exchange_2) > Decimal("0.00000001")):
                logging.critical("[BOT][BalanceChecker] Token balance decreased! I will be stopped NOW")
                raise RuntimeError("Token balance decreased! I will be stopped NOW")
        self.balance_1_exchange_1, self.balance_2_exchange_1 = self.balances_exchange_1["USDT"].free, \
            self.balances_exchange_1[self.config["token_ticker"]].free
        self.balance_1_exchange_2, self.balance_2_exchange_2 = self.balances_exchange_2["USDT"].free, \
            self.balances_exchange_2[self.config["token_ticker"]].free
        log(logging.info, "[BOT] Fetching balances from exchanges successful")
        if (self.balances_exchange_1["BNB"].free <= self.config["min_amount_for_trigger_buy_bnb"] and
                self.config["buy_bnb_in_bot"]):
            self.alerts.custom_text_message(
                "Running out of BNB {0}. I'm going to get some more".format(self.balances_exchange_1["BNB"].free))
            amount, price = self.exchange_1.buy_fee_token_on_market_for_usdt(self.config["amount_USDT_for_BNB_buy"])
            self.alerts.custom_text_message("Bought {0} BNB for {1} USDT at a price {2} USDT"
                                            .format(amount, self.config["amount_USDT_for_BNB_buy"], price))
            self.config["database"].change_bnb_price_in_profile(self.config["profile_id"], price)

    @timeit_debug
    def get_order_books(self) -> tuple | None:
        exchange_1_order_book = self.exchange_1.get_order_book()
        exchange_2_order_book = self.exchange_2.get_order_book()
        if (exchange_1_order_book is None or exchange_2_order_book is None or
                not exchange_1_order_book or not exchange_2_order_book):
            log(logging.info, "[BOT] Order book is None")
            return None
        time_exchange_1, exchange_1_order_book = exchange_1_order_book.timestamp, exchange_1_order_book
        time_exchange_2, exchange_2_order_book = exchange_2_order_book.timestamp, exchange_2_order_book
        return time_exchange_1, exchange_1_order_book, time_exchange_2, exchange_2_order_book

    @timeit_debug
    def wait_for_new_depth(self):
        while True:
            log(logging.info, "[BOT] Wait for new depth")
            order_book = self.get_order_books()
            if order_book is not None:
                if self.time_exchange_2 < order_book[2]:
                    break

    def handle_empty_depth(self, state: bool):
        if state:
            if self.empty_depth_start_time == 0:
                self.empty_depth_start_time = time.time()
            if time.time() - self.empty_depth_start_time > definitions.EMPTY_DEPTH_TIME and not self.is_alert_was_send:
                self.is_alert_was_send = True
        elif not state:
            if self.is_alert_was_send is None or self.is_alert_was_send:
                self.is_alert_was_send = False
                self.empty_depth_start_time = 0

    @timeit_info
    def try_trade(self, exchange_1_order_book: OrderBook, exchange_2_order_book: OrderBook) -> None:
        try:
            exchange_1_ask, exchange_1_ask_amount = exchange_1_order_book.get_ask()
            exchange_1_bid, exchange_1_bid_amount = exchange_1_order_book.get_bid()
            exchange_2_ask, exchange_2_ask_amount = exchange_2_order_book.get_ask()
            exchange_2_bid, exchange_2_bid_amount = exchange_2_order_book.get_bid()
            (exchange_1_ask, exchange_1_ask_amount,
             exchange_1_bid, exchange_1_bid_amount) = (Decimal(exchange_1_ask), Decimal(exchange_1_ask_amount),
                                                       Decimal(exchange_1_bid), Decimal(exchange_1_bid_amount))
            (exchange_2_bid, exchange_2_bid_amount,
             exchange_2_ask, exchange_2_ask_amount) = (Decimal(exchange_2_bid), Decimal(exchange_2_bid_amount),
                                                       Decimal(exchange_2_ask), Decimal(exchange_2_ask_amount))
        except:
            log(logging.warning, "[BOT] Empty depth")
            self.handle_empty_depth(True)
            return None

        self.handle_empty_depth(False)
        ether_to_interact = Decimal(self.config["amount_tokens_for_trade"])

        if ((exchange_2_bid - exchange_1_ask) / exchange_1_ask) * 100 >= Decimal(self.config["course_delta_value"]):
            exchange_1_calculate = exchange_1_order_book.calculate("BUY", ether_to_interact)
            if exchange_1_calculate is None:
                logging.info("[BOT][Exchange 1] Not Enough in depth")
                return None
            price_buy, avg_sol_price_buy, usdt_buy_amount = exchange_1_calculate
            log(logging.info, " [BOT] calculated buy on Exchange 1 {0} {1} {2}".format(price_buy, avg_sol_price_buy,
                                                                                       usdt_buy_amount))
            exchange_2_calculate = exchange_2_order_book.calculate("SELL", ether_to_interact)
            if exchange_2_calculate is None:
                log(logging.info, "[BOT][Exchange 2] Not Enough in depth")
                return None
            price_sell, avg_sol_price_sell, usdt_sell_amount = exchange_2_calculate
            log(logging.info,
                "[BOT] calculated sell on Exchange 2 {0} {1} {2}".format(price_sell, avg_sol_price_sell,
                                                                         usdt_sell_amount))
            usdt_sell_amount_minus_trade_fee = usdt_sell_amount * Decimal('0.002')
            usdt_buy_amount_minus_trade_fee = usdt_buy_amount * Decimal('0.00075')
            profit = (usdt_sell_amount - usdt_buy_amount -
                      usdt_buy_amount_minus_trade_fee - usdt_sell_amount_minus_trade_fee)
            if usdt_buy_amount <= Decimal(self.balance_1_exchange_1) and Decimal(self.balance_2_exchange_2) >= \
                    self.config["amount_tokens_for_trade"] and (profit > 0 or self.config["disable_profit_check"]):
                log(logging.info, " [BOT] Make trade BUY on Exchange 1 SELL on Exchange 2")
                exchange_1_price_buy, exchange_1_price_buy_fork = (exchange_1_order_book
                                                                   .order_fork(price_buy, "BUY",
                                                                               self.config["fork_step_exchange_1"]))
                exchange_2_price_sell_fork = exchange_2_order_book.order_with_max_price(exchange_1_price_buy_fork,
                                                                                        "SELL")
                self.exchange_2_price = exchange_2_price_sell_fork
                if (Decimal(self.balance_1_exchange_1) - exchange_1_price_buy *
                        ether_to_interact < definitions.USDT_CRITICAL_AMOUNT):
                    log(logging.info, " [BOT][Exchange 1] I dont have enough balance for placing fork order")
                    return None
                thread_exchange_1 = ThreadWithReturnValue(target=self.exchange_1.place_order,
                                                          args=("BUY", ether_to_interact,
                                                                exchange_1_price_buy_fork))
                thread_exchange_1.start()
                thread_exchange_2 = ThreadWithReturnValue(target=self.exchange_2.place_order,
                                                          args=("SELL", self.calc_sell_amount(ether_to_interact),
                                                                exchange_2_price_sell_fork))
                thread_exchange_2.start()
                log(logging.info, " [BOT] wait for end sending request")
                order_exchange_1, order_exchange_2 = None, None
                try:
                    order_exchange_1 = thread_exchange_1.waiting()
                    oid = order_exchange_1.id
                    open("exchange_1_order_id.txt", "w").write(oid)
                except BaseException as e:
                    log(logging.error, " [BOT][Exchange 1] Exception while trying placing order")
                    logging.error(e)

                log(logging.info, " [BOT] Exchange 1 order placed")

                try:
                    order_exchange_2 = thread_exchange_2.waiting()
                    oid = order_exchange_2.id
                    open("exchange_2_order_id.txt", "w").write(oid)
                except BaseException as e:
                    log(logging.error, "[BOT][exchange_2] Exception while trying placing order")
                    logging.error(e)

                self.alerts.custom_text_message("I've placed orders. I'm waiting for the close")
                exchange_1_order_replacement, exchange_2_order_replacement = self.wait_to_close_orders(
                    order_exchange_1, order_exchange_2)

                market_order, is_exchange_1 = None, None
                if order_exchange_1 is not None or order_exchange_2 is not None:
                    market_order, is_exchange_1 = self.handle_order_fail(order_exchange_1, order_exchange_2, "BUY",
                                                                         "SELL")

                if market_order is not None:
                    if is_exchange_1:
                        log(logging.info, " [BOT][Exchange 2] Fetching trading results")
                        exchange_2_trade = self.exchange_2.get_trade_info(order_exchange_2)
                        log(logging.info, " [BOT][Exchange 2] Results fetched successfully")
                        log(logging.info, " [BOT][Exchange 2] Fetching balances")
                        exchange_1_balances_after_trade = self.exchange_1.get_balances()
                        exchange_2_balances_after_trade = self.exchange_2.get_balances()
                        report_to_db(self.config, market_order, exchange_2_trade,
                                     {"BNB": self.config["price_BNB_when_buy"],
                                      "SOL": self.config["price_token_when_buy"]},
                                     ((exchange_2_bid - exchange_1_ask) / exchange_1_ask) * 100,
                                     exchange_1_balances_after_trade,
                                     exchange_2_balances_after_trade,
                                     None,
                                     exchange_1_order_book, exchange_2_order_book, exchange_1_ask, exchange_2_bid,
                                     exchange_1_order_book, exchange_2_order_book,
                                     avg_sol_price_buy,
                                     avg_sol_price_sell, self.config["token_ticker"], False)
                        self.fetch_balances()
                        self.failed_order_count += 1
                        return None
                    else:
                        exchange_1_trade = self.exchange_1.get_extended_trade_info(order_exchange_1)
                        exchange_1_balances_after_trade = self.exchange_1.get_balances()
                        exchange_2_balances_after_trade = self.exchange_2.get_balances()
                        report_to_db(self.config, exchange_1_trade, market_order,
                                     {"BNB": self.config["price_BNB_when_buy"],
                                      "SOL": self.config["price_token_when_buy"]},
                                     ((exchange_2_bid - exchange_1_ask) / exchange_1_ask) * 100,
                                     exchange_1_balances_after_trade,
                                     exchange_2_balances_after_trade,
                                     None,
                                     exchange_1_order_book, exchange_2_order_book, exchange_1_ask, exchange_2_bid,
                                     exchange_1_order_book, exchange_2_order_book,
                                     avg_sol_price_buy,
                                     avg_sol_price_sell, self.config["token_ticker"], False,
                                     "BUY Exchange 1 SELL Exchange 1")
                        self.fetch_balances()
                        self.failed_order_count += 1
                        return None

                exchange_1_trade, exchange_2_trade = self.handle_replaced_orders(order_exchange_1,
                                                                                 exchange_1_order_replacement,
                                                                                 order_exchange_2,
                                                                                 exchange_2_order_replacement)

                log(logging.info, "[BOT] Exchange 2 order placed")
                while True:
                    log(logging.info, "[BOT] Getting depth after trade")
                    try:
                        order_book = self.get_order_books()
                        exchange_1_order_book_after_trade, exchange_2_order_book_after_trade = (order_book[1],
                                                                                                order_book[3])
                        break
                    except:
                        log(logging.info, "[BOT] Empty depth")

                exchange_1_balances_after_trade = self.exchange_1.get_balances()
                exchange_2_balances_after_trade = self.exchange_2.get_balances()
                exchange_1_balance_1_after_trade, exchange_1_balance_2_after_trade = (
                    exchange_1_balances_after_trade["USDT"].free,
                    exchange_1_balances_after_trade[self.config["token_ticker"]].free)
                exchange_2_balance_1_after_trade, exchange_2_balance_2_after_trade = (
                    exchange_2_balances_after_trade["USDT"].free,
                    exchange_2_balances_after_trade[self.config["token_ticker"]].free)
                log(logging.info, " [BOT] balances Exchange 1 " + str(exchange_1_balance_1_after_trade) + str(
                    exchange_1_balance_2_after_trade))
                log(logging.info, " [BOT] balances Exchange 2 " + str(exchange_2_balance_1_after_trade) + str(
                    exchange_2_balance_2_after_trade))
                log(logging.info, " [BOT] Results fetched successfully")
                log(logging.info, " [BOT] Save results to db")
                report_to_db(self.config, exchange_1_trade, exchange_2_trade,
                             {"BNB": self.config["price_BNB_when_buy"], "SOL": self.config["price_token_when_buy"]},
                             ((exchange_2_bid - exchange_1_ask) / exchange_1_ask) * 100,
                             exchange_1_balances_after_trade,
                             exchange_2_balances_after_trade,
                             None,
                             exchange_1_order_book, exchange_2_order_book, exchange_1_ask, exchange_2_bid,
                             exchange_1_order_book_after_trade, exchange_2_order_book_after_trade,
                             avg_sol_price_buy,
                             avg_sol_price_sell, self.config["token_ticker"])
                log(logging.info, " [BOT] Saved successfully")
                log(logging.info, " [BOT] Send report to telegram")
                self.alerts.report_trade(exchange_1_trade, exchange_2_trade,
                                         ((exchange_2_bid - exchange_1_ask) / exchange_1_ask) * 100)
                log(logging.info, " [BOT] Sent successfully")
                log(logging.info, "[BOT] Wait for new depth from exchange_2")
                self.wait_for_new_depth()
                self.failed_order_count = 0
                if (self.balance_1_exchange_1 + self.balance_1_exchange_2 > exchange_1_balance_1_after_trade +
                        exchange_2_balance_1_after_trade):
                    log(logging.error, "[BOT] Balance has decreased")
                    self.fetch_balances()
                else:
                    self.fetch_balances()
            if Decimal(self.balance_2_exchange_2) < self.config["amount_tokens_for_trade"]:
                log(logging.info, "[BOT] Not enough tokens on exchange_2")
            if usdt_buy_amount > Decimal(self.balance_1_exchange_1):
                log(logging.info, "[BOT] Not enough USDT on exchange_1")
            if profit <= 0:
                log(logging.info, "[BOT] Estimated profit <= 0")

        elif ((exchange_1_bid - exchange_2_ask) / exchange_2_ask) * 100 >= Decimal(
                self.config["course_delta_value"]):
            exchange_2_calculate = exchange_2_order_book.calculate("BUY", ether_to_interact)
            if exchange_2_calculate is None:
                logging.info("[BOT][Exchange 2] Not Enough in depth")
                return None
            price_buy, avg_sol_price_buy, usdt_buy_amount = exchange_2_calculate
            usdt_buy_amount_minus_trade_fee = usdt_buy_amount * Decimal('0.002')
            log(logging.info, " [BOT] calculated buy on Exchange 2 {0} {1} {2}".format(price_buy, avg_sol_price_buy,
                                                                                       usdt_buy_amount))
            exchange_1_calculate = exchange_1_order_book.calculate("SELL", ether_to_interact)
            if exchange_1_calculate is None:
                logging.info("[BOT][Exchange 1] Not Enough in depth")
                return None
            price_sell, avg_sol_price_sell, usdt_sell_amount = exchange_1_calculate
            usdt_sell_amount_minus_trade_fee = usdt_sell_amount * Decimal('0.00075')
            log(logging.info,
                "[BOT] calculated sell on exchange_1 {0} {1} {2}".format(price_sell,
                                                                         avg_sol_price_sell,
                                                                         usdt_sell_amount))
            profit = (usdt_sell_amount - usdt_buy_amount -
                      usdt_buy_amount_minus_trade_fee - usdt_sell_amount_minus_trade_fee)

            if usdt_buy_amount <= Decimal(self.balance_1_exchange_2) and Decimal(self.balance_2_exchange_1) >= \
                    self.config["amount_tokens_for_trade"] and (profit > 0 or self.config["disable_profit_check"]):
                log(logging.info, " [BOT] go trade buy on exchange_2 sell on exchange_1")

                exchange_1_price_sell, exchange_1_price_sell_fork = (
                    exchange_1_order_book.order_fork(price_sell, "SELL", self.config["fork_step_exchange_1"]))
                exchange_2_buy_fork_price = exchange_2_order_book.order_with_max_price(exchange_1_price_sell, "BUY")
                log(logging.info, exchange_2_buy_fork_price)
                self.exchange_2_price = exchange_2_buy_fork_price
                exchange_2_buy_price = price_buy
                if Decimal(self.balance_1_exchange_2) - (exchange_2_buy_price * ether_to_interact) < 3:
                    log(logging.info, " [BOT][exchange_2] I dont have enough balance for placing fork order")
                    return None
                thread_exchange_1 = ThreadWithReturnValue(target=self.exchange_1.place_order,
                                                          args=(
                                                              "SELL", ether_to_interact,
                                                              exchange_1_price_sell_fork))
                thread_exchange_1.start()
                ether_to_interact_additional = self.calc_buy_amount_for_second_exchange(
                    ether_to_interact, self.config["buy_more_tokens_on_second_exchange_percent"])
                thread_exchange_2 = ThreadWithReturnValue(target=self.exchange_2.place_order,
                                                          args=("buy", ether_to_interact_additional,
                                                                exchange_2_buy_fork_price))
                thread_exchange_2.start()
                log(logging.info, " [BOT] wait for ending sending request")
                order_exchange_1, order_exchange_2 = None, None
                try:
                    order_exchange_1 = thread_exchange_1.waiting()
                    oid = order_exchange_1.id
                    open("exchange_1_order_id.txt", "w").write(oid)
                except BaseException as e:
                    log(logging.error, "[BOT][Exchange 1] Exception while trying placing order")
                    logging.error(e)

                log(logging.info, " [BOT] Exchange 1 order placed")

                try:
                    order_exchange_2 = thread_exchange_2.waiting()
                    oid = order_exchange_2.id
                    open("exchange_2_order_id.txt", "w").write(oid)
                except BaseException as e:
                    log(logging.error, "[BOT][Exchange 2] Exception while trying placing order")
                    logging.error(e)
                while True:
                    log(logging.info, " [BOT] Getting depth after trade")
                    try:
                        order_book = self.get_order_books()
                        (exchange_1_order_book_after_trade,
                         exchange_2_order_book_after_trade) = order_book[1], order_book[3]
                        break
                    except:
                        log(logging.info, " [BOT] Empty depth")

                self.alerts.custom_text_message("I've placed orders. I'm waiting for the close")
                exchange_1_order_replacement, exchange_2_order_replacement = self.wait_to_close_orders(
                    order_exchange_1,
                    order_exchange_2)
                market_order, is_exchange_1 = None, None
                if order_exchange_1 is not None or order_exchange_2 is not None:
                    market_order, is_exchange_1 = self.handle_order_fail(order_exchange_1, order_exchange_2, "SELL",
                                                                         "BUY")

                if market_order is not None:
                    if is_exchange_1:
                        log(logging.info, " [BOT][Exchange 2] Fetching trading results")
                        exchange_2_trade = self.exchange_2.get_trade_info(order_exchange_2)
                        log(logging.info, " [BOT][Exchange 2] Results fetched successfully")
                        log(logging.info, " [BOT][Exchange 2] Fetching balances")
                        exchange_1_balances_after_trade = self.exchange_1.get_balances()
                        exchange_2_balances_after_trade = self.exchange_2.get_balances()
                        report_to_db(self.config, market_order, exchange_2_trade,
                                     {"BNB": self.config["price_BNB_when_buy"],
                                      "SOL": self.config["price_token_when_buy"]},
                                     ((exchange_1_bid - exchange_2_ask) / exchange_2_ask) * 100,
                                     exchange_1_balances_after_trade,
                                     exchange_2_balances_after_trade,
                                     None,
                                     exchange_1_order_book, exchange_2_order_book, exchange_1_ask, exchange_2_bid,
                                     exchange_1_order_book, exchange_2_order_book,
                                     avg_sol_price_buy,
                                     avg_sol_price_sell, self.config["token_ticker"], False)
                        self.fetch_balances()
                        self.failed_order_count += 1
                        return None
                    else:
                        exchange_1_trade = self.exchange_1.get_extended_trade_info(order_exchange_1)
                        exchange_1_balances_after_trade = self.exchange_1.get_balances()
                        exchange_2_balances_after_trade = self.exchange_2.get_balances()
                        report_to_db(self.config, exchange_1_trade, market_order,
                                     {"BNB": self.config["price_BNB_when_buy"],
                                      "SOL": self.config["price_token_when_buy"]},
                                     ((exchange_1_bid - exchange_2_ask) / exchange_2_ask) * 100,
                                     exchange_1_balances_after_trade,
                                     exchange_2_balances_after_trade,
                                     None,
                                     exchange_1_order_book, exchange_2_order_book, exchange_1_ask, exchange_2_bid,
                                     exchange_1_order_book, exchange_2_order_book,
                                     avg_sol_price_buy,
                                     avg_sol_price_sell, self.config["token_ticker"], False,
                                     "sell exchange_1 buy exchange_1")
                        self.fetch_balances()
                        self.failed_order_count += 1
                        return None

                exchange_1_trade, exchange_2_trade = self.handle_replaced_orders(order_exchange_1,
                                                                                 exchange_1_order_replacement,
                                                                                 order_exchange_2,
                                                                                 exchange_2_order_replacement)

                exchange_1_balances_after_trade = self.exchange_1.get_balances()
                exchange_2_balances_after_trade = self.exchange_2.get_balances()
                (exchange_1_balance_1_after_trade,
                 exchange_1_balance_2_after_trade) = (exchange_1_balances_after_trade["USDT"].free,
                                                      exchange_1_balances_after_trade[self.config["token_ticker"]]
                                                      .free)
                (exchange_2_balance_1_after_trade,
                 exchange_2_balance_2_after_trade) = (exchange_2_balances_after_trade["USDT"].free,
                                                      exchange_2_balances_after_trade[self.config["token_ticker"]]
                                                      .free)
                log(logging.info, " [BOT] balances Exchange 1 " + str(exchange_1_balance_1_after_trade) + str(
                    exchange_1_balance_2_after_trade))
                log(logging.info, " [BOT] balances Exchange 2 " + str(exchange_2_balance_1_after_trade) + str(
                    exchange_2_balance_2_after_trade))
                log(logging.info, " [BOT] Results fetched successfully")
                log(logging.info, " [BOT] Save results to db")
                report_to_db(self.config, exchange_1_trade, exchange_2_trade,
                             {"BNB": self.config["price_BNB_when_buy"], "SOL": self.config["price_token_when_buy"]},
                             ((exchange_1_bid - exchange_2_ask) / exchange_2_ask) * 100,
                             exchange_1_balances_after_trade,
                             exchange_2_balances_after_trade,
                             None,
                             exchange_1_order_book, exchange_2_order_book, exchange_1_bid, exchange_2_ask,
                             exchange_1_order_book_after_trade, exchange_2_order_book_after_trade,
                             avg_sol_price_sell,
                             avg_sol_price_buy, self.config["token_ticker"])
                log(logging.info, " [BOT] Saved successfully")
                log(logging.info, " [BOT] Send report to telegram")
                self.alerts.report_trade(exchange_1_trade, exchange_2_trade,
                                         ((exchange_1_bid - exchange_2_ask) / exchange_2_ask) * 100)
                log(logging.info, " [BOT] Sent successfully")
                log(logging.info, "[BOT] Wait for new depth from exchange_2")
                self.wait_for_new_depth()
                self.failed_order_count = 0
                if (self.balance_1_exchange_1 + self.balance_1_exchange_2 > exchange_1_balance_1_after_trade +
                        exchange_2_balance_1_after_trade):
                    log(logging.info, " [BOT] Balance has decreased")
                    self.fetch_balances()
                else:
                    self.fetch_balances()
            if Decimal(self.balance_2_exchange_1) < self.config["amount_tokens_for_trade"]:
                log(logging.info, " [BOT] Not enough tokens on Exchange 1")
            if usdt_buy_amount > Decimal(self.balance_1_exchange_2):
                log(logging.info, " [BOT] Not enough USDT on Exchange 2")
            if profit <= 0:
                log(logging.info, " [BOT] Estimated profit <= 0")

    @timeit_debug
    def handle_replaced_orders(self, order_exchange_1, exchange_1_order_replacement, order_exchange_2,
                               exchange_2_order_replacement) -> (Trade, Trade):
        exchange_1_trade, exchange_2_trade = None, None
        if exchange_1_order_replacement is None and exchange_2_order_replacement is None:
            log(logging.info, "[BOT] All orders placed successful")
            log(logging.info, "[BOT][Exchange 1] Fetching order")
            exchange_1_trade = self.exchange_1.get_extended_trade_info(order_exchange_1)
            log(logging.info, "[BOT][Exchange 2] Fetching order")
            exchange_2_trade = self.exchange_2.get_trade_info(order_exchange_2)
        elif exchange_1_order_replacement is not None and exchange_2_order_replacement is None:
            log(logging.info, "[BOT][Exchange 1] Order on exchange_1 has been replaced")
            log(logging.info, "[BOT][Exchange 1] Fetching old order")
            exchange_1_trade_old = self.exchange_1.get_extended_trade_info(order_exchange_1)
            log(logging.info, "[BOT][Exchange 1] Order fetched")
            log(logging.info, "[BOT][Exchange 1] Fetch new order")
            exchange_1_trade_new = self.exchange_1.get_extended_trade_info(exchange_1_order_replacement)
            if exchange_1_trade_new.token_amount == Decimal(self.config["amount_tokens_for_trade"]):
                log(logging.info, "[BOT][Exchange 1] Order has been replaced completely")
                exchange_1_trade = exchange_1_trade_new
            else:
                log(logging.info, "[BOT][Exchange 1] Order has been replaced particularly")
                exchange_1_trade = deepcopy(exchange_1_trade_old)
                exchange_1_trade.fee_amount = list(exchange_1_trade_old.fee_amount) + list(
                    exchange_1_trade_new.fee_amount)
                exchange_1_trade.fee_currency = list(exchange_1_trade_old.fee_currency) + list(
                    exchange_1_trade_new.fee_currency)
                exchange_1_trade.order_price = ((exchange_1_trade_old.order_total *
                                                 exchange_1_trade_old.token_amount +
                                                 exchange_1_trade_new.order_total *
                                                 exchange_1_trade_new.token_amount) /
                                                (exchange_1_trade_new.token_amount +
                                                 exchange_1_trade_old.token_amount))
                exchange_1_trade.order_total = exchange_1_trade_old.order_total + exchange_1_trade_new.order_total
                exchange_1_trade.token_amount = exchange_1_trade_new.token_amount + exchange_1_trade_old.token_amount
            exchange_2_trade = self.exchange_2.get_trade_info(order_exchange_2)

        elif exchange_1_order_replacement is None and exchange_2_order_replacement is not None:
            log(logging.info, "[BOT][Exchange 2] Order on exchange_2 has been replaced")
            log(logging.info, "[BOT][Exchange 2] Fetching old order")
            exchange_2_trade_old = self.exchange_2.get_trade_info(order_exchange_2)
            log(logging.info, "[BOT][Exchange 2] Order fetched")
            log(logging.info, "[BOT][Exchange 2] Fetch new order")
            exchange_2_trade_new = self.exchange_2.get_trade_info(exchange_2_order_replacement)
            if exchange_2_trade_new.token_amount == Decimal(self.config["amount_tokens_for_trade"]):
                log(logging.info, "[BOT][Exchange 2] Order has been replaced completely")
                exchange_2_trade = exchange_2_trade_new
            else:
                log(logging.info, "[BOT][Exchange 2] Order has been replaced particularly")
                exchange_2_trade = deepcopy(exchange_2_trade_old)
                exchange_2_trade.fee_amount = exchange_2_trade_old.fee_amount + exchange_2_trade_new.fee_amount
                exchange_2_trade.order_price = ((exchange_2_trade_old.order_total *
                                                 exchange_2_trade_old.token_amount +
                                                 exchange_2_trade_new.order_total *
                                                 exchange_2_trade_new.token_amount) /
                                                (exchange_2_trade_new.token_amount +
                                                 exchange_2_trade_old.token_amount))
                exchange_2_trade.order_total = exchange_2_trade_old.order_total + exchange_2_trade_new.order_total
                exchange_2_trade.token_amount = exchange_2_trade_new.token_amount + exchange_2_trade_old.token_amount
            exchange_1_trade = self.exchange_1.get_extended_trade_info(order_exchange_1)

        elif exchange_1_order_replacement is not None and exchange_2_order_replacement is not None:
            log(logging.info, "[BOT] Order on both exchanges has been replaced")
            log(logging.info, "[BOT][Exchange 1] Fetching old order")
            self.exchange_1.get_extended_trade_info(order_exchange_1)
            log(logging.info, "[BOT][Exchange 1] Order fetched")
            log(logging.info, "[BOT][Exchange 1] Fetch new order")
            exchange_1_trade_new = self.exchange_1.get_extended_trade_info(exchange_1_order_replacement)
            log(logging.info, "[BOT][exchange_2] Fetching old order")
            exchange_2_trade_old = self.exchange_2.get_trade_info(order_exchange_2)
            log(logging.info, "[BOT][exchange_2] Order fetched")
            log(logging.info, "[BOT][exchange_2] Fetch new order")
            exchange_2_trade_new = self.exchange_2.get_trade_info(exchange_2_order_replacement)
            if exchange_1_order_replacement.token_amount == Decimal(self.config["amount_tokens_for_trade"]):
                log(logging.info, "[BOT][Exchange 1] Order has been replaced completely")
                exchange_1_trade = exchange_1_trade_new
            else:
                log(logging.info, "[BOT][Exchange 1] Order has been replaced particularly")
            if exchange_2_order_replacement.token_amount == Decimal(self.config["amount_tokens_for_trade"]):
                log(logging.info, "[BOT][exchange_2] Order has been replaced completely")
                exchange_2_trade = exchange_2_trade_new
            else:
                log(logging.info, "[BOT][exchange_2] Order has been replaced particularly")
                exchange_2_trade = deepcopy(exchange_2_trade_old)
                exchange_2_trade.fee_amount = exchange_2_trade_old.fee_amount + exchange_2_trade_new.fee_amount
                exchange_2_trade.order_price = ((exchange_2_trade_old.order_total *
                                                 exchange_2_trade_old.token_amount +
                                                 exchange_2_trade_new.order_total *
                                                 exchange_2_trade_new.token_amount) /
                                                (exchange_2_trade_new.token_amount +
                                                 exchange_2_trade_old.token_amount))
                exchange_2_trade.order_total = exchange_2_trade_old.order_total + exchange_2_trade_new.order_total
                exchange_2_trade.token_amount = exchange_2_trade_new.token_amount + exchange_2_trade_old.token_amount
        return exchange_1_trade, exchange_2_trade

    @timeit_debug
    def handle_order_fail(self, order_exchange_1: OrderBook, order_exchange_2: OrderBook, route_exchange_1: str,
                          route_exchange_2: str) -> (Trade, bool):
        if order_exchange_1 is None and order_exchange_2 is None:
            log(logging.info, "[BOT][FailSave] Orders have not been placed anywhere. Missing the signal.")
        elif order_exchange_1 is None:
            log(logging.info,
                "[BOT][FailSave][Exchange 1] I dont placed order on Exchange 1. Trying placing market order")
            market_order = self.exchange_1.place_market_order(route_exchange_1, self.config["amount_tokens_for_trade"])
            log(logging.info, "[BOT][FailSave][Exchange 1] Get trade info")
            exchange_1_trade = self.exchange_1.get_extended_trade_info(market_order)
            return exchange_1_trade, True
        elif order_exchange_2 is None:
            log(logging.info,
                "[BOT][FailSave][Exchange 2] I dont placed order on Exchange 2. "
                "Trying placing reverse market order on Exchange 1")
            route = "BUY" if route_exchange_2 == "buy" else "SELL"
            market_order = self.exchange_1.place_market_order(route, self.config["amount_tokens_for_trade"])
            log(logging.info, "[BOT][FailSave][Exchange 2] Get trade info")
            exchange_1_trade = self.exchange_1.get_extended_trade_info(market_order)
            return exchange_1_trade, False

    def fix_start_balances_in_trade(self):
        mock_trade = Trade("-1", 0, "", "", "", 0, "BNB", 1, 1, 1)
        exchange_1_balances_after_trade = self.exchange_1.get_balances()
        exchange_2_balances_after_trade = self.exchange_2.get_balances()
        report_to_db(self.config, mock_trade, mock_trade,
                     {"BNB": self.config["price_BNB_when_buy"],
                      "SOL": self.config["price_token_when_buy"]},
                     0, exchange_1_balances_after_trade,
                     exchange_2_balances_after_trade,
                     0,
                     OrderBook("", [], [], -1), OrderBook("", [], [], -1), 0, 0,
                     OrderBook("", [], [], -1), OrderBook("", [], [], -1),
                     0,
                     0, self.config["token_ticker"], True,
                     "Start balances only. Not real trade.")

    def graceful_quit(self, sig_num):
        if sig_num == signal.SIGUSR1:
            log(logging.info,
                "[SignalHandler] Received signal for graceful stop. Bot will be stopped after try_trade is completed.")
            self.graceful_quit_flag = True
        pass

    @staticmethod
    def delete_order_id_txts():
        for file_with_order_id in ["exchange_1_order_id.txt", "exchange_2_order_id.txt",
                                   "exchange_2_order_id_replaced.txt",
                                   "exchange_1_order_id_replaced.txt"]:
            try:
                os.remove(file_with_order_id)
            except:
                pass

    @timeit_info
    def run_trade(self):
        signal.signal(signal.SIGUSR1, self.graceful_quit)
        count_trades = self.config["database"].count_trades_by_profile_id(self.config["profile_id"])
        if count_trades == 0:
            self.fix_start_balances_in_trade()
        self.fetch_balances()
        while True:
            order_book = self.get_order_books()
            if order_book is None:
                continue
            if order_book[0] < 0 and order_book[2] < 0:
                continue
            time_exchange_1, exchange_1_order_book = order_book[0], order_book[1]
            time_exchange_2, exchange_2_order_book = order_book[2], order_book[3]
            if time_exchange_1 != self.last_update_time_exchange_1:
                if time.time() * 1000 - time_exchange_1 > definitions.EXCHANGE_1_ORDERBOOK_TIMEOUT_MS:
                    log(logging.info, "[BOT] Data is not actual")
                    continue
                log(logging.info, " [BOT] Trying to calculate")
                if self.failed_order_count >= definitions.FAILED_ORDER_COUNT:
                    log(logging.info, "Failed order amount >= {0}".format(definitions.FAILED_ORDER_COUNT))
                    raise RuntimeError("Failed order amount >= {0}".format(definitions.FAILED_ORDER_COUNT))
                self.try_trade(exchange_1_order_book, exchange_2_order_book)
                self.delete_order_id_txts()
                if self.graceful_quit_flag:
                    log(logging.info, "[ExitHandler] Graceful quit flag activated. Stopping bot")
                    break

    def calc_sell_amount(self, ether_to_interact):
        if self.config["sell_tail"]:
            if self.balance_2_exchange_2 // ether_to_interact == 1:
                return self.balance_2_exchange_2.quantize(Decimal("1.00000000"), ROUND_FLOOR)
            else:
                return ether_to_interact
        else:
            return ether_to_interact

    @staticmethod
    def calc_delta_between(price, replace_price, route):
        if route.lower() == "buy":
            return (replace_price - price) / price * 100
        elif route.lower() == "sell":
            return (price - replace_price) / replace_price * 100
