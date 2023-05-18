import concurrent.futures
import logging
import os
from queue import Queue
from time import sleep
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
    def create_singleton(cls, auto_destroy: bool = True):
        cls.INSTANCE = cls()
        cls._auto_destroy = auto_destroy
        return cls.INSTANCE

    @classmethod
    def destroy_singleton(cls):
        cls.INSTANCE = None

    def execute(self, main: Callable):
        self.pool_size = int(os.cpu_count() / 2 + 1)
        handler_results = list()
        handler_futures = list()
        with concurrent.futures.ProcessPoolExecutor(self.pool_size) as self._pool:
            # Something could add to the queue before calling execute()

            # The entry point may add to the queue.
            main_result = main()

            # This outer loop is in case the handlers add things to the queue.
            while not self.queue.empty():
                print(f"Queue size: {self.queue.qsize()}")

                # Iterate through whatever is in the queue and work to the pool.
                while not self.queue.empty():
                    handler, args, kwargs = self.queue.get()
                    handler_future = self._pool.submit(handler, *args, **kwargs)
                    handler_futures.append(handler_future)

                # Wait for this batch to complete.
                for handler_result in concurrent.futures.as_completed(handler_futures):
                    handler_results.append(handler_result.result())

            print("Queue is empty")

        self._pool = None

        if self.__class__.INSTANCE and self is self.__class__.INSTANCE and self._auto_destroy:
            self.destroy_singleton()

        return main_result, handler_results

    def invoke(self, task: Callable, *args, **kwargs) -> concurrent.futures.Future:
        future: concurrent.futures.Future = self._pool.submit(task, *args, **kwargs)
        self._futures.put(future)
        return future
