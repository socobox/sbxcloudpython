import json
import logging
import os
from typing import Dict, List, Optional, Type, TypeVar, Set

import redis.asyncio as redis
from pydantic import BaseModel

CachedType = TypeVar("CachedType", bound=BaseModel)


logger = logging.getLogger(__name__)


class RedisService:
    _redis: Optional[redis.Redis] = None
    _host: str
    _port: int
    _user: Optional[str] = None
    _password: Optional[str] = None

    def __init__(
        self,
        host: str,
        port: int,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        # fail if host is empty
        if host is None or len(host) == 0:
            raise TypeError(
                "host must be provided, port, user and password are optional"
            )

        self._redis = None
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    async def get_connection(self) -> "RedisService":
        if not self._redis:
            # catch ConnectionRefusedError
            try:
                if self._user and self._password:
                    self._redis = await redis.from_url(
                        f"redis://{self._user}:{self._password}@{self._host}:{self._port}"
                    )
                    await self._redis.ping()
                    logger.info("Redis connection established")
                else:
                    self._redis = await redis.from_url(
                        f"redis://{self._host}:{self._port}"
                    )
                    await self._redis.ping()
                    logger.info("Redis connection established")

                if not self._redis:
                    raise RuntimeError("Redis connection is not established")

            except redis.ConnectionError as e:
                # print stack trace to error log
                logger.error(e, exc_info=True)
                raise RuntimeError("Redis connection is not established") from e

        return self

    async def close_connection(self):
        if self._redis is not None:
            await self._redis.close()

    async def get_object(
        self, key: str, result_type: Type[CachedType]
    ) -> Optional[CachedType]:
        await self.get_connection()
        raw_result = await self._redis.get(key)
        if raw_result is not None:
            result = json.loads(raw_result)
            return result_type(**result)
        return None

    async def set_object(self, key: str, value: CachedType, ex: Optional[int] = None) -> None:
        await self.get_connection()
        value_as_json = value.model_dump_json()
        if ex is None:
            await self._redis.set(key, value_as_json)
        else:
            await self._redis.set(key, value_as_json, ex=ex)

    async def mset_objects(self, items: Dict[str, CachedType], ex: Optional[int] = None) -> None:
        await self.get_connection()
        # map as set of key, item
        items_as_json = {key: item.model_dump_json() for key, item in items.items()}
        if ex is None:
            await self._redis.mset(items_as_json)
        else:
            for key, item in items.items():
                await self._redis.set(key, item.model_dump_json(), ex=ex)

    async def mget_objects(
        self, keys: List[str], result_type: Type[CachedType]
    ) -> Optional[List[CachedType]]:
        await self.get_connection()
        values = await self._redis.mget(*keys)
        return [result_type(**json.loads(value)) if value else None for value in values]

    async def push_to_queue(self, queue_name: str, data: CachedType) -> None:
        await self.get_connection()
        tmp_json = data.model_dump_json()
        await self._redis.rpush(queue_name, tmp_json)

    async def set_keys_index(self, index_key: str, keys: List[str], ex: Optional[int] = None) -> None:
        """Store a list of keys as index"""
        await self.get_connection()
        # Convert set of keys to string before storing
        keys_as_str = json.dumps(keys)
        if ex is None:
            await self._redis.set(index_key, keys_as_str)
        else:
            await self._redis.set(index_key, keys_as_str, ex=ex)

    async def get_keys_index(self, index_key: str) -> List[str]:
        """Retrieve a list of keys from index"""
        await self.get_connection()
        keys_as_str = await self._redis.get(index_key)
        # If keys exist, convert from string back to list
        return json.loads(keys_as_str) if keys_as_str else []


def get_redis_service() -> RedisService:
    logger.info("Starting Redis Service")

    host: str = os.environ.get("REDIS_HOST", "localhost")
    port: int = int(os.environ.get("REDIS_PORT", 6379))
    user: Optional[str] = os.environ.get("REDIS_USER", None)
    password: Optional[str] = os.environ.get("REDIS_PASSWORD", None)
    logger.debug(
        f"Redis host: {host}, port: {port}, user: {user}, password: {password}"
    )
    return RedisService(host, port, user, password)
