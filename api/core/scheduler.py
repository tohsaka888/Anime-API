import asyncio
from time import perf_counter
from typing import Callable, Coroutine, Type

from api.core.anime import *
from api.core.danmaku import *
from api.core.loader import ModuleLoader
from api.core.proxy import AnimeProxy
from api.utils.logger import logger


class Scheduler:
    """
    调度器, 负责调度引擎搜索、解析资源
    """

    def __init__(self):
        self._loader = ModuleLoader()

    async def search_anime(self, keyword: str) -> AsyncIterator[AnimeMeta]:
        """
        异步搜索动漫

        :param keyword: 关键词
        """
        if not keyword:
            yield

        searchers = self._loader.get_anime_searchers()
        if not searchers:
            logger.warning(f"No anime searcher enabled")
            return

        start_time = perf_counter()

        for searcher in searchers:
            logger.info(f"{searcher.__class__.__name__} is searching for [{keyword}]")
            async for meta in searcher._search(keyword):
                yield meta

        end_time = perf_counter()
        logger.info(f"Searching anime finished in {end_time - start_time:.2f}s")

    async def search_danmaku(self, keyword: str) -> AsyncIterator[DanmakuMeta]:
        """
        搜索弹幕库
        """
        searchers = self._loader.get_danmaku_searcher()
        if not searchers:
            logger.warning(f"No danmaku searcher enabled")
            yield

        start_time = perf_counter()

        for searcher in searchers:
            logger.info(f"{searcher.__class__.__name__} is searching for [{keyword}]")
            async for meta in searcher._search(keyword):
                yield meta

        end_time = perf_counter()
        logger.info(f"Searching danmaku finished in {end_time - start_time:.2f}s")

    async def parse_anime_detail(self, meta: AnimeMeta) -> AnimeDetail:
        """解析番剧详情页信息"""
        detail_parser = self._loader.get_anime_detail_parser(meta.module)
        if not detail_parser:  # 直接访问直链, 且配置文件已关闭模块, 把工具类加载起来完成解析
            self._loader.load_utils_module(meta.module)
            detail_parser = self._loader.get_anime_detail_parser(meta.module)
        logger.info(f"{detail_parser.__class__.__name__} parsing {meta.detail_url}")
        if detail_parser is not None:
            return await detail_parser._parse(meta.detail_url)
        return AnimeDetail()

    async def parse_anime_real_url(self, anime: Anime) -> AnimeInfo:
        """解析一集视频的直链"""
        url_parser = self._loader.get_anime_url_parser(anime.module)
        logger.info(f"{url_parser.__class__.__name__} parsing {anime.raw_url}")
        url = await url_parser._parse(anime.raw_url)
        if url.is_available():
            return url
        logger.warning(f"Parse real url failed")
        return AnimeInfo()

    def get_anime_proxy_class(self, meta: AnimeMeta) -> Type[AnimeProxy]:
        """获取视频代理器类"""
        return self._loader.get_anime_proxy_class(meta.module)

    async def parse_danmaku_detail(self, meta: DanmakuMeta) -> DanmakuDetail:
        """解析弹幕库详情信息"""
        detail_parser = self._loader.get_danmaku_detail_parser(meta.module)
        if not detail_parser:
            self._loader.load_utils_module(meta.module)
            detail_parser = self._loader.get_danmaku_detail_parser(meta.module)
        logger.info(f"{detail_parser.__class__.__name__} parsing {meta.play_url}")
        if detail_parser is not None:
            return await detail_parser._parse(meta.play_url)
        return DanmakuDetail()

    async def parse_danmaku_data(self, danmaku: Danmaku) -> DanmakuData:
        """解析一集弹幕的数据"""
        data_parser = self._loader.get_danmaku_data_parser(danmaku.module)
        logger.debug(f"{data_parser.__class__.__name__} parsing {danmaku.cid}")
        if data_parser is not None:
            start_time = perf_counter()
            data = await data_parser._parse(danmaku.cid)
            end_time = perf_counter()
            logger.info(f"Reading danmaku data finished in {end_time - start_time:.2f}s")
            return data
        return DanmakuData()

    def change_module_state(self, module: str, enable: bool):
        """设置模块启用状态"""
        return self._loader.change_module_state(module, enable)
