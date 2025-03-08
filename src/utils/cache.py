import msgpack
import redis
from pydantic import BaseModel
from functools import wraps
from typing import Any
import hashlib
import json
import inspect


# Setup Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=False)

# Helper function to serialize a Pydantic model to msgpack
def serialize_pydantic(model: Any) -> bytes:
    if isinstance(model, list):
        return msgpack.packb([item.dict() if isinstance(item, BaseModel) else item for item in model], use_bin_type=True)
    elif isinstance(model, dict):
        return msgpack.packb({k: v.dict() if isinstance(v, BaseModel) else v for k, v in model.items()}, use_bin_type=True)
    elif isinstance(model, BaseModel):
        return msgpack.packb(model.dict(), use_bin_type=True)
    else:
        return msgpack.packb(model, use_bin_type=True)  # Fallback for non-model types


# Helper function to recursively deserialize msgpack data to a Pydantic model
def deserialize_pydantic(data: bytes, model_class: BaseModel) -> Any:
    deserialized_data = msgpack.unpackb(data, raw=False)

    # Handle the case when the data is a list of models
    if isinstance(deserialized_data, list):
        return [deserialize_pydantic_item(item, model_class) for item in deserialized_data]
    
    # Handle single model
    return deserialize_pydantic_item(deserialized_data, model_class)


# Recursive deserialization for individual items
def deserialize_pydantic_item(item: Any, model_class: BaseModel) -> BaseModel:
    if isinstance(item, dict):
        # If the item is a dictionary, we use model_class to create an instance
        return model_class(**item)
    elif isinstance(item, list):
        # If the item is a list, we deserialize the items in the list
        return [deserialize_pydantic_item(i, model_class) for i in item]
    else:
        # For any other cases, directly return the item (not a Pydantic model)
        return item


# Generate a cache key based on the function name and arguments
def generate_cache_key(func, args, kwargs):
    cache_key = f"{func.__name__}:{json.dumps((args[1:], kwargs), sort_keys=True)}"
    return hashlib.sha256(cache_key.encode()).hexdigest()

# The decorator to cache API responses in Redis
def cache_api_response(timeout: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(func, args, kwargs)

            # Check if data is cached in Redis
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return_type = inspect.signature(func).return_annotation

                if hasattr(return_type, '__origin__') and return_type.__origin__ == list:
                    # Handle List[Model]
                    model_class = return_type.__args__[0]
                    return deserialize_pydantic(cached_data, model_class)
                elif isinstance(return_type, type) and issubclass(return_type, BaseModel):
                    # Handle a single BaseModel
                    return deserialize_pydantic(cached_data, return_type)

            # If no cache, make the API call and cache the result
            result = func(*args, **kwargs)

            # Serialize the result (handle single or list of models)
            if isinstance(result, list):
                model_class = result[0].__class__ if result else None
                if model_class:
                    serialized_data = serialize_pydantic(result)
            elif isinstance(result, BaseModel):
                model_class = result.__class__
                serialized_data = serialize_pydantic(result)
            else:
                serialized_data = serialize_pydantic(result)  # Serialize any other types

            # Cache the serialized data in Redis with the generated key
            redis_client.setex(cache_key, timeout, serialized_data)

            return result

        return wrapper
    return decorator
