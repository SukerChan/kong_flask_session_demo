import os
import sys

import redis
from dotenv import load_dotenv

load_dotenv()

redis_pool = redis.ConnectionPool(host=os.environ.get('REDIS_HOST', 'localhost'),
                                  port=os.environ.get('REDIS_PORT', 6379))


def get_redis() -> redis.Redis:
    global redis_pool
    r = redis.Redis(connection_pool=redis_pool)
    return r
