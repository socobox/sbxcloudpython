import logging
import os
from abc import ABCMeta
from typing import Type, Optional, TypeVar, List

from deepmerge import always_merger
from pydantic import BaseModel, ValidationError
from sbxpy import SbxCore as Sc, Find, SbxCore

from sbxpy.cache import get_redis_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar(
    "T", bound=BaseModel
)  # Use bound if you want T to be a subclass of BaseModel


class SBXService(metaclass=ABCMeta):
    # This is your abstract base class

    @staticmethod
    def find(model_name: str, page: int = 1, page_size: int = 1000) -> Find:
        sbx: SbxCore = SBX.get_instance()
        query = sbx.with_model(model_name)
        query.set_page(page)
        query.set_page_size(page_size)
        return query

    @staticmethod
    async def get_by_key(
        model_name: str, result_type: Type[T], key: str
    ) -> Optional[T]:
        query = SBXService.find(model_name, page_size=1)
        query.where_with_keys([key])
        return SBXResponse(**await query.find()).first(result_type)

    @staticmethod
    async def list_all(model_name: str, result_type: Type[T]) -> Optional[List[T]]:
        query = SBXService.find(model_name)
        return SBXResponse(**await query.find()).all(result_type)


class SBX:
    _instance: Optional[Sc] = None

    @classmethod
    def get_instance(cls) -> Sc:
        if cls._instance is None:
            cls._instance = Sc()
            token = os.environ.get("SBX_TOKEN")
            app_key = os.environ.get("SBX_APP_KEY")
            cls._instance.initialize(os.environ.get("SBX_DOMAIN"), app_key, os.environ.get("SBX_HOST"))
            if not all([token, app_key]):
                raise Exception(
                    "SBX_TOKEN and SBX_APP_KEY must be provided as environment variables"
                )
            cls._instance.headers["Authorization"] = "Bearer " + token
        return cls._instance


class SBXResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    results: Optional[List[dict]] = None
    fetched_results: Optional[dict[str, dict[str, dict]]] = None

    @staticmethod
    def merge(responses: List[dict]) -> "SBXResponse":
        merged_results = []
        merged_fetched_results = {}

        sbx_responses: List[SBXResponse] = [SBXResponse(**res) for res in responses]

        for response in sbx_responses:
            if response.results:
                merged_results.extend(response.results)

            if response.fetched_results:
                # deep merge fetched results dictionaries
                merged_fetched_results = always_merger.merge(
                    merged_fetched_results, response.fetched_results
                )

        return SBXResponse(
            success=all(response.success for response in sbx_responses),
            message="Merged Results",
            results=merged_results,
            fetched_results=merged_fetched_results,
        )

    def has_results(self) -> bool:
        return self.success and self.results is not None and len(self.results) > 0

    def first(self, type_def: Type[T]) -> Optional[T]:
        try:
            if self.results:
                return type_def(**self.results[0])
        except ValidationError as e:
            logger.error(
                f"Pydantic validation error for type_def: {type_def}, errors: {e.errors()}"
            )
            raise e
        return None

    def all(self, type_def: Type[T]) -> List[T]:
        if self.results:
            return [type_def(**result) for result in self.results]
        return []

    #     given a dictionary of [string:[string:dic]] return a Type[T] dictionary
    # in other words, given a json of { "fetched_results": { "model": { "key": { "field": "value" } } } }
    def get_ref(self, model: str, key: str, type_def: Type[T]) -> Optional[T]:
        if self.fetched_results and model in self.fetched_results:
            if key in self.fetched_results[model]:
                try:
                    dict_obj = self.fetched_results[model][key]
                    return type_def(**dict_obj)

                except ValidationError as e:
                    print(
                        f"Pydantic validation error for model: {model}, key: {str(key)}, errors: {e.errors()}"
                    )
            else:
                print(
                    f"get_ref: model: {model}, key: {key}, type_def: {type_def} not found in fetched_results[model]"
                )
        else:
            print(
                f"get_ref: model: {model}, key: {key}, type_def: {type_def} not found in fetched_results"
            )

        return None
