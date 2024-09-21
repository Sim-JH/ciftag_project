from redis import Redis

from ciftag.settings import env_key


class RedisManager:
    def __init__(self):
        host = env_key.REDIS_HOST
        port = env_key.REDIS_PORT

        # lock 획득 재시도 제한
        self.lock_attempts_limit = 5

        # redis connection
        self.redis = Redis(
            host=host,
            port=port,
            decode_responses=True
        )

    def acquire_redis_lock(self, lock_name: str):
        """distributed lock using redis"""
        lock_name = lock_name
        time_out = 60  # 락 내부 실행 최대 대기 시간/초 (쿼리 실행 대기 시간)
        sleep_time = 0.1  # 각 작업간 유휴 시간
        blocking = True  # lock acquire 블로킹 체크 여부
        blocking_timeout = env_key.REDIS_LOCK_WAITING  # lock 획득을 위한 최대 대기 시간 (None: 무제한)

        lock = self.redis.lock(lock_name, timeout=time_out, sleep=sleep_time)
        have_lock = lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)

        return lock, have_lock

    def check_set_form_redis(self, name: str, val: str) -> bool:
        """set 존재 시 1, 없을 시 0 -> bool로 변환하여 반환"""
        return bool(self.redis.sismember(name, val))

    def add_set_to_redis(self, name: str, val: str):
        """redis set 추가"""
        self.redis.sadd(name, val)

    def delete_set_from_redis(self, name: str):
        """redis set 추가"""
        self.redis.sadd(name)

