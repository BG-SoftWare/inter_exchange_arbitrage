import datetime
import logging
from decimal import Decimal

from sqlalchemy import BigInteger, DECIMAL, Boolean, null
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text, DateTime, desc
from sqlalchemy import create_engine, func, select, insert, and_, update, text


class DatabaseAdapter:
    meta = MetaData()

    exchanges = Table(
        "exchanges", meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
        Column('exchange_credetians', Text, default={"api_key": null, "api_sec": null}),
        Column('pair', String(255)),
        Column('proxy_url', String(255))
    )

    profiles = Table(
        "profiles", meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
        Column('exchange_main', Integer, ForeignKey(exchanges.c.id)),
        Column('exchange_sec', Integer, ForeignKey(exchanges.c.id)),
        Column('course_delta', DECIMAL(26, 16)),
        Column('price_token_when_buy', DECIMAL(26, 16)),
        Column('all_usdt', DECIMAL(26, 16)),
        Column('amount_for_usdt_buy', DECIMAL(26, 16)),
        Column('price_fee_token_main', DECIMAL(26, 16), default=1),
        Column('price_fee_token_sec', DECIMAL(26, 16), default=1),
        Column('datetime_when_fee_token_buy_main', DateTime, default=1),
        Column('datetime_when_fee_token_buy_sec', DateTime, default=1),
        Column("trade_amount", DECIMAL(26, 16)),
        Column("trade_amount_when_start", DECIMAL(26, 16)),
        Column("group_id", Integer),
        Column("main_exchange_start_token_amount", DECIMAL(26, 16)),
        Column("sec_exchange_start_token_amount", DECIMAL(26, 16))
    )

    trade_info = Table(
        "trade_info", meta,
        Column("id", Integer, primary_key=True),
        Column('exchanges_id', Integer, ForeignKey(exchanges.c.id)),
        Column('order_id', BigInteger),
        Column('depth_dump', Text),
        Column('depth_dump_after_trade', Text),
        Column('order_price_from_depth', DECIMAL(16, 16)),
        Column('order_price_from_fork', DECIMAL(26, 16)),
        Column('avg_order_price', DECIMAL(26, 16)),
        Column('avg_order_price_from_depth', DECIMAL(26, 16)),
        Column('token_amount', DECIMAL(26, 16)),
        Column('usdt_amount', DECIMAL(26, 16)),
        Column('order_fee', DECIMAL(26, 16)),
        Column('order_fee_in_fee_token', DECIMAL(26, 16)),
        Column('fee_currency_exchange_rate', DECIMAL(26, 16), default=1),
        Column('trade_time', DateTime, default=datetime.datetime.now),
    )

    balances = Table(
        'balances', meta,
        Column('id', Integer, primary_key=True),
        Column('exchange', Integer, ForeignKey(exchanges.c.id)),
        Column('token_amount', DECIMAL(26, 16)),
        Column('usdt_amount', DECIMAL(26, 16)),
        Column('fee_token_amount', DECIMAL(26, 16), default=-1),
        Column('token_price', DECIMAL(26, 16)),
        Column('fee_token_price', DECIMAL(26, 16), default=0),
    )

    trades = Table(
        "trades", meta,
        Column("id", Integer, primary_key=True),
        Column("profile_id", Integer, ForeignKey(profiles.c.id)),
        Column('is_success', Boolean, default=False),
        Column("route", String(255), default=null),
        Column('deal_1', Integer, ForeignKey(trade_info.c.id)),
        Column('deal_2', Integer, ForeignKey(trade_info.c.id)),
        Column("caught_course_delta", DECIMAL(26, 16)),
        Column("real_course_delta", DECIMAL(26, 16)),
        Column('balances_main_exchange', Integer, ForeignKey(balances.c.id)),
        Column('balances_sec_exchange', Integer, ForeignKey(balances.c.id)),
        Column('profit', DECIMAL(26, 16))
    )

    trade_reports = Table(
        "trade_reports", meta,
        Column("id", Integer, primary_key=True),
        Column("report_datetime", DateTime),
        Column("profile_id", Integer, ForeignKey("profiles.id")),
        Column("bank_percent", DECIMAL(26, 16)),
        Column("start_balance", DECIMAL(26, 16)),
        Column("current_balance", DECIMAL(26, 16)),
        Column("profit_per_iteration", DECIMAL(26, 16)),
        Column("all_profit", DECIMAL(26, 16)),
        Column("trades_count", Integer),
        Column("trade_minus_count", Integer),
        Column("trade_minus_percent", DECIMAL(26, 16)),

    )

    profit_percent = Table(
        "profit_percent", meta,
        Column("id", Integer, primary_key=True),
        Column("date_calc", DateTime),
        Column("all_profit", DECIMAL(26, 16)),
        Column("all_usdt", DECIMAL(26, 16))
    )

    token_moving = Table(
        "token_moving", meta,
        Column("id", Integer, primary_key=True),
        Column("profile_id", Integer, ForeignKey(profiles.c.id)),
        Column("date_buy", DateTime),
        Column("route", String(255)),
        Column("token_amount_main_exchange", DECIMAL(26, 16)),
        Column("usdt_amount_main_exchange", DECIMAL(26, 16)),
        Column("price_main_exchange", DECIMAL(26, 16)),
        Column("token_amount_sec_exchange", DECIMAL(26, 16)),
        Column("usdt_amount_sec_exchange", DECIMAL(26, 16)),
        Column("price_sec_exchange", DECIMAL(26, 16)),
    )

    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
        self.meta.bind = self.engine
        self.meta.create_all()

    def insert_into_trades(self, args):
        conn = self.engine.connect()
        exchanges_id_main, exchanges_id_sec = conn.execute(select([self.profiles.c.exchange_main,
                                                                   self.profiles.c.exchange_sec]).where(
            self.profiles.c.id == args["profile_id"])).fetchone()
        fee_currency_exchange_rate = args["main_exchange_fee_token_price"], Decimal(1)
        token_price = conn.execute(select([self.profiles.c.price_token_when_buy]).where(
            args["profile_id"] == self.profiles.c.id
        )).fetchone()[0]

        transaction = conn.begin()
        logging.info("Start inserting data into the database")
        try:
            logging.info("Start inserting data into the trade_info table")
            trade_info_ins_main = conn.execute(insert(self.trade_info), [
                {
                    "exchanges_id": exchanges_id_main,
                    "order_id": args["main_exchange_order_id"],
                    "depth_dump": args["main_exchange_depth_dump"],
                    "depth_dump_after_trade": args["main_exchange_depth_dump_after_trade"],
                    "order_price_from_depth": args["main_exchange_order_from_depth"],
                    "order_price_from_fork": args["main_exchange_order_from_fork"],
                    "avg_order_price": args["main_exchange_avg_order_price"],
                    "avg_order_price_from_depth": args["main_exchange_avg_order_price_from_depth"],
                    "token_amount": args["main_exchange_token_amount"],
                    "usdt_amount": args["main_exchange_usdt_amount"],
                    "order_fee": args["main_exchange_order_fee_exchange_token"],
                    "fee_currency_exchange_rate": fee_currency_exchange_rate[0],
                    'order_fee_in_fee_token': args["main_exchange_order_fee_in_fee_token"]
                }
            ])
            trade_info_ins_sec = conn.execute(insert(self.trade_info), [
                {
                    "exchanges_id": exchanges_id_sec,
                    "order_id": args["secondary_exchange_order_id"],
                    "depth_dump": args["secondary_exchange_depth_dump"],
                    "depth_dump_after_trade": args["secondary_exchange_depth_dump_after_trade"],
                    "order_price_from_depth": args["secondary_exchange_order_from_depth"],
                    "order_price_from_fork": args["secondary_exchange_order_from_fork"],
                    "avg_order_price": args["secondary_exchange_avg_order_price"],
                    "avg_order_price_from_depth": args["secondary_exchange_avg_order_price_from_depth"],
                    "token_amount": args["secondary_exchange_token_amount"],
                    "usdt_amount": args["secondary_exchange_usdt_amount"],
                    "order_fee": args["secondary_exchange_order_fee_exchange_token"],
                    "fee_currency_exchange_rate": fee_currency_exchange_rate[1],
                    'order_fee_in_fee_token': args["secondary_exchange_order_fee_in_fee_token"]
                }
            ])

            logging.info("Start inserting data into the balances table")
            balances_ins_main = conn.execute(insert(self.balances), [
                {
                    "exchange": exchanges_id_main,
                    "token_amount": args["main_exchange_token_balance"],
                    "usdt_amount": args["main_exchange_balance_usdt"],
                    "fee_token_amount": args["main_exchange_fee_token_amount"] if
                    "main_exchange_fee_token_amount" in args.keys() else -1,
                    "token_price": token_price,
                    "fee_token_price": args["main_exchange_fee_token_price"] if
                    "main_exchange_fee_token_price" in args.keys() else 0
                }
            ])
            balances_ins_sec = conn.execute(insert(self.balances), [
                {
                    "exchange": exchanges_id_sec,
                    "token_amount": args["secondary_exchange_token_balance"],
                    "usdt_amount": args["secondary_exchange_balance_usdt"],
                    "fee_token_amount": args["secondary_exchange_fee_token_amount"] if
                    "secondary_exchange_fee_token_amount" in args.keys() else -1,
                    "token_price": token_price,
                    "fee_token_price": args["secondary_exchange_fee_token_price"] if
                    "secondary_exchange_fee_token_price" in args.keys() else 0,
                }
            ])

            logging.info("Start inserting data into the trades table")
            conn.execute(insert(self.trades), [
                {
                    "profile_id": args["profile_id"],
                    "is_success": args["is_success"],
                    "route": args["route"],
                    "deal_1": trade_info_ins_main.lastrowid,
                    "deal_2": trade_info_ins_sec.lastrowid,
                    "caught_course_delta": args["caught_course_delta"],
                    "real_course_delta": args["real_course_delta"],
                    "balances_main_exchange": balances_ins_main.lastrowid,
                    "balances_sec_exchange": balances_ins_sec.lastrowid,
                    "profit": args["profit"]
                }
            ])
            transaction.commit()
            logging.info("[DatabaseAdapter] Insert to database was SUCCESSFUL")
        except Exception as e:
            transaction.rollback()
            logging.critical("[DatabaseAdapter] Insert to database was FAILED")
            logging.critical(e)
            logging.critical("stacktrace ", exc_info=e)
            raise RuntimeError
        conn.close()
        self.engine.dispose()

    def count_trades_by_profile_id(self, profile_id):
        conn = self.engine.connect()
        sel = select([func.count(self.trades.c.id)]).where(self.trades.c.profile_id == profile_id)
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_all_usdt_from_profile(self, profile_id):
        conn = self.engine.connect()
        sel = select([self.profiles.c.all_usdt]).where(self.profiles.c.id == profile_id)
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_last_profit_and_all_profit(self, profile_id):
        conn = self.engine.connect()
        last_profit = conn.execute(select([self.trades.c.profit]).where(
            self.trades.c.profile_id == profile_id).order_by(self.trades.c.id.desc()
                                                             )).first()
        all_profit = conn.execute(select([func.sum(self.trades.c.profit)]).where(
            self.trades.c.profile_id == profile_id
        )).fetchall()
        conn.close()
        self.engine.dispose()
        if last_profit and all_profit is not None:
            return last_profit[0], all_profit[0][0]

    def get_profiles(self):
        conn = self.engine.connect()
        sel = select([self.profiles.c.id,
                      self.profiles.c.name,
                      self.profiles.c.exchange_main,
                      self.profiles.c.exchange_sec,
                      self.profiles.c.course_delta,
                      self.profiles.c.price_token_when_buy,
                      self.profiles.c.all_usdt,
                      self.profiles.c.price_fee_token_main,
                      self.profiles.c.price_fee_token_sec])
        result = conn.execute(sel).fetchall()[0]
        profiles_params = ["id", "name", "exchange_main", "exchange_sec", "course_delta", "price_token_when_buy",
                           "all_usdt", "price_fee_token_main", "price_fee_token_sec"]
        conn.close()
        self.engine.dispose()
        if result is not None:
            return dict(zip(profiles_params, result))

    def get_all_profit_per_day(self, profile_id, to_date=datetime.datetime.utcnow().date()):
        conn = self.engine.connect()
        begin_time = to_date - datetime.timedelta(days=1)
        sel = select([func.sum(self.trades.c.profit)]).select_from(
            self.trades.waiting(self.trade_info, self.trades.c.deal_1 == self.trade_info.c.id)).where(
            and_(
                self.trades.c.profile_id == profile_id,
                self.trade_info.c.trade_time >= begin_time,
                self.trade_info.c.trade_time < to_date
            )
        )
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]
        else:
            logging.error("The data is absent")

    def get_trades_count_by_profile_id_per_day(self, profile_id, to_date=datetime.datetime.utcnow().date()):
        conn = self.engine.connect()
        begin_time = to_date - datetime.timedelta(days=1)
        sel = select([func.count()]).select_from(
            self.trades.waiting(self.trade_info, self.trades.c.deal_1 == self.trade_info.c.id)).where(
            and_(
                self.trades.c.profile_id == profile_id,
                self.trade_info.c.trade_time >= begin_time,
                self.trade_info.c.trade_time < to_date
            )
        )
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_last_all_usdt_from_trades_by_profile(self, profile_id):
        conn = self.engine.connect()
        select_main = (conn.execute(
            select(
                [
                    self.balances.c.token_amount,
                    self.balances.c.token_price,
                    self.balances.c.usdt_amount,
                    self.balances.c.fee_token_amount,
                    self.balances.c.fee_token_price
                ]
            )
            .select_from(self.balances.waiting(
                self.trades, self.balances.c.id == self.trades.c.balances_main_exchange)
            )
            .where(self.trades.c.profile_id == profile_id)
            .order_by(desc(self.balances.c.id))).first())

        select_sec = conn.execute(
            select(
                [
                    self.balances.c.token_amount,
                    self.balances.c.token_price,
                    self.balances.c.usdt_amount,
                    self.balances.c.fee_token_amount,
                    self.balances.c.fee_token_price
                ]
            )
            .select_from(self.balances.waiting(
                self.trades, self.balances.c.id == self.trades.c.balances_sec_exchange)
            )
            .where(self.trades.c.profile_id == profile_id)
            .order_by(desc(self.balances.c.id))).first()

        params = ["token_amount", "token_price", "usdt_amount", "fee_token_amount", "fee_token_price"]
        main_data = dict(zip(params, select_main))
        sec_data = dict(zip(params, select_sec))
        result = main_data["token_amount"] * main_data["token_price"] + main_data["usdt_amount"] + main_data[
            "fee_token_amount"] * main_data["fee_token_price"] + sec_data["token_amount"] * sec_data["token_price"] + \
                 sec_data["usdt_amount"] + sec_data["fee_token_amount"] * sec_data["fee_token_price"]
        conn.close()
        self.engine.dispose()
        return result

    def change_bnb_price_in_profile(self, profile_id, price):
        conn = self.engine.connect()
        transaction = conn.begin()
        conn.execute(update(self.profiles).values(price_fee_token_main=price,
                                                  datetime_when_fee_token_buy_main=datetime.datetime.now()).where(
            self.profiles.c.id == profile_id))
        transaction.commit()
        conn.close()
        self.engine.dispose()

    def get_last_usdt_all_and_all_profit(self, profile_id):
        conn = self.engine.connect()
        all_profit = conn.execute(select([func.sum(self.trades.c.profit)]).where(
            self.trades.c.profile_id == profile_id
        )).fetchall()
        conn.close()
        self.engine.dispose()
        if all_profit is not None:
            return self.get_last_all_usdt_from_trades_by_profile(profile_id), all_profit[0][0]

    def get_count_minus_trades_by_profile_id_per_day(self, profile_id, to_date=datetime.datetime.utcnow().date()):
        conn = self.engine.connect()
        begin_time = to_date - datetime.timedelta(days=1)
        sel = select([func.count()]).select_from(
            self.trades.waiting(self.trade_info, self.trades.c.deal_1 == self.trade_info.c.id)).where(
            and_(
                self.trades.c.profile_id == profile_id,
                self.trade_info.c.trade_time >= begin_time,
                self.trade_info.c.trade_time < to_date,
                self.trades.c.profit <= 0
            )
        )
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_failed_percent_minus_trades_by_profile_id_per_day(self, profile_id,
                                                              to_date=datetime.datetime.utcnow().date()):
        return self.get_count_minus_trades_by_profile_id_per_day(profile_id,
                                                                 to_date) / self.get_trades_count_by_profile_id_per_day(
            profile_id, to_date)

    def get_fee_token_prices_and_token_price_for_profile_id(self, profile_id):
        conn = self.engine.connect()
        sel = select([self.profiles.c.price_fee_token_main, self.profiles.c.price_fee_token_sec,
                      self.profiles.c.price_token_when_buy]).where(self.profiles.c.id == profile_id)
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0], result[0][1], result[0][2]

    def get_last_main_fee_token_price(self, profile_group):
        conn = self.engine.connect()
        sel = text(
            'SELECT price_fee_token_main '
            'FROM `profiles` '
            'WHERE id IN :id_list '
            'ORDER BY `datetime_when_fee_token_buy_main` ASC LIMIT 1'
        )
        result = conn.execute(sel, id_list=tuple(profile_group))
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_sum_token_amount_first_trade_for_profile(self, profile_id):
        conn = self.engine.connect()
        sel = text(
            'SELECT b1.token_amount + b2.token_amount FROM trades'
            ' JOIN balances b1 on b1.id=trades.balances_main_exchange'
            ' JOIN balances b2 on b2.id=trades.balances_sec_exchange '
            'WHERE trades.profile_id=:profile_id LIMIT 1;'
        )
        result = conn.execute(sel, profile_id=profile_id)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def get_token_amount_first_trade_for_profile(self, profile_id):
        conn = self.engine.connect()
        sel = text(
            'SELECT b1.token_amount, b2.token_amount FROM trades'
            'JOIN balances b1 on b1.id=trades.balances_main_exchange'
            'JOIN balances b2 on b2.id=trades.balances_sec_exchange '
            'WHERE trades.profile_id=:profile_id LIMIT 1;'
        )
        result = conn.execute(sel, profile_id=profile_id)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0], result[0][1]

    def get_trade_amount_for_profile(self, profile_id):
        conn = self.engine.connect()
        sel = select([self.profiles.c.trade_amount]).where(self.profiles.c.id == profile_id)
        result = conn.execute(sel)
        result = result.fetchall()
        conn.close()
        self.engine.dispose()
        if result is not None:
            return result[0][0]

    def clone_first_trade_and_modify_orig_trade(self, token_amount_first_exchange, token_amount_second_exchange,
                                                profile_id):
        conn = self.engine.connect()
        first_trade_query = select(self.trades).where(self.trades.c.profile_id == profile_id).limit(1)
        profile = select(self.profiles).where(self.profiles.c.id == profile_id).limit(1)
        result_profile = conn.execute(profile)
        fetched_result_profile = result_profile.fetchall()
        result_first_trade = conn.execute(first_trade_query)
        fetched_result_first_trade = result_first_trade.fetchall()
        transaction = conn.begin()
        conn.execute(insert(self.trades), [
            {
                "profile_id": fetched_result_first_trade[0][1],
                "is_success": fetched_result_first_trade[0][2],
                "route": fetched_result_first_trade[0][3],
                "deal_1": fetched_result_first_trade[0][4],
                "deal_2": fetched_result_first_trade[0][5],
                "caught_course_delta": fetched_result_first_trade[0][6],
                "real_course_delta": fetched_result_first_trade[0][7],
                "balances_main_exchange": fetched_result_first_trade[0][8],
                "balances_sec_exchange": fetched_result_first_trade[0][9],
                "profit": fetched_result_first_trade[0][10]
            }
        ])
        logging.info("Start inserting data into the balances table")
        balances_ins_main = conn.execute(insert(self.balances), [
            {
                "exchange": fetched_result_profile[0][2],
                "token_amount": token_amount_first_exchange,
                "usdt_amount": 0,
                "fee_token_amount": 0,
                "token_price": 0,
                "fee_token_price": 0,
            }
        ])
        balances_ins_sec = conn.execute(insert(self.balances), [
            {
                "exchange": fetched_result_profile[0][3],
                "token_amount": token_amount_second_exchange,
                "usdt_amount": 0,
                "fee_token_amount": 0,
                "token_price": 0,
                "fee_token_price": 0,
            }
        ])
        conn.execute(update(self.trades).where(self.trades.c.id == fetched_result_first_trade[0][0]).values(
            balances_main_exchange=balances_ins_main.lastrowid, balances_sec_exchange=balances_ins_sec.lastrowid,
            profit=Decimal(0), route="Start balances only. Not real trade."))
        transaction.commit()

    def edit_first_trade_token_amount(self, token_amount_first_exchange, token_amount_second_exchange,
                                      profile_id):
        conn = self.engine.connect()
        first_trade_query = select(self.trades).where(self.trades.c.profile_id == profile_id).limit(1)
        result_first_trade = conn.execute(first_trade_query)
        fetched_result_first_trade = result_first_trade.fetchall()
        transaction = conn.begin()
        logging.info("Start inserting data into the balances table")
        conn.execute(update(self.balances).where(self.balances.c.id == fetched_result_first_trade[0][8]).values(
            token_amount=Decimal(token_amount_first_exchange)))
        conn.execute(update(self.balances).where(self.balances.c.id == fetched_result_first_trade[0][9]).values(
            token_amount=Decimal(token_amount_second_exchange)))
        transaction.commit()

    def add_daily_calculation_to_profit_percent(self, all_profit, all_usdt, date=datetime.datetime.utcnow()):
        conn = self.engine.connect()
        transaction = conn.begin()
        conn.execute(
            insert(self.profit_percent), [
                {
                    "date_calc": date,
                    "all_profit": all_profit,
                    "all_usdt": all_usdt
                }
            ]
        )
        transaction.commit()
        conn.close()
        self.engine.dispose()

    def add_to_buy_token(self, profile_id, route, token_amount_main_exchange, usdt_amount_main_exchange,
                         price_main_exchange,
                         token_amount_sec_exchange, usdt_amount_sec_exchange, price_sec_exchange):
        conn = self.engine.connect()
        transaction = conn.begin()
        conn.execute(
            insert(self.token_moving), [
                {
                    "profile_id": profile_id,
                    "date_buy": datetime.datetime.now(),
                    "route": route,
                    "token_amount_main_exchange": token_amount_main_exchange,
                    "usdt_amount_main_exchange": usdt_amount_main_exchange,
                    "price_main_exchange": price_main_exchange,
                    "token_amount_sec_exchange": token_amount_sec_exchange,
                    "usdt_amount_sec_exchange": usdt_amount_sec_exchange,
                    "price_sec_exchange": price_sec_exchange,
                }
            ]
        )
        transaction.commit()
        conn.close()
        self.engine.dispose()

    def get_price_token_when_buy_by_profile_id(self, profile_id):
        conn = self.engine.connect()
        r = conn.execute(
            select(
                [
                    self.token_moving.c.usdt_amount_main_exchange,
                    self.token_moving.c.token_amount_main_exchange,
                    self.token_moving.c.usdt_amount_sec_exchange,
                    self.token_moving.c.token_amount_sec_exchange])
            .where(and_(self.token_moving.c.profile_id == profile_id, self.token_moving.c.route == "BUY")))
        result = r.fetchall()
        conn.close()
        self.engine.dispose()
        all_token_amount, all_usdt_amount = 0, 0
        if result is not None:
            for move in result:
                all_usdt_amount += move[0] + move[2]
                all_token_amount += move[1] + move[3]
        if all_token_amount == 0:
            return 0
        return all_usdt_amount / all_token_amount

    def set_price_token_when_buy_and_token_amounts_by_profile_id(self, profile_id, price_when_buy, token_main,
                                                                 token_sec):
        conn = self.engine.connect()
        transaction = conn.begin()
        conn.execute(
            update(self.profiles).values(price_token_when_buy=price_when_buy,
                                         main_exchange_start_token_amount=token_main,
                                         sec_exchange_start_token_amount=token_sec).where(
                self.profiles.c.id == profile_id))
        transaction.commit()
        self.engine.dispose()
        self.edit_first_trade_token_amount(token_main, token_sec, profile_id)

    def get_usdt_amount_for_buying_usdt_by_profile_id(self, profile_id):
        conn = self.engine.connect()
        transaction = conn.begin()
        r = conn.execute(
            select(self.profiles.c.amount_for_usdt_buy).where(self.profiles.c.id == profile_id))
        result = r.fetchall()
        transaction.commit()
        self.engine.dispose()
        if result is not None:
            return result[0][0]
