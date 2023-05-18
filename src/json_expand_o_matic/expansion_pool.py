import concurrent.futures
import logging
import os
import time

logger = logging.getLogger(__name__)


def _initialize(data):
    global work
    work = data


def _write_file(request):
    begin = time.time()
    global work
    directory, filename, data = work[request]
    try:
        # Assume that the path will already exist.
        # We'll take a hit on the first file in each new path but save the overhead
        # of checking on each subsequent one. This assumes that most objects will
        # have multiple nested objects.
        with open(f"{directory}/{filename}", "w") as f:
            f.write(data)
    except FileNotFoundError:
        os.makedirs(directory, exist_ok=True)
        with open(f"{directory}/{filename}", "w") as f:
            f.write(data)
    return time.time() - begin


class ExpansionPool:
    def __init__(self, *, logger: logging.Logger, pool_ratio: float = 0.8, pool_size: int = 0):
        assert logger, "Logger is required"
        self.logger = logger
        self.pool_ratio = pool_ratio or 1
        self.pool_size = pool_size or int(os.cpu_count() * self.pool_ratio) or 1
        self.work = list()

    def drain(self):
        begin = time.time()
        chunksize = 1 + int(len(self.work) / self.pool_size)

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.pool_size, initializer=_initialize, initargs=(self.work,)
        ) as pool:
            handler_futures = pool.map(_write_file, range(0, len(self.work)), chunksize=chunksize)
            handler_results = [f for f in handler_futures]

        pool = None

        self.elapsed = time.time() - begin

        self.work_time = sum(handler_results)
        self.overhead = self.elapsed - self.work_time
