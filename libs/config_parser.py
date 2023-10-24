import json
import os
from decimal import Decimal

from dotenv import load_dotenv

from libs.grpc_client import GRPCClient
from libs.database_adapter import DatabaseAdapter


class ConfigParser:
    def __init__(self, envfile=os.path.join(os.path.dirname(__file__), '.env')):
        load_dotenv(envfile)
        self.config = dict()
        self.config["disable_profit_check"] = os.getenv("DISABLE_PROFIT_CHECK") == "True"
        self.config["token_ticker"] = os.getenv("TOKEN_TICKER")
        self.config["grpc_address_exchange_1"] = os.getenv("GRPC_ADDRESS_EXCHANGE_1")
        self.config["grpc_address_exchange_2"] = os.getenv("GRPC_ADDRESS_EXCHANGE_2")
        self.config["bot_api_key"] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.config["profile_group"] = json.loads(os.getenv("PROFILE_GROUP"))
        self.config["buy_bnb_in_bot"] = os.getenv("BUY_BNB_IN_BOT") == "True"
        self.config["sell_tail"] = os.getenv("SELL_TAIL") == "True"
        self.config["disable_count_fee_on_exchange_2_when_buy"] = os.getenv(
            "DISABLE_COUNT_FEE_ON_EXCHANGE_2_WHEN_BUY") == "True"
        self.__prepare_databases()
        self.__prepare_exchanges()
        self.__to_decimal()
        self.__to_int()

    def __to_decimal(self):
        self.config["course_delta_value"] = Decimal(os.getenv("COURSE_DELTA"))
        self.config["amount_USDT_for_BNB_buy"] = Decimal(os.getenv("USDT_AMOUNT_FOR_BUY_BNB"))
        self.config["min_amount_for_trigger_buy_bnb"] = Decimal(os.getenv("MIN_AMOUNT_FOR_TRIGGER_BUY_BNB"))
        self.config["buy_more_tokens_on_second_exchange_percent"] = Decimal(
            os.getenv("BUY_MORE_TOKENS_ON_SECOND_EXCHANGE_PERCENT"))

    def __to_int(self):
        self.config["fork_step_exchange_2"] = int(os.getenv("FORK_STEP_EXCHANGE_2"))
        self.config["fork_step_exchange_1"] = int(os.getenv("FORK_STEP_EXCHANGE_1"))
        self.config["chat_id_for_alerts"] = int(os.getenv("TELEGRAM_CHAT_ID"))

    def __prepare_databases(self):
        print(os.getenv("DATABASE_CONNECTION_STRING"))
        self.config["database"] = DatabaseAdapter(os.getenv("DATABASE_CONNECTION_STRING"))
        self.config["profile_id"] = int(os.getenv("PROFILE_ID"))
        self.config["price_BNB_when_buy"], _, self.config["price_token_when_buy"] = self.config[
            "database"].get_fee_token_prices_and_token_price_for_profile_id(self.config["profile_id"])
        self.config["amount_tokens_for_trade"] = self.config["database"].get_trade_amount_for_profile(
            int(os.getenv("PROFILE_ID")))

    def __prepare_exchanges(self):
        self.config["exchange_1"] = GRPCClient(self.config["grpc_address_exchange_1"])
        self.config["exchange_2"] = GRPCClient(self.config["grpc_address_exchange_2"])
