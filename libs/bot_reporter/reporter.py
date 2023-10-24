import datetime
from decimal import Decimal

import requests

from libs.objects.trade import Trade


class ReportBot:
    def __init__(self, bot_token, chat_id, config):
        self.__bot_token = bot_token
        self.__chat_id = chat_id
        self.__config = config

    def report_trade(self, trade_exchange_1: Trade, trade_exchange_2: Trade, delta_bid_ask: Decimal):
        if self.__bot_token == "" and self.__chat_id == 0:
            return
        profit, all_profit = self.__config["database"].get_last_profit_and_all_profit(self.__config["profile_id"])
        fmt_params = {
            "direction": "buy on Exchange 1 sell on Exchange 2" if trade_exchange_1.route == "BUY" else
            "sell on Exchange 1 buy on Exchange 2",
            "course_delta": str(delta_bid_ask),
            "profit": str(profit),
            "all_profit": str(all_profit),
            "id_exchange_1": trade_exchange_1.id,
            "time_exchange_1": datetime.datetime.fromtimestamp(int(trade_exchange_1.time / 1000)),
            "route_exchange_1": trade_exchange_1.route.upper(),
            "avg_price_exchange_1": Decimal(trade_exchange_1.order_total) / Decimal(trade_exchange_1.token_amount),
            "id_exchange_2": trade_exchange_2.id,
            "time_exchange_2": datetime.datetime.fromtimestamp(int(trade_exchange_2.time / 1000)),
            "route_exchange_2": trade_exchange_2.route.upper(),
            "avg_price_exchange_2": Decimal(trade_exchange_2.order_total) / Decimal(trade_exchange_2.token_amount),

        }
        params = {
            "chat_id": str(self.__chat_id),
            "text": f"""
                    New Trade
                    Direction: {fmt_params["direction"]}
                    Course delta: {fmt_params["course_delta"]}
                    Profit: {fmt_params["profit"]}
                    Total profit: {fmt_params["all_profit"]}
                    ID Exchange 1: {fmt_params["id_exchange_1"]}
                    Time Exchange 1: {fmt_params["time_exchange_1"]}
                    Price {fmt_params["route_exchange_1"]} on Exchange 1: {fmt_params["avg_price_exchange_1"]}
                    ID Exchange 2: {fmt_params["id_exchange_2"]}
                    Time Exchange 2: {fmt_params["time_exchange_2"]}
                    Price {fmt_params["route_exchange_2"]} on Exchange 2: {fmt_params["avg_price_exchange_2"]}
                    """,
        }
        response = requests.post(f"https://api.telegram.org/bot{self.__bot_token}/sendMessage", params=params)
        if response.status_code != 200:
            raise ConnectionError

    def crash_report(self, text):
        if self.__bot_token == "" and self.__chat_id == 0:
            return
        params = {"chat_id": str(self.__chat_id), "text": f"The bot has stopped working \n{text}"}
        r = requests.post(f"https://api.telegram.org/bot{self.__bot_token}/sendMessage", params=params)
        if r.status_code != 200:
            raise ConnectionError

    def custom_text_message(self, text):
        if self.__bot_token == "" and self.__chat_id == 0:
            return
        params = {"chat_id": str(self.__chat_id), "text": f"{text}"}
        r = requests.post(f"https://api.telegram.org/bot{self.__bot_token}/sendMessage", params=params)
        if r.status_code != 200:
            raise ConnectionError
