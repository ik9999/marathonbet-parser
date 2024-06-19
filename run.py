from inc import BrowserManager, Parser, RedisManager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from loguru import logger
import sys
import config
from typing import Optional, List, Dict, Any, Awaitable

async def run_single_parser(parser: Parser, redis_man: RedisManager):
    while True:
        logger.trace("called try_parse")
        res = await parser.try_parse()
        logger.trace("try_parse res for {}: {}", parser.item_to_parse['code'], res)
        redis_man.save_odds(parser.item_to_parse['code'], res)
        if res is None:
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(5)

async def run():
    logger.info("Version 1.0 started. config: {}", config)
    browser_man = await BrowserManager.create()
    redis_man = RedisManager()
    parsers_list: list[Parser] = []
    for item_to_parse in config.data_to_parse:
        parser = Parser(browser_man, item_to_parse)
        parser.start_loop()
        parsers_list.append(parser)

    tasks: list[Awaitable] = []
    for parser in parsers_list:
        tasks.append(run_single_parser(parser, redis_man))
    await asyncio.gather(*tasks)
    time.sleep(100)

if __name__ == "__main__":
    logs_root = f"logs"
    logger.add(logs_root + "/file_{time}_prob.log", rotation="500 MB", compression="zip", level="TRACE", backtrace=True, diagnose=True, enqueue=True)
    logger.configure(handlers=[{"sink": sys.stdout, "level": "TRACE"}])
    asyncio.run(run())
    # loop = asyncio.get_event_loop()
    # executor = ThreadPoolExecutor()
    # loop.run_in_executor(executor, asyncio.run, run())
    # time.sleep(100)
