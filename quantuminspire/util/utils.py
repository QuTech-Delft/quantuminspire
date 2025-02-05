import asyncio
import concurrent
import platform
from typing import Any, Coroutine


def run_async(async_function: Coroutine[Any, Any, Any]) -> Any:
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        _ = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(asyncio.run, async_function).result()
    except RuntimeError:

        return asyncio.run(async_function)
