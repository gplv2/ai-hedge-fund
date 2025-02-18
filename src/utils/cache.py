import redis
import functools
import json
import hashlib
import pandas as pd
from pprint import pprint
from pydantic.json import pydantic_encoder

# Set up Redis connection (configure as needed)
r = redis.Redis(host='localhost', port=6379, db=0)

#def custom_serializer(o):
#    if isinstance(o, pd.Timestamp):
#        return o.isoformat()
#    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

# Set up Redis connection
r = redis.Redis(host='localhost', port=6379, db=0)

def custom_serializer(o):
    if isinstance(o, pd.Timestamp):
        return o.isoformat()  # Convert Timestamp to ISO string
    # You can add more cases if needed.
    # Fall back to the Pydantic encoder for other objects.
    try:
        return pydantic_encoder(o)
    except Exception:
        return str(o)
    
def redis_cache(expire=600):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            pprint(key_data)
            # {'args': (<tools.api.financials_client.FinancialsAPIClient object at 0x7f5075221820>,
            # 'NVDA'),
            # 'func': 'get_company_news',
            # 'kwargs': {'end_date': '2025-02-17',
            # 'limit': 1000,
            # 'start_date': '2024-02-17'}}

            # Generate a unique cache key; combine kwargs and args and func
            key_data = {
                'func': func.__name__,
                "args": args[1:],  # skip the first argument
                "kwargs": kwargs
            }
            key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
            key = f"cache:{func.__name__}:{key_hash}"
            #key = f"cache:{hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()}"
            cached = r.get(key)
            if cached:
                data = json.loads(cached)
                # If data is stored as a DataFrame, check for our marker.
                if isinstance(data, dict) and data.get('__dataframe__'):
                    return pd.DataFrame(**data['data'])
                return data
            
            # Call the actual function.
            result = func(*args, **kwargs)
            
            # Serialize the result:
            if isinstance(result, pd.DataFrame):
                # Convert the DataFrame using the 'split' orientation.
                # Use our custom serializer to handle Timestamps.
                serialized = json.dumps({
                    '__dataframe__': True,
                    'data': result.to_dict(orient='split')
                }, default=custom_serializer)
            else:
                serialized = json.dumps(result, default=pydantic_encoder)
            
            r.set(key, serialized, ex=expire)
            return result
        return wrapper
    return decorator
