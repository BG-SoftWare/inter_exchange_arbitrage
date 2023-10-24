import logging
import os
import subprocess
import time
import traceback
from decimal import Decimal

from libs.bot_reporter.reporter import ReportBot
from libs.health_check import health_check
from libs.misc import custom_logging as log
from libs.misc import ping_proxies
from libs.config_parser import ConfigParser as Parser
from libs.tradelogic import TradeLogic

p = subprocess.Popen("mv *.txt logs/", stdout=subprocess.PIPE, shell=True)

(output, err) = p.communicate()
p_status = p.wait()

if os.path.isfile("./bot.lock"):
    print("Second instance of bot is not allowed")
    quit()

with open("./bot.lock", "w") as lockfile:
    lockfile.write("{0}".format(os.getpid()))

logging.basicConfig(filename=f'bot_{time.strftime("%d-%m-%Y_%H_%M_%S", time.localtime())}.txt')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())

log(logging.info, "[BOT] Scanning configs")

config = Parser(".env").config
exchange_1 = config["exchange_1"]
exchange_2 = config["exchange_2"]

log(logging.info, "[BOT] Scanning successful")
log(logging.info, "[BOT][Exchange 2] checking connection and api keys")

log(logging.info, "[BOT][Exchange 1] Trying to ping grpc proxy")
exchange_1_status = ping_proxies("Exchange 1", exchange_1)
log(logging.info, "[BOT][Exchange 2] Trying to ping grpc proxy")
exchange_2_status = ping_proxies("Exchange 2", exchange_2)

alerts = ReportBot(config["bot_api_key"], config["chat_id_for_alerts"], config)
log(logging.info, "[BOT] Checking TelegramBot")
alerts.custom_text_message("I started")

if exchange_1_status and exchange_2_status:
    log(logging.info, " [BOT] gRPC OK.")
elif not exchange_1_status:
    log(logging.info, " [BOT][Exchange 1] gRPC proxy is not responding.")
    alerts.custom_text_message("gRPC proxy Exchange 1 is not responding")
elif not exchange_2_status:
    log(logging.info, " [BOT][Exchange 2] gRPC proxy is not responding.")
    alerts.custom_text_message("gRPC proxy Exchange 1 is not responding")

try:
    exchange_2_balance = exchange_2.get_balances()
except:
    log(logging.error, "[BOT][Exchange 2] checking keys failed")
    alerts.custom_text_message("There's a problem with the account on Exchange 2")
    exit(-1)
log(logging.info, "[BOT][Exchange 2] checking keys successfully")

log(logging.info, "[BOT][Exchange 1] checking keys")

try:
    exchange_1_balance = exchange_1.get_balances()
except:
    log(logging.error, "[BOT][Exchange 1] checking keys failed")
    alerts.custom_text_message("There's a problem with the account on Exchange 1")
    exit(-1)

log(logging.info, "[BOT][Exchange 1] checking keys successfully")
token_sum = (Decimal(exchange_1_balance[config["token_ticker"]].free) +
             Decimal(exchange_2_balance[config["token_ticker"]].free))

if token_sum < config["amount_tokens_for_trade"] * 2 or token_sum // (config["amount_tokens_for_trade"] * 2) > 1:
    log(logging.critical, "Token balances is lower or higher than amount_tokens_for_trade * 2 ")
    exit()

log(logging.info, "[BOT] Check Exchange 1 depth bridge started")
while 1:
    if health_check(exchange_1):
        log(logging.info, "[BOT] Bridge status ok")
        break
    else:
        log(logging.warning, " [BOT] Cant retrieve depth. Retrying for 5 sec")
        time.sleep(5)

log(logging.info, "[BOT] Check Exchange 2 exchange depth bridge started")

while 1:
    if health_check(exchange_2):
        log(logging.info, " [BOT] Bridge status ok")
        break
    else:
        log(logging.warning, " [BOT] Cant retrieve depth. Retrying for 5 sec")
        time.sleep(5)

log(logging.info, " [BOT] Scanning depth for signals")

trades = TradeLogic(exchange_1, exchange_2, alerts, config)
try:
    trades.run_trade()
except KeyboardInterrupt:
    log(logging.info, " [BOT] Ctrl+C pressed. Im exit")
    alerts.custom_text_message("I'm stopping")
    exit(0)
except BaseException as e:
    log(logging.error, e)
    t = traceback.format_exc()
    alerts.crash_report(t)
    logging.info(t)
finally:
    os.remove("./bot.lock")
