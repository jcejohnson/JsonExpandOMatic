import os
import logging
import concurrent.futures
from queue import Queue
from typing import Callable, List

logger = logging.getLogger(__name__)


class ExpansionPool:
    INSTANCE: "ExpansionPool" = None

    def __init__(self):
        self._pool: concurrent.futures.Executor = None
        self._futures: Queue = Queue()
        self._results = list()
        self._auto_destroy: bool = True
        self.pool_size: int = None
        self.queue = Queue()

    @classmethod
    def create_singleton(cls, auto_destroy: bool=True):
        cls.INSTANCE = cls()
        cls._auto_destroy = auto_destroy
        return cls.INSTANCE

    @classmethod
    def destroy_singleton(cls):
        cls.INSTANCE = None

    def execute(self, callable: Callable):
        self.pool_size = int(os.cpu_count/2+1)
        with concurrent.futures.ProcessPoolExecutor(self.pool_size) as self._pool:
            result = callable()

            while not self._futures.empty():
                print(self._futures.qsize())

                futures = list()
                while not self._futures.empty():
                    futures.append(self._futures.get())

                print(len(futures))

                for result in concurrent.futures.as_completed(futures):
                    self._results.append(result.result())
                    # print(len(self._results), end=" ")
                # print("")

                # result: concurrent.futures.Future = self._futures.get()
                # self._results.put(result)

            print("Queue is empty")

        self._pool = None

        if self.__class__.INSTANCE and self is self.__class__.INSTANCE and self._auto_destroy:
            self.destroy_singleton()

        return result

    def invoke(self, task: Callable, *args, **kwargs) -> concurrent.futures.Future:
        future: concurrent.futures.Future = self._pool.submit(task, *args, **kwargs)
        self._futures.put(future)
        return future
