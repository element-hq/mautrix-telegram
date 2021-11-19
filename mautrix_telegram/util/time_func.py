from asyncio import Future, isfuture
from functools import wraps
from time import time
from types import FunctionType
from inspect import isawaitable
import logging
from typing import Optional

log = logging.getLogger("mau.time_func")

def time_func(log_level: str, name: Optional[str] = None):
    def decorator(func: FunctionType):
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            int_level = logging.getLevelName(log_level)
            func_name = name or func.__name__
            t1 = time()
            res = func(*args,  **kwargs)
            print(func_name, res)
            if isawaitable(res):
                # Ensure we only log once the function completes
                async def await_result():
                    t2 = time()
                    awaited_res = await res
                    invocation_time = time() - t1
                    await_time = time() - t2
                    log.log(int_level, f"async func {func_name} took {round(invocation_time+await_time, 3)}s (invoke {round(invocation_time, 3)}s, await {round(await_time, 3)})")
                    return awaited_res
                return await_result()
            else:
                log.log(int_level, f"func {func_name} took {round(time() - t1, 3)}s")
                return res
        return wrapper_function
    return decorator
