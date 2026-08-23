import os
import json
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.models import SearchResult
from backend.config import config


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        pass


class DemoSearchProvider(SearchProvider):
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        return []


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com/search"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            return []
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                json={"api_key": self.api_key, "query": query, "max_results": max_results, "search_depth": "basic"},
                timeout=aiohttp.ClientTimeout(total=config.WEB_SEARCH_TIMEOUT),
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                results = []
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="tavily",
                    ))
                return results


class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.SERPER_API_KEY
        self.base_url = "https://google.serper.dev/search"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            return []
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json={"q": query, "num": max_results},
                timeout=aiohttp.ClientTimeout(total=config.WEB_SEARCH_TIMEOUT),
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                results = []
                for item in data.get("organic", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="serper",
                    ))
                return results


def get_search_provider() -> SearchProvider:
    provider_name = config.WEB_SEARCH_PROVIDER.lower()
    if provider_name == "tavily":
        return TavilySearchProvider()
    elif provider_name == "serper":
        return SerperSearchProvider()
    return DemoSearchProvider()
