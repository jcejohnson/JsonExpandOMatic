import logging
from multiprocessing.pool import ThreadPool
from queue import Queue

logger = logging.getLogger(__name__)


class ExpansionPool:
    INSTANCE = None

    def __init__(self):
        self._pool = None
        self._results = Queue()
        self._auto_destroy = True

    @classmethod
    def create_singleton(cls, auto_destroy=True):
        cls.INSTANCE = cls()
        cls._auto_destroy = auto_destroy
        return cls.INSTANCE

    @classmethod
    def destroy_singleton(cls):
        cls.INSTANCE = None

    def execute(self, callable):
        with ThreadPool() as self._pool:
            result = callable()

            while not self._results.empty():
                self._results.get().wait()

            # close the pool
            self._pool.close()
            # wait for all tasks to complete
            self._pool.join()

        self._pool = None

        if self.__class__.INSTANCE and self is self.__class__.INSTANCE and self._auto_destroy:
            self.destroy_singleton()

        return result

    def invoke(self, task):
        result = self._pool.apply_async(task)
        self._results.put(result)
        return result
