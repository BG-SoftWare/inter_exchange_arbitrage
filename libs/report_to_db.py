import datetime
import logging
from decimal import Decimal

from libs.misc import custom_logging as log
from libs.misc import timeit_debug


def calc_delta_in_percent(num_1, num_2):
    if (num_1 + num_2) / 2 == 0:
        return 0
    return (Decimal(abs(num_1 - num_2)) / ((num_1 + num_2) / 2)) * 100


def control_fee(fee_from_exchange, order_total, fee_percent, deviation_percent=5):
    estimated_fee = (fee_percent / 100) * order_total
    if calc_delta_in_percent(fee_from_exchange, estimated_fee) > deviation_percent:
        return estimated_fee
    return fee_from_exchange


@timeit_debug
def report_generator(config, trade_exchange_1, trade_exchange_2, config_exchange_rate,
                     delta_bid_ask, balance_exchange_1, balance_exchange_2, profit, order_book_exchange_1,
                     order_book_exchange_2, price_from_depth_exchange_1, price_from_depth_exchange_2,
                     order_book_after_trade_exchange_1, order_book_after_trade_exchange_2, catch_avg_price_exchange_1,
                     catch_avg_price_exchange_2, coin_ticker, is_success=True, route=""):
    insert_to_db = {
        "profile_id": config["profile_id"],
        "route": None,
        "main_exchange_depth_dump": None,
        "main_exchange_depth_dump_after_trade": None,
        "main_exchange_order_id": None,
        "main_exchange_avg_order_price": None,
        "main_exchange_avg_order_price_from_depth": None,
        "main_exchange_order_from_depth": None,
        "main_exchange_order_from_fork": None,
        "main_exchange_token_amount": None,
        "main_exchange_usdt_amount": None,
        "main_exchange_order_fee_usdt": None,
        "main_exchange_order_fee_exchange_token": None,
        "main_exchange_trade_time": None,
        "secondary_exchange_depth_dump": None,
        "secondary_exchange_depth_dump_after_trade": None,
        "secondary_exchange_order_id": None,
        "secondary_exchange_avg_order_price": None,
        "secondary_exchange_avg_order_price_from_depth": None,
        "secondary_exchange_order_from_depth": None,
        "secondary_exchange_order_from_fork": None,
        "secondary_exchange_token_amount": None,
        "secondary_exchange_usdt_amount": None,
        "secondary_exchange_order_fee_usdt": None,
        "secondary_exchange_order_fee_exchange_token": None,
        "secondary_exchange_trade_time": None,
        "caught_course_delta": None,
        "real_course_delta": None,
        "main_exchange_balance_usdt": None,
        "secondary_exchange_balance_usdt": None,
        "all_token_amount": None,
        "main_exchange_fee_token_amount": None,
        "main_exchange_fee_token_amount_in_usdt": None,
        "all_token_amount_in_usdt": None,
        "all_usdt_amount": None,
        "profit": None,
        "all_profit": None,
        "is_success": is_success,
    }

    exchange_1_fee, is_fee_token = trade_exchange_1.calculate_fee(config_exchange_rate["BNB"],
                                                                  config_exchange_rate["SOL"], "BNB", coin_ticker)

    log(logging.info, "[ReportToDb] Get last bnb price")
    config_exchange_rate["BNB"] = Decimal(config["database"].get_last_main_fee_token_price(config["profile_group"]))
    log(logging.info, "[ReportToDb] Prepare data for insertion")
    if route != "":
        insert_to_db["route"] = route
    else:
        insert_to_db['route'] = "buy on Exchange 1 sell on Exchange 2" if trade_exchange_1.route == "BUY" \
            else "sell on Exchange 1 buy on Exchange 2"
    insert_to_db['main_exchange_depth_dump'] = order_book_exchange_1.to_json()
    insert_to_db['main_exchange_order_id'] = trade_exchange_1.id
    insert_to_db['main_exchange_avg_order_price'] = Decimal(trade_exchange_1.order_total) / Decimal(
        trade_exchange_1.token_amount)
    insert_to_db['main_exchange_token_amount'] = trade_exchange_1.token_amount
    insert_to_db['main_exchange_usdt_amount'] = trade_exchange_1.order_total
    insert_to_db['main_exchange_order_fee_usdt'] = \
        trade_exchange_1.calculate_fee(config_exchange_rate["BNB"], config_exchange_rate["SOL"], "BNB", coin_ticker)[0]
    insert_to_db['main_exchange_order_fee_exchange_token'] = \
        trade_exchange_1.calculate_fee(config_exchange_rate["BNB"], config_exchange_rate["SOL"], "BNB", coin_ticker)[0]
    insert_to_db["secondary_exchange_depth_dump"] = order_book_exchange_2.to_json()
    insert_to_db["secondary_exchange_order_id"] = trade_exchange_2.id
    insert_to_db["secondary_exchange_avg_order_price"] = Decimal(trade_exchange_2.order_total) / Decimal(
        trade_exchange_2.token_amount)
    insert_to_db["secondary_exchange_token_amount"] = trade_exchange_2.token_amount
    insert_to_db["secondary_exchange_usdt_amount"] = trade_exchange_2.order_total
    insert_to_db["secondary_exchange_order_fee_usdt"] = control_fee(
        trade_exchange_2.calculate_fee(config_exchange_rate["BNB"], config_exchange_rate["SOL"], "BNB", coin_ticker)[0],
        trade_exchange_2.order_total, Decimal("0.2"))
    insert_to_db["secondary_exchange_order_fee_exchange_token"] = control_fee(
        trade_exchange_2.calculate_fee(config_exchange_rate["BNB"], config_exchange_rate["SOL"], "BNB", coin_ticker)[0],
        trade_exchange_2.order_total, Decimal("0.2"))
    insert_to_db["caught_course_delta"] = delta_bid_ask
    insert_to_db["main_exchange_balance_usdt"] = balance_exchange_1["USDT"].free
    insert_to_db["secondary_exchange_balance_usdt"] = balance_exchange_2["USDT"].free
    insert_to_db["main_exchange_fee_token_amount"] = balance_exchange_1["BNB"].free
    insert_to_db["all_token_amount"] = balance_exchange_1[coin_ticker].free + balance_exchange_2[coin_ticker].free
    insert_to_db["main_exchange_fee_token_amount_in_usdt"] = balance_exchange_1["BNB"].free * config_exchange_rate[
        "BNB"]
    insert_to_db["all_token_amount_in_usdt"] = (balance_exchange_1[coin_ticker].free + balance_exchange_2[
        coin_ticker].free) * config_exchange_rate["SOL"]
    insert_to_db["all_usdt_amount"] = (insert_to_db["main_exchange_balance_usdt"] + insert_to_db[
        "secondary_exchange_balance_usdt"] + insert_to_db["main_exchange_fee_token_amount_in_usdt"] +
                                       insert_to_db["all_token_amount_in_usdt"])
    insert_to_db["main_exchange_order_from_depth"] = price_from_depth_exchange_1
    insert_to_db["main_exchange_order_from_fork"] = trade_exchange_1.order_price
    insert_to_db["secondary_exchange_order_from_depth"] = price_from_depth_exchange_2
    insert_to_db["secondary_exchange_order_from_fork"] = trade_exchange_2.order_price
    insert_to_db['main_exchange_depth_dump_after_trade'] = order_book_after_trade_exchange_1.to_json()
    insert_to_db['secondary_exchange_depth_dump_after_trade'] = order_book_after_trade_exchange_2.to_json()
    insert_to_db["main_exchange_avg_order_price_from_depth"] = catch_avg_price_exchange_1
    insert_to_db["secondary_exchange_avg_order_price_from_depth"] = catch_avg_price_exchange_2
    insert_to_db['main_exchange_trade_time'] = datetime.datetime.fromtimestamp(int(trade_exchange_1.time / 1000))
    insert_to_db['secondary_exchange_trade_time'] = datetime.datetime.fromtimestamp(int(trade_exchange_2.time / 1000))
    insert_to_db["main_exchange_fee_token_price"] = config_exchange_rate["BNB"]
    insert_to_db["main_exchange_token_balance"] = balance_exchange_1[coin_ticker].free
    insert_to_db["secondary_exchange_token_balance"] = balance_exchange_2[coin_ticker].free
    try:
        insert_to_db["exchange_1_order_fee_in_fee_token"] = sum(
            [Decimal(amount) for amount in trade_exchange_1.fee_amount])
    except:
        insert_to_db["exchange_1_order_fee_in_fee_token"] = trade_exchange_1.fee_amount
    insert_to_db["exchange_2_order_fee_in_fee_token"] = \
        trade_exchange_2.calculate_fee(config_exchange_rate["BNB"], config_exchange_rate["SOL"], "BNB", coin_ticker)[0]
    if trade_exchange_1.route == "BUY":
        insert_to_db['real_course_delta'] = ((insert_to_db["secondary_exchange_avg_order_price"] - insert_to_db[
            'main_exchange_avg_order_price']) / insert_to_db['main_exchange_avg_order_price']) * 100
    else:
        insert_to_db['real_course_delta'] = ((insert_to_db['main_exchange_avg_order_price'] - insert_to_db[
            "secondary_exchange_avg_order_price"]) / insert_to_db["secondary_exchange_avg_order_price"]) * 100

    if profit is None:
        if trade_exchange_1.route == "BUY":
            insert_to_db["profit"] = (insert_to_db["secondary_exchange_usdt_amount"] - insert_to_db[
                "main_exchange_usdt_amount"]) - insert_to_db["secondary_exchange_order_fee_usdt"] - insert_to_db[
                                         "main_exchange_order_fee_usdt"]
        else:
            if config["disable_count_fee_on_exchange_2_when_buy"] and is_success:
                insert_to_db["profit"] = (insert_to_db["main_exchange_usdt_amount"] - insert_to_db[
                    "secondary_exchange_usdt_amount"]) - insert_to_db["main_exchange_order_fee_usdt"]
            else:
                insert_to_db["profit"] = (insert_to_db["main_exchange_usdt_amount"] - insert_to_db[
                    "secondary_exchange_usdt_amount"]) - insert_to_db["secondary_exchange_order_fee_usdt"] - \
                                         insert_to_db["main_exchange_order_fee_usdt"]

    else:
        insert_to_db["profit"] = profit

    config["database"].insert_into_trades(insert_to_db)

    if not is_fee_token:
        log(logging.critical,
            "This transaction was not paid in a fee token: currencies {0} amounts {1}".format(
                str(trade_exchange_1.fee_currency), str(trade_exchange_1.fee_amount)))
        raise RuntimeError("This transaction was not paid in a fee token")
