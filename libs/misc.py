import logging
import time
from datetime import datetime
from functools import wraps


def get_time():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')


def custom_logging(level, text):
    level(f"{get_time()} {text}")


def ping_proxies(exchange_name, exchange):
    for i in range(4):
        try:
            custom_logging(logging.info, f"[BOT] {exchange_name} ping {exchange.ping()} ms")
        except:
            custom_logging(logging.info, f"[BOT] {exchange_name} ping request failed")
            return False
    return True


def timeit_debug(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        custom_logging(logging.debug, f'[TimeMeasure] Function {func.__name__} Took {total_time:.4f} seconds')
        return result

    return timeit_wrapper


def timeit_info(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        custom_logging(logging.info, f'[TimeMeasure] Function {func.__name__} Took {total_time:.4f} seconds')
        return result

    return timeit_wrapper
