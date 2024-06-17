from inc import BrowserManager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from loguru import logger
import sys

async def run():
    browser_man = await BrowserManager.create()
    time.sleep(100)

if __name__ == "__main__":
    logger.configure(handlers=[{"sink": sys.stdout, "level": "TRACE"}])
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    loop.run_in_executor(executor, asyncio.run, run())
    time.sleep(100)
