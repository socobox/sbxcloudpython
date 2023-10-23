import logging
from typing import Type, Optional, TypeVar, Set, List

from sbxpy.cache import get_redis_service
from sbxpy.sbx import SBXService, SBXResponse
from sbxpy.domain import SBXModel

# initialize logger
logger = logging.getLogger(__name__)

redis_service = get_redis_service()
CachedType = TypeVar("CachedType", bound=SBXModel)


class SBXCachedService(SBXService):
    @staticmethod
    async def get(
        key: str, result_type: Type[CachedType], use_cache=True
    ) -> Optional[CachedType]:
        try:
            await redis_service.get_connection()
            cached_keys: Set[str] = set(
                await redis_service.get_keys_index(f"{result_type.get_model()}:*") or []
            )

            cache_key = f"{result_type.get_model()}:{key}"

            if use_cache and key in cached_keys:
                model_instance = await redis_service.get_object(cache_key, result_type)
                if model_instance:
                    return model_instance

            query = SBXCachedService.find(result_type.get_model())
            query.where_with_keys([key])
            model_instance = SBXResponse(**await query.find()).first(result_type)

            if model_instance:
                await redis_service.set_object(cache_key, model_instance)
                cached_keys.add(key)
                await redis_service.set_keys_index(
                    f"{result_type.get_model()}:*", list(cached_keys)
                )

            return model_instance

        except Exception as e:
            logger.exception(f"An error occurred while retrieving data: {e}")
        finally:
            await redis_service.close_connection()  # If applicable.

    @staticmethod
    async def list(
        result_type: Type[CachedType], use_cache=True
    ) -> Optional[List[CachedType]]:
        try:
            keys_idx = f"{result_type.get_model()}:*"
            if use_cache:
                cache_keys: Set[str] = set(
                    await redis_service.get_keys_index(keys_idx) or []
                )
                if len(cache_keys) > 0:
                    model_instances = await redis_service.mget_objects(
                        list(cache_keys), result_type
                    )
                    if model_instances:
                        return model_instances

            query = SBXCachedService.find(CachedType.get_model())
            model_instances = SBXResponse(**await query.find()).all(result_type)

            if model_instances:
                model_map = {
                    f"{result_type.get_model()}:{instance.key}": instance
                    for instance in model_instances
                }
                # save the items in cache
                await redis_service.mset_objects(model_map)
                # update the index
                cache_keys = {instance.key for instance in model_instances}
                await redis_service.set_keys_index(keys_idx, list(cache_keys))

            return model_instances

        except Exception as e:
            logger.exception(f"An error occurred while retrieving data: {e}")
        # finally:
        #     await redis_service.close_connection()  # If applicable.
