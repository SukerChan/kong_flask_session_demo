import os
import sys

import redis

redis_pool = redis.ConnectionPool(host='localhost')


def get_redis() -> redis.Redis:
    global redis_pool
    r = redis.Redis(connection_pool=redis_pool)
    return r
