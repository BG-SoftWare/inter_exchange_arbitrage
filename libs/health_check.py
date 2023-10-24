import traceback

from libs.misc import timeit_debug


@timeit_debug
def health_check(exchange):
    try:
        data = exchange.get_depth()
        if data.timestamp == -1:
            raise RuntimeError
    except:
        traceback.print_exc()
        return False
    return True
