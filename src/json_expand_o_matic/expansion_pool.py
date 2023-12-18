"""
Use a ProcessPoolExecutor to save the data in parallel rather than serially.
"""

import logging
import multiprocessing as mp
import os
import time
from ctypes import POINTER, Structure, c_ubyte, cast, create_string_buffer, string_at
from enum import Enum
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)


class InitArgsType(Enum):
    ArrayOfTuples = "ArrayOfTuples"
    SharedMemoryArray = "SharedMemoryArray"


__initargsmode__ = InitArgsType.SharedMemoryArray
__unpackfunc__ = None
__work__ = None


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
    global __initargsmode__
    global __work__
    global __unpackfunc__

    __initargsmode__ = mode
    __work__ = data

    if __initargsmode__ == InitArgsType.SharedMemoryArray:
        __unpackfunc__ = lambda request: [  # noqa: E731
            string_at(element).decode("utf-8") for element in __work__[request]
        ]
    elif __initargsmode__ == InitArgsType.ArrayOfTuples:
        __unpackfunc__ = lambda request: __work__[request]  # noqa: E731


def _write_file(request):
    global __unpackfunc__

    begin = time.time()
    directory, filename, data, checksum_filename, checksum = __unpackfunc__(request)

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
    def __init__(
        self,
        *,
        logger: logging.Logger,
        pool_ratio: Optional[float] = None,
        pool_size: Optional[int] = None,
        pool_disable: Optional[bool] = False,
        pool_mode: Union[str, InitArgsType] = InitArgsType.SharedMemoryArray,
    ):
        assert logger, "logger is required"
        self.logger = logger
        self.work: list = list()

        self.init_style = InitArgsType(pool_mode)

        self._set_pool_size(pool_ratio, pool_size, pool_disable)

        if self.pool_size > 1:
            logger.info(f"PoolSize: [{self.pool_size}]. Mode [{self.init_style.value}].")
        else:
            logger.info(f"PoolSize: [{self.pool_size}].")

    def setup(self) -> Tuple["ExpansionPool", list]:
        return self, self.work

    def finalize(self):
        begin = time.time()

        if self.pool_size == 1:
            _initialize(InitArgsType.ArrayOfTuples, self.work)
            results = [_write_file(i) for i in range(0, len(self.work))]

        else:
            results = self._pooled_processing()

        self.elapsed = time.time() - begin

        self.work_time = sum(results)
        self.overhead = self.elapsed - self.work_time

    def _pooled_processing(self):
        if self.init_style == InitArgsType.SharedMemoryArray:
            data = self._prepare_shared_memory_array()
        elif self.init_style == InitArgsType.ArrayOfTuples:
            data = self.work

        chunksize = 1 + int(len(self.work) / self.pool_size)

        with mp.Pool(processes=self.pool_size, initializer=_initialize, initargs=(self.init_style, data)) as pool:
            futures = pool.map(_write_file, range(0, len(self.work)), chunksize=chunksize)
            results = [f for f in futures]
            return results

    def _prepare_shared_memory_array(self):
        value_list = [
            WorkTuple(
                *[
                    cast(create_string_buffer((component or "").encode("utf-8")), POINTER(c_ubyte))
                    for component in work_unit
                ]
            )
            for work_unit in self.work
        ]
        data = mp.Array(WorkTuple, value_list, lock=False)
        return data

    def _set_pool_size(self, pool_ratio, pool_size, pool_disable):
        if pool_disable:
            self.pool_size = 1
        elif pool_size:
            self.pool_size = abs(pool_size)
        elif pool_size == 0 and not pool_ratio:
            self.pool_size = os.cpu_count()
        elif pool_ratio:
            assert (
                pool_size is None
            ), f"Programmer error: pool_ratio [{pool_ratio}] cannot be used with pool_size [{pool_size}]."
            self.pool_size = abs(int(os.cpu_count() * pool_ratio))
        else:
            self.pool_size = 1
