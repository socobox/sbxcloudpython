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
        key: str, result_type: Type[CachedType], use_cache=True, ex: Optional[int] = None
    ) -> Optional[CachedType]:
        if not issubclass(result_type, SBXModel) or result_type.get_model() is None:
            logger.error(f"type of {type(result_type)} is not a subclass of SBXModel")
            raise ValueError("result_type must be a subclass of SBXModel")
        keys_idx = f"{result_type.get_model()}:*"
        cache_key = f"sbx:{result_type.get_model()}:{key}"
        cached_keys: Set[str] = set()
        model_instance = None
        await redis_service.get_connection()
        if use_cache:
            try:
                cached_keys: Set[str] = set(
                    await redis_service.get_keys_index(keys_idx) or []
                )
                if key in cached_keys:
                    model_instance = await redis_service.get_object(cache_key, result_type)
                    if model_instance:
                        return model_instance
            except Exception as e:
                logger.exception(f"An error occurred while retrieving data: {e}")
        try:
            query = SBXCachedService.find(result_type.get_model())
            query.where_with_keys([key])
            model_instance = SBXResponse(**await query.find()).first(result_type)

            if model_instance:
                await redis_service.set_object(cache_key, model_instance, ex)
                cached_keys.add(key)
                await redis_service.set_keys_index(
                    f"{result_type.get_model()}:*", list(cached_keys), ex
                )

            return model_instance
        except Exception as e:
            logger.exception(f"An error occurred while retrieving data: {e}")
            return model_instance

        # finally:
        #     await redis_service.close_connection()  # If applicable.

    @staticmethod
    async def list(
        result_type: Type[CachedType], use_cache=True, ex: Optional[int] = None
    ) -> Optional[List[CachedType]]:
        if not issubclass(result_type, SBXModel):
            logger.error(f"type of {type(result_type)} is not a subclass of SBXModel")
            raise ValueError("result_type must be a subclass of SBXModel")

        logger.debug(f"Retrieving list of {result_type}")
        keys_idx = f"{result_type.get_model()}:*"
        model_instances = None
        try:

            if use_cache:
                cache_keys: Set[str] = set(
                    await redis_service.get_keys_index(keys_idx) or []
                )
                if len(cache_keys) > 0:
                    model_instances = await redis_service.mget_objects(
                        list(
                            [f"sbx:{result_type.get_model()}:{k}" for k in cache_keys]
                        ),
                        result_type,
                    )
                    model_instances = [
                        model_instance
                        for model_instance in model_instances
                        if model_instance is not None
                    ]

                    if model_instances and len(model_instances) == len(cache_keys):
                        return model_instances
        except Exception as e:
            logger.exception(f"An error occurred while retrieving data: {e}")
        try:
            query = SBXCachedService.find(result_type.get_model())

            all_data = await query.find_all_query()

            model_instances = SBXResponse(**query.merge_results(all_data)).all(
                result_type
            )

            if model_instances:
                model_map = {
                    f"sbx:{result_type.get_model()}:{instance.key}": instance
                    for instance in model_instances
                }
                # save the items in cache
                await redis_service.mset_objects(model_map, ex)
                # update the index
                cache_keys = {instance.key for instance in model_instances}
                await redis_service.set_keys_index(keys_idx, list(cache_keys), ex)

            return model_instances

        except Exception as e:
            logger.exception(f"An error occurred while retrieving data: {e}")
            return model_instances
        # finally:
        #     await redis_service.close_connection()  # If applicable.