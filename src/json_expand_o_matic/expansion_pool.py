"""
Use a ProcessPoolExecutor to save the data in parallel rather than serially.
"""

import asyncio
import logging
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor
from ctypes import POINTER, Structure, c_ubyte, cast, create_string_buffer, string_at
from datetime import datetime
from enum import Enum
from typing import Tuple, Union

import aiofiles

logger = logging.getLogger(__name__)


class Modes(Enum):
    ArrayOfTuples = "ArrayOfTuples"
    SharedMemoryArray = "SharedMemoryArray"


__mode__ = Modes.SharedMemoryArray
__unpk__ = None
__work__ = None
__size__ = 0


class WorkTuple(Structure):
    _fields_ = [
        ("directory", POINTER(c_ubyte)),
        ("filename", POINTER(c_ubyte)),
        ("data", POINTER(c_ubyte)),
        ("checksum_filename", POINTER(c_ubyte)),
        ("checksum", POINTER(c_ubyte)),
    ]

    def __iter__(self):
        yield self.directory
        yield self.filename
        yield self.data
        yield self.checksum_filename
        yield self.checksum


def _initialize(mode, data):
    global __mode__
    global __work__
    global __unpk__
    global __size__

    __mode__ = mode
    __work__ = data
    __size__ = len(data)

    if __mode__ == Modes.SharedMemoryArray:
        __unpk__ = lambda request: [string_at(element).decode("utf-8") for element in __work__[request]]
    elif __mode__ == Modes.ArrayOfTuples:
        __unpk__ = lambda request: __work__[request]


def _write_file(request):
    global __unpk__

    begin = time.time()

    directory, filename, data, checksum_filename, checksum = __unpk__(request)

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


async def async_write_file(request: int):
    global __work__
    global __unpk__
    global __size__

    if request < 0 or request >= __size__:
        return 0.0

    begin = time.time()

    directory, filename, data, checksum_filename, checksum = __unpk__(request)

    async def do():
        async with aiofiles.open(f"{directory}/{filename}", "w") as f:
            await f.write(data)
        if checksum_filename and checksum:
            async with aiofiles.open(f"{directory}/{checksum_filename}", "w") as f:
                await f.write(checksum)

    try:
        # Assume that the path will already exist.
        # We'll take a hit on the first file in each new path but save the overhead
        # of checking on each subsequent one. This assumes that most objects will
        # have multiple nested objects.
        await do()
    except FileNotFoundError:
        os.makedirs(directory, exist_ok=True)
        await do()
    return time.time() - begin


async def write_concurrently(begin_idx: int, end_idx: int):
    tasks = []
    for idx in range(begin_idx, end_idx, 1):
        tasks.append(asyncio.create_task(async_write_file(idx)))
    results = await asyncio.gather(*tasks)
    return results


def run_batch_tasks(batch_idx: int, step: int):
    begin = batch_idx * step + 1
    end = begin + step

    results = [result for result in asyncio.run(write_concurrently(begin, end))]
    return results


class ExpansionPool:
    def __init__(
        self,
        *,
        logger: logging.Logger,
        pool_ratio: float = None,
        pool_size: int = None,
        pool_disable: bool = False,
        pool_mode: Union[str, Modes] = Modes.SharedMemoryArray,
    ):
        assert logger, "logger is required"
        self.logger = logger
        self.work = list()

        self.mode = Modes(pool_mode)

        if pool_disable:
            self.pool_size = 1
        elif pool_size:
            self.pool_size = abs(pool_size)
        elif pool_size == 0 and not pool_ratio:
            self.pool_size = os.cpu_count()
        elif pool_ratio:
            assert pool_size is None, "Programmer error."
            self.pool_size = abs(int(os.cpu_count() * self.pool_ratio))
        else:
            assert pool_size is None, "Programmer error."
            assert pool_ratio is None, "Programmer error."
            self.pool_size = 1

        if self.pool_size > 1:
            logger.info(f"PoolSize: [{self.pool_size}]. Mode [{pool_mode.value}].")
        else:
            logger.info(f"PoolSize: [{self.pool_size}].")

    def setup(self) -> Tuple["ExpansionPool", list]:
        return self, self.work

    def finalize(self):
        begin = time.time()

        if self.pool_size == 1:
            _initialize(Modes.ArrayOfTuples, self.work)
            results = [_write_file(i) for i in range(0, len(self.work))]

        else:
            print("Beginning")
            b = datetime.now()
            results = asyncio.run(self._pooled_processing())
            delta = datetime.now() - b
            print(delta)

        self.elapsed = time.time() - begin

        self.work_time = sum(results)
        self.overhead = self.elapsed - self.work_time

    async def _pooled_processing(self):
        if self.mode == Modes.SharedMemoryArray:
            data = self._prepare_shared_memory_array()
        elif self.mode == Modes.ArrayOfTuples:
            data = self.work

        chunksize = 1 + int(len(self.work) / self.pool_size)

        # with mp.Pool(processes=self.pool_size, initializer=_initialize, initargs=(self.mode, data)) as pool:
        #     futures = pool.map(_write_file, range(0, len(self.work)), chunksize=chunksize)
        #     results = [f for f in futures]
        #     return results

        # This is significantly slower than the approach above.
        # From https://scribe.rip/combining-multiprocessing-and-asyncio-in-python-for-performance-boosts-15496ffe96b
        # and related articles.
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(
            max_workers=self.pool_size, initializer=_initialize, initargs=(self.mode, data)
        ) as executor:
            tasks = [
                loop.run_in_executor(executor, run_batch_tasks, batch_idx, chunksize)
                for batch_idx in range(self.pool_size)
            ]

        results = [result for sub_list in await asyncio.gather(*tasks) for result in sub_list]

        return results

    def _prepare_shared_memory_array(self):
        value_list = [
            WorkTuple(
                *[cast(create_string_buffer(component.encode("utf-8")), POINTER(c_ubyte)) for component in work_unit]
            )
            for work_unit in self.work
        ]
        data = mp.Array(WorkTuple, value_list, lock=False)
        return data
