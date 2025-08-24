import redis.asyncio as redis  # <-- The correct modern async import
from redis.exceptions import ConnectionError as RedisConnectionError

import json
import os
import sqlite3
from .config import settings
import logging

logger = logging.getLogger(__name__)

_redis_client = None
_sql_conn = None

async def get_redis():
    """
    Establishes an asynchronous Redis connection pool.
    """
    global _redis_client
    if settings.REDIS_URL:
        if _redis_client is None:
            # Use redis.from_url for the async client, it returns a connection pool
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _redis_client
    return None

async def check_redis_connection():
    """
    Checks if a connection can be established to Redis.
    Raises an exception if the connection fails.
    """
    logger = logging.getLogger(__name__)
    logger.info("Checking Redis connection...")
    try:
        redis_client: Redis = await get_redis()
        if not redis_client:
            logger.error("Redis is disabled. REDIS_URL is not configured.")
            # In our new design, Redis is required, so we should raise an error.
            raise ConnectionError("Redis is required but REDIS_URL is not configured.")
        
        # The PING command is the standard way to check if Redis is alive.
        await redis_client.ping()
        logger.info("Redis connection successful.")
    except RedisConnectionError as e:
        logger.error(f"FATAL: Could not connect to Redis at {settings.REDIS_URL}. Please ensure it is running.")
        logger.error(f"Connection error: {e}")
        # Re-raise the exception to stop the application from starting.
        raise



def sqlite_setup():
    """
    Sets up the fallback SQLite database. This remains synchronous.
    """
    global _sql_conn
    if _sql_conn is None:
        _sql_conn = sqlite3.connect('cache.db', check_same_thread=False)
        c = _sql_conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)')
        _sql_conn.commit()
    return _sql_conn

async def get_cached(key: str):
    """
    Asynchronously gets a value from the Redis cache, with SQLite fallback.
    """
    r = await get_redis()
    if r:
        val = await r.get(key)
        return json.loads(val) if val else None
    
    # Fallback to SQLite
    conn = sqlite_setup()
    cur = conn.cursor()
    cur.execute('SELECT v FROM cache WHERE k=?', (key,))
    row = cur.fetchone()
    return json.loads(row[0]) if row else None

async def set_cached(key: str, value, expire: int = None):
    """
    Asynchronously sets a value in the Redis cache, with SQLite fallback.
    """
    r = await get_redis()
    if r:
        await r.set(key, json.dumps(value), ex=expire)
        return
    
    # Fallback to SQLite
    conn = sqlite_setup()
    cur = conn.cursor()
    cur.execute('REPLACE INTO cache (k,v) VALUES (?,?)', (key, json.dumps(value)))
    conn.commit()