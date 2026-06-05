from typing import Annotated, Any
from bson import ObjectId
from pydantic import BeforeValidator, ConfigDict, PlainSerializer
from pydantic_core import core_schema

# Custom type for MongoDB ObjectId
# This allows Pydantic to handle ObjectId as a string in JSON and as an ObjectId in Python
PyObjectId = Annotated[
    str,
    BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x),
    PlainSerializer(lambda x: str(x), return_type=str),
]
