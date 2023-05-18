import concurrent.futures
import logging
import os
from multiprocessing import Queue as Queue
from typing import Callable

logger = logging.getLogger(__name__)


def _write_file(request):
    directory, filename, data = [r for r in request]
    try:
        # Assume that the path will already exist.
        # We'll take a hit on the first file in each new path but save the overhead
        # of checking on each subsequent one. This assumes that most objects will
        # have multiple nested objects.
        with open(filename, "w") as f:
            f.write(data)
    except FileNotFoundError:
        os.makedirs(directory, exist_ok=True)
        with open(filename, "w") as f:
            f.write(data)


class ExpansionPool:
    def __init__(self, *, logger):
        self.logger = logger

        self._pool: concurrent.futures.Executor = None
        self._futures: Queue = Queue()
        self._results = list()
        self._auto_destroy: bool = True
        self.pool_size: int = None
        self.queue = Queue()

    def execute(self, main: Callable):
        self.pool_size = int(os.cpu_count() * 0.8) or 1
        handler_results = list()
        handler_futures = list()
        with concurrent.futures.ProcessPoolExecutor(self.pool_size) as self._pool:
            # Something could add to the queue before calling execute()

            # The entry point may add to the queue.
            main_result = main()

            # This outer loop is in case the handlers add things to the queue.
            while self.queue.qsize():
                queue_size = self.queue.qsize()

                self.logger.debug(f"Queue size: {queue_size}")

                self.logger.debug("Gathering work")
                work = list()
                while self.queue.qsize():  # while len(work) < queue_size:
                    args = self.queue.get()
                    work.append(args)
                self.logger.debug(f"Work size : {len(work)}")

                chunksize = 1 + int(len(work) / self.pool_size)
                self.logger.debug(f"Submitting work with chunksize {chunksize}")
                handler_futures = self._pool.map(_write_file, work, chunksize=chunksize)

                self.logger.debug("Gathering results")
                for handler_result in handler_futures:
                    handler_results.append(handler_result)

            self.logger.debug("Queue is empty")

        self._pool = None

        return main_result, handler_results
