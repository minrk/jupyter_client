from concurrent.futures import Future, ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager
from functools import partial

import pytest
import zmq

from ..manager import KernelManager


def run_one():
    km = KernelManager(context=zmq.Context.instance())
    assert not km.context.closed
    a = km.context.socket(zmq.PUSH)
    b = km.context.socket(zmq.PULL)
    port = a.bind_to_random_port("tcp://127.0.0.1")
    b.connect("tcp://127.0.0.1:%i" % port)
    a.send(b"test")
    assert b.recv() == b"test"


@contextmanager
def parallel_thread(n):
    with ThreadPoolExecutor(max(n // 2, 1)) as pool:
        yield partial(pool.submit, run_one)


@contextmanager
def parallel_multiprocessing(n):
    with ProcessPoolExecutor(max(n // 2, 1)) as pool:
        yield partial(pool.submit, run_one)


def multiprocessing_nested_subfunc(sub_n, **kwargs):
    with ProcessPoolExecutor(sub_n) as pool:
        return pool.submit(run_one, **kwargs).result()


@contextmanager
def parallel_multiprocessing_nested(n):
    with ProcessPoolExecutor(max(n // 2, 1)) as pool:

        def f(**kwargs):
            return pool.submit(partial(multiprocessing_nested_subfunc, sub_n=2), **kwargs)

        yield f


@pytest.mark.parametrize("n", [1, 8, 16, 32, 64])
@pytest.mark.parametrize(
    "method", ["thread", "multiprocessing", "multiprocessing_nested"]
)
@pytest.mark.parametrize("instance", ["open", "closed", "clear"])
def test_spawn_context_exists(n, method, instance):
    # initialize zmq.Context.instance state:
    if instance == "open":
        # global context exists and is open
        ctx = zmq.Context.instance()
        assert not ctx.closed
    elif instance == "closed":
        # global context exists and is closed
        ctx = zmq.Context.instance()
        ctx.term()
    elif instance == "clear":
        # no global context
        zmq.Context._instance = None

    # submit n potentially concurrent runs of `run_one`
    futures = []
    context_func = globals()["parallel_" + method]
    with context_func(n) as submit:
        futures.append(submit())

    for f in futures:
        assert f.result(timeout=10) is None
