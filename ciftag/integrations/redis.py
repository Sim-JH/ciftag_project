from redis import Redis

import ciftag.utils.logger as logger
from ciftag.settings import env_key

logs = logger.Logger(log_dir='Redis')


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

    def check_and_add_with_lua(self, name: str, val: str) -> bool:
        """ Lua 스크립트를 사용한 중복 체크 및 추가를 원자적으로 수행
        Lua 스크립트는 Redis의 단일 스레드 구조를 활용 하기에, 동시에 요청이 오더라도 락처럼 내부적으로 한 번에 하나의 스크립트만 처리.
        단, 현재는 단일 노드의 경우에만 원자성을 보장하므로, 멀티 노드에서는 키 태그 혹은 레드락 알고리즘 사용
        키 태그 : name = f"{name}:{{{tag}}}"
        false 중복, true 추가 성공
        """
        script = """
        if redis.call("SISMEMBER", KEYS[1], ARGV[1]) == 1 then
            return 0
        else
            redis.call("SADD", KEYS[1], ARGV[1])
            return 1
        end
        """
        result = self.redis.eval(script, 1, name, val)

        return bool(result)

    def delete_set_from_redis(self, name: str):
        """사용한 redis set 삭제"""
        if not self.redis.exists(name):
            logs.log_data(f'Redis Name Not Exsist: {name}')
        else:
            self.redis.delete(name)

    def increase_key(self, name):
        """key의 value 증가 후 반환"""
        return self.redis.incr(name)

    def set_expire(self, name, limit_cnt):
        """key의 제한시간 설정"""
        self.redis.expire(name, limit_cnt)

    def get_ttl(self, name):
        """key의 만료시간 조회"""
        return self.redis.ttl(name)

