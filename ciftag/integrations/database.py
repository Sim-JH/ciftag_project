import time
import contextlib

from sqlalchemy.orm import scoped_session

import ciftag.utils.logger as logger
from ciftag.settings import engine, Session
from ciftag.integrations.redis import RedisManager


logs = logger.Logger()


class DBManager:
    """ sql/orm 방식 지원 DB 연결 매니저
    - Redis Lock을 사용하여 동시 연결 제어 가능
    - REST API 요청을 통한 연결은 ORM 사용
    - 내부 로직 상의 연결은 직접 SQL 사용
    현재 내부 로직 연결 > API 요청 연결인 구조
    """
    def __init__(self, lock_name=None):
        """
        :param lock_name: redis lock key name. None이면 lock 사용하지 않음.
        """
        self.lock_name = lock_name

        if self.lock_name:
            self.r = RedisManager()

    @staticmethod
    def __connection_with_lock(func):
        """ Redis Lock을 이용한 동시 연결 제어 데코레이터.
        lock 관리 정책은 RedisManager.acquire_lock()에 서술
        :param func: Connection class function
        """
        def wrapper(self, *args, **kwargs):
            """ :param self: Connection class instance """
            if self.lock_name is None:
                return func(self, *args, **kwargs)

            lock_attempts = 0  # lock 획득 재시도 횟수
            sleep_interval = 0.1

            while lock_attempts < self.r.lock_attempts_limit:
                try:
                    # lock 획득 요청
                    lock, have_lock = self.r.acquire_redis_lock(self.lock_name)
                except Exception as e:
                    # lock 획득 시도 시 redis-py 내부 모듈에 의한 error catch
                    logs.log_data(f"---LockError on redis lock acquire: ", str(e))
                    lock_attempts += 1
                    time.sleep(sleep_interval)
                    sleep_interval *= 2
                    continue

                if have_lock:
                    try:
                        # lock 내부 db 커넥션 수행
                        result = func(self, *args, **kwargs)
                        return result
                    finally:
                        lock.release()
                else:
                    # lock을 얻지 못하면 다시 요청 (스핀락)
                    lock_attempts += 1
                    time.sleep(sleep_interval)
                    sleep_interval *= 2

            # 락 획득 재시도 횟수가 최대 재시도 횟수를 넘었을 시, 로깅 후 일반 연결
            logs.log_data(f"---{str(args[0])} 요청에 대한 lock 획득 실패. 일반 연결")
            result = func(self, *args, **kwargs)

            return result
        return wrapper

    @__connection_with_lock
    @contextlib.contextmanager
    def create_connection(self):
        """ 직접 쿼리 실행 DB 연결 컨텍스트 매니저 (고성능)
        redis lock을 통한 분산 연결 지원
        """
        __connection = engine.connect()
        trans = __connection.begin()
        try:
            yield __connection
            trans.commit()
        except Exception as e:
            trans.rollback()
            logs.log_data(f"Transaction rollback due to error: {str(e)}")
            raise
        finally:
            __connection.close()

    @contextlib.contextmanager
    def create_session(self) -> scoped_session:
        """orm 세션 컨텍스트 매니저
        지정한 pool 사이즈 사용
        """
        __session = Session()
        try:
            yield __session
            __session.commit()
        except Exception as e:
            __session.rollback()
            logs.log_data(f"Session rollback due to error: {str(e)}")
            raise
        finally:
            __session.close()

