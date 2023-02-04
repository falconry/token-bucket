import datetime
import os
import random
import threading
import time
import uuid
from collections import Counter
from typing import Any, Callable, List

import pytest
from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory

import token_bucket


def patched_freeze_time():
    f = freeze_time()
    f.ignore = tuple(set(f.ignore) - {"threading"})  # pyright: ignore
    return f


@pytest.fixture
def frozen_time():
    with patched_freeze_time() as ft:
        yield ft


def _run_threaded(func: Callable[..., Any], num_threads: int):
    threads = [threading.Thread(target=func) for __ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


# NOTE(kgriffs): Don't try to remove more tokens than could ever
#   be available according to the bucket capacity.
# Test this only in the CI. It is incredibly slow and so
#   unlikely that you may never see it.
@pytest.mark.skipif(os.getenv("CI") != "true", reason="slow test")
@pytest.mark.parametrize(
    ("rate", "capacity", "max_tokens_to_consume"),
    [
        (10, 1, 1),
        (100, 1, 1),
        (100, 2, 2),
        (10, 10, 1),
        (10, 10, 2),
        (100, 10, 1),
        (100, 10, 10),
        (100, 100, 5),
        (100, 100, 10),
        (1000, 10, 1),
        (1000, 10, 5),
        (1000, 10, 10),
    ],
)
def test_negative_count(
    rate: int,
    capacity: int,
    max_tokens_to_consume: int,
):
    # NOTE(kgriffs): Usually there will be a much larger number of
    #   keys in a production system, but keep to just five to increase
    #   the likelihood of collisions.
    keys = [uuid.uuid4().bytes for __ in range(5)]
    num_threads = 100
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    token_counts: List[float] = []

    def loop():
        for __ in range(1000):
            key = random.choice(keys)
            num_tokens = random.randint(1, max_tokens_to_consume)

            # NOTE(kgriffs): The race condition is only possible when
            #   conforming.
            if limiter.consume(key, num_tokens):
                token_counts.append(storage.get_token_count(key))

            # NOTE(kgriffs): Sleep for only a short time to increase the
            #   likelihood for contention, while keeping to something
            #   more realistic than a no-op (max of 1 ms)
            time.sleep(random.random() / 1000)

    _run_threaded(loop, num_threads)

    negative_counts = [c for c in token_counts if c < 0]
    if negative_counts:
        # NOTE(kgriffs): Negatives should be rare
        ratio_of_negatives = float(len(negative_counts)) / len(token_counts)
        assert ratio_of_negatives < 0.008

        # NOTE(kgriffs): Shouldn't ever have more than a few extra tokens
        #   removed. Allow for 2-3 collisions at max token removal
        assert (max_tokens_to_consume * -2) < min(negative_counts)


def test_burst_replenishment(frozen_time: FrozenDateTimeFactory):
    capacity = 100
    rate = 100
    num_threads = 4
    trials = 100

    storage = token_bucket.MemoryStorage()

    def consume():
        for i in range(trials):
            key = bytes(i)
            storage.replenish(key, rate, capacity)

    for __ in range(capacity // num_threads):
        _run_threaded(consume, num_threads)
        frozen_time.tick(1.0 / rate)

    # NOTE(kgriffs): Ensure that a race condition did not result in
    #   not all the tokens being replenished
    for i in range(trials):
        key = bytes(i)
        assert storage.get_token_count(key) == capacity


def test_burst_conforming_ratio(frozen_time: FrozenDateTimeFactory):
    rate = 100
    capacity = 10
    key = b"key"
    target_ratio = 0.5
    max_ratio = 0.55
    num_threads = 4

    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    # NOTE(kgriffs): Rather than using a lock to protect some counters,
    #   rely on the GIL and count things up after the fact.
    conforming_states: Counter[bool] = Counter()

    # NOTE(kgriffs): Start with an empty bucket
    while limiter.consume(key):
        pass

    def consume():
        conforming_states.update([limiter.consume(key)])

    for __ in range(int(rate * 10 / target_ratio / num_threads)):
        # NOTE(kgriffs): Only generate some of the tokens needed, so
        #   that some requests will end up being non-conforming.
        sleep_in_seconds = 1.0 / rate * target_ratio * num_threads
        frozen_time.tick(delta=datetime.timedelta(seconds=sleep_in_seconds))

        _run_threaded(consume, num_threads)

    actual_ratio = conforming_states[True] / len(list(conforming_states.elements()))

    # NOTE: With a frozen time we should hit exactly. However, due to a tiny gap between
    #   replenish, frozen_time.tick and consume, it is possible that we have a little bit
    #   more than expected. You may see this only with PyPy.
    assert target_ratio <= actual_ratio < max_ratio
