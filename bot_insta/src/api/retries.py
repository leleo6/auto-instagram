import time
import logging
import random
from functools import wraps

log = logging.getLogger(__name__)

def with_retries(max_attempts=3, base_delay=5.0, backoff_factor=2.0, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff and jitter.
    Useful for APIs and uploads that might fail due to network or rate limits.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            delay = base_delay
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        log.error("❌ Max retries reached for %s. Final error: %s", func.__name__, e)
                        raise
                    
                    jitter = random.uniform(0, 0.2 * delay)
                    sleep_time = delay + jitter
                    
                    log.warning("⚠️ %s failed on attempt %d/%d (%s). Retrying in %.1fs...", 
                                func.__name__, attempt, max_attempts, e, sleep_time)
                    time.sleep(sleep_time)
                    
                    attempt += 1
                    delay *= backoff_factor
        return wrapper
    return decorator
