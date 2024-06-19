from typing import Optional, List, Dict, Any
import redis
from loguru import logger
import json
import config

class RedisManager:
    redis_client: redis.Redis
    def __init__(self):
        self.redis_client = redis.Redis(host=config.redis_host, port=int(config.redis_port), db=0, password=config.redis_password, protocol=3)

    def save_odds(self, event_code: str, odds_data: Optional[List[Dict[str, str]]]):
        redis_key = f"odds:marathobet:{event_code}"
        if odds_data is not None:
            odds_data_json_str = json.dumps(odds_data)
            self.redis_client.set(redis_key, odds_data_json_str)
        else:
            self.redis_client.delete(redis_key)
