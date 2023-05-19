"""
Use a ProcessPoolExecutor to save the data in parallel rather than serially.
"""

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

    """
    the_work = [work[request][0]]
    if request < 0:
        the_work.extend(work[request][1:3])
    elif request > 0:
        the_work.extend(work[request][3:5])
    else:
        the_work = work[request]

    the_work = work[request]
    l = len(the_work)

    if l == 3:
        directory, filename, data = the_work
        checksum_filename = checksum = None
    elif l == 5:
        directory, filename, data, checksum_filename, checksum = the_work
    else:
        assert l == 3 or l == 5, f"Invalid work length {l}"
    """
    directory, filename, data, checksum_filename, checksum = work[request]

    def do():
        with open(f"{directory}/{filename}", "w") as f:
            f.write(data)
        if checksum_filename and checksum:
            with open(f"{directory}/{checksum_filename}", "w") as f:
                f.write(checksum)

    try:
        # Assume that the path will already exist.
        # We'll take a hit on the first file in each new path but save the overhead
        # of checking on each subsequent one. This assumes that most objects will
        # have multiple nested objects.
        do()
    except FileNotFoundError:
        os.makedirs(directory, exist_ok=True)
        do()
    return time.time() - begin


class ExpansionPool:
    def __init__(self, *, logger: logging.Logger, pool_ratio: float = 0.8, pool_size: int = 0):
        assert logger, "logger is required"
        self.logger = logger
        self.work = list()

        # If `pool_*` are both falsy no pool will be used (i.e. - work is serialized).
        # If only `pool_size` is falsy, pool_size = os.cpu_count() * pool_ratio.
        # If `pool_size` is truthy it is used as-is and `pool_ratio` is ignored.

        self.pool_ratio = abs(pool_ratio or 1)  # Only used if `pool_size` is falsy.
        self.pool_size = abs(pool_size or int(os.cpu_count() * self.pool_ratio) or 1)

    def drain(self):
        begin = time.time()
        chunksize = 1 + int(len(self.work) / self.pool_size)

        if self.pool_size == 1:
            global work
            work = self.work
            results = [_write_file(i) for i in range(0, len(self.work))]

        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=self.pool_size, initializer=_initialize, initargs=(self.work,)
            ) as pool:
                futures = pool.map(_write_file, range(0, len(self.work)), chunksize=chunksize)
                results = [f for f in futures]

        pool = None

        self.elapsed = time.time() - begin

        self.work_time = sum(results)
        self.overhead = self.elapsed - self.work_time
