import traceback
import asyncio
from asyncio import Task, Lock
from typing import Optional, List, Dict, Any
from inc.browser import BrowserManager
from playwright.async_api import Page, Locator
from loguru import logger
import sys, time
# from threading import Lock
import schedule
import aioschedule as schedule

class Parser:
    browser_man: BrowserManager
    item_to_parse: Dict[str, Any]
    is_loading: bool
    page: Optional[Page]
    cur_page_parsing: Lock
    __loop_task: Optional[Task]
    __update_window_lock: Lock
    __update_window_in_progress: bool
    __is_live: bool

    def __init__(self, browser: BrowserManager, item_to_parse: Dict[str, Any]):
        self.browser_man = browser
        self.item_to_parse = item_to_parse
        self.cur_page_parsing = Lock()
        self.page = None
        self.__loop_task = None
        self.__update_window_lock = Lock()
        self.__update_window_in_progress = False
        self.__is_live = False
        schedule.every(60).to(120).seconds.do(self.update_window)


    async def __start_loop(self): 
        logger.trace("__start_loop called for {}", self.item_to_parse['code'])
        await self.update_window()
        await asyncio.sleep(0)
        while True:
            await schedule.run_pending()
            await asyncio.sleep(0.1)

    def start_loop(self):
        logger.trace("start_loop called for {}", self.item_to_parse['code'])
        self.__loop_task = asyncio.create_task(self.__start_loop())

    async def update_window(self):
        if self.__update_window_in_progress:
            logger.warning("update_window for {} is already in progress", self.item_to_parse['code'])
            return
        tries = 0
        while True:
            new_page: Optional[Page] = None
            async with self.__update_window_lock:
                try:
                    logger.trace("Parser for {}. Called update_window (try {})", self.item_to_parse['code'], tries)
                    print(self.item_to_parse["url"])
                    new_page = await self.browser_man.open_page(self.item_to_parse["url"])
                    # html = await new_page.content()
                    # print(html)
                    all_markets_btn_selector: str = 'table.table-shortcuts-menu td div'
                    logger.trace("Parser for {}. Page opened. Waiting for {}", self.item_to_parse['code'], all_markets_btn_selector)
                    # time.sleep(5)
                    await self.browser_man.wait_for(new_page, all_markets_btn_selector)
                    logger.trace("Parser for {}. Page opened. Element {} exist", self.item_to_parse['code'], all_markets_btn_selector)
                    all_markets_btn_els = new_page.locator(all_markets_btn_selector, has_text='All Markets')
                    all_markets_btn_els_num = await all_markets_btn_els.count()
                    if all_markets_btn_els_num == 0:
                        raise Exception("all_markets_btn_els_num == 0")
                    # all_markets_btn_el = all_markets_btn_els.first
                    logger.trace("Parser for {}. Page opened. Clicking on all markets btn", self.item_to_parse['code'])
                    await new_page.evaluate(f'''
                        () => Array.from(document.querySelectorAll("{all_markets_btn_selector}")).find(el => el.textContent.includes("All Markets")).click()
                    ''')
                    # await all_markets_btn_el.click(force=True)
                    logger.trace("Parser for {}. Clicked all markets btn. Sleep 1s", self.item_to_parse['code'])
                    await asyncio.sleep(1)
                    logger.trace("Parser for {}. Call try_parse", self.item_to_parse['code'])
                    await self.try_parse(new_page)
                    async with self.cur_page_parsing:
                        if self.page is not None:
                            await self.page.close()
                        self.page = new_page
                    logger.trace("done update_window for {}", self.item_to_parse['code'])
                    break
                except Exception as e:
                    logger.error("Unable to create new window: {}", e)
                    logger.error(e.__traceback__)
                    print(e)
                    exc_info = sys.exc_info()
                    traceback.print_exception(*exc_info)
                    traceback.print_tb(e.__traceback__)
                    if new_page is not None:
                        if not new_page.is_closed():
                            logger.trace("update_window for {} error: set self.page to None", self.item_to_parse['code'])
                            try:
                                await new_page.close()
                            except Exception as e:
                                logger.warning("update_window for {} error: Error closing new_page: {}", self.item_to_parse['code'], e)
                        new_page = None
                    async with self.cur_page_parsing:
                        logger.trace("update_window for {} error: set self.page to None", self.item_to_parse['code'])
                        if self.page is not None:
                            if not self.page.is_closed():
                                logger.trace("update_window for {} error: set self.page to None", self.item_to_parse['code'])
                                try:
                                    await self.page.close()
                                except Exception as e:
                                    logger.warning("update_window for {} error: Error closing self.page: {e}", self.item_to_parse['code'], e)
                            self.page = None
                    tries += 1
            await asyncio.sleep(5)

    async def try_parse(self, page: Optional[Page]=None) -> Optional[List[Dict[str, str]]]:
        lock_aquired = False
        if page == self.page or page is None:
            lock_aquired = True
            await self.cur_page_parsing.acquire()
        if page is None:
            page = self.page
        if page is None:
            logger.warning("page is None")
            if lock_aquired:
                self.cur_page_parsing.release()
            return None
        odds_res: List[Dict[str, str]] = []
        try:
            if page.is_closed():
                raise Exception("page is closed")
            logger.trace("try_parse called for {}", self.item_to_parse['code'])
            header_table_sel = 'table.market-table-name'
            header_table_els = page.locator(header_table_sel)
            logger.trace("try_parse for {}. header_table_els.count() {}", self.item_to_parse['code'], await header_table_els.count())
            col_to_parse = self.item_to_parse["col_to_parse"]
            odds_res = await page.evaluate(f'''
                () => {{
                    var els = document.querySelectorAll("{header_table_sel}");
                    var header_tbl_el = Array.from(els).find(el => el.querySelector('tr td div.name-field').textContent.includes("{col_to_parse}"));
                    var parent_el = header_tbl_el.parentElement;
                    var content_table_rows_els = parent_el.querySelectorAll("td:has(div.result-left):has(div.result-right)");
                    var res = [];
                    for (content_table_row_el_idx in Array.from(content_table_rows_els)) {{
                        var el = content_table_rows_els[content_table_row_el_idx];
                        var res_left = el.querySelector('div.result-left').textContent.trim();
                        var res_right = el.querySelector('div.result-right').textContent.trim();
                        var is_active = true;
                        if (el.querySelector('.suspended-selection')) {{
                            is_active = false;
                        }}
                        res.push({{
                            "name": res_left,
                            "value": res_right,
                            "is_active": is_active,
                        }});
                    }}
                    return res
                }}
            ''')
            logger.trace("try_parse for {}. got odds_res: {}", self.item_to_parse["code"], odds_res)
            if type(odds_res) != list:
                raise Exception("odds_res is not list")
            if len(odds_res) <= 0:
                raise Exception("odds_res is empty")
            if type(odds_res[0]) != dict:
                raise Exception("type(odds_res[0]) != dict")
            if "/live/" in page.url:
                if not self.__is_live:
                    logger.info("try_parse for {}. Event is live. Change schedule to every 5 minutes", self.item_to_parse['code'])
                    schedule.clear()
                    schedule.every(4).to(7).minutes.do(self.update_window)
                self.__is_live = True
        except Exception as e:
            if lock_aquired:
                self.cur_page_parsing.release()
            logger.warning("try_parse error: {}", e)
            return None
        if lock_aquired:
            self.cur_page_parsing.release()
        logger.trace("done try_parse for {}. odds_res: {}", self.item_to_parse["code"], odds_res)
        return odds_res
