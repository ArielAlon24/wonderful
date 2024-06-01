import asyncio
from typing import TypeVar, Generic

K = TypeVar("K")
V = TypeVar("V")


class AsyncDict(Generic[K, V]):
    def __init__(self):
        self._dict = {}
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> V | None:
        async with self._lock:
            return self._dict[key]

    async def set(self, key: K, value: V) -> None:
        async with self._lock:
            self._dict[key] = value

    async def remove(self, key: K) -> None:
        async with self._lock:
            del self._dict[key]

    async def contains(self, key: K) -> bool:
        async with self._lock:
            return key in self._dict
