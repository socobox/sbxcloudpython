from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


def sbx(**kwargs):
    def inner_cls(cls):
        cls._model = kwargs.get("model", None)
        return cls

    return inner_cls


class MetaModel(BaseModel):
    created_time: Optional[datetime] = Field(
        None, description="The creation time in ISO 8601 format"
    )
    updated_time: Optional[datetime] = Field(
        None, description="The updated time in ISO 8601 format"
    )


class SBXModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    key: Optional[str] = Field(None, alias="_KEY")
    _META: Optional[MetaModel] = None

    @classmethod
    def get_model(cls):
        return cls._model

    def __hash__(self):
        return hash(self.key) if self.key is not None else id(self)

    def __eq__(self, other):
        if isinstance(other, SBXModel):
            return self.key == other.key if self.key is not None else self is other
        return NotImplemented
