import random
import threading
import time
import uuid

import pytest

import token_bucket


def _run_threaded(func, num_threads):
    threads = [threading.Thread(target=func) for __ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


# NOTE(kgriffs): Don't try to remove more tokens than could ever
#   be available according to the bucket capacity.
@pytest.mark.parametrize(
    "rate,capacity,max_tokens_to_consume",
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
def test_negative_count(rate, capacity, max_tokens_to_consume):
    # NOTE(kgriffs): Usually there will be a much larger number of
    #   keys in a production system, but keep to just five to increase
    #   the likelihood of collisions.
    keys = [uuid.uuid4().bytes for __ in range(5)]
    num_threads = 100
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    token_counts = []

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


def test_replenishment():
    capacity = 100
    rate = 100
    num_threads = 4
    trials = 100

    storage = token_bucket.MemoryStorage()

    def loop():
        for i in range(trials):
            key = str(i)

            for __ in range(int(capacity / num_threads)):
                storage.replenish(key, rate, capacity)
                time.sleep(1.0 / rate)

    _run_threaded(loop, num_threads)

    # NOTE(kgriffs): Ensure that a race condition did not result in
    #   not all the tokens being replenished
    for i in range(trials):
        key = str(i)
        assert storage.get_token_count(key) == capacity


def test_conforming_ratio():
    rate = 100
    capacity = 10
    key = "key"
    target_ratio = 0.5
    ratio_max = 0.62
    num_threads = 4

    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    # NOTE(kgriffs): Rather than using a lock to protect some counters,
    #   rely on the GIL and count things up after the fact.
    conforming_states = []

    # NOTE(kgriffs): Start with an empty bucket
    while limiter.consume(key):
        pass

    def loop():
        # NOTE(kgriffs): Run for 10 seconds
        for __ in range(int(rate * 10 / target_ratio / num_threads)):
            conforming_states.append(limiter.consume(key))

            # NOTE(kgriffs): Only generate some of the tokens needed, so
            #   that some requests will end up being non-conforming.
            time.sleep(1.0 / rate * target_ratio * num_threads)

    _run_threaded(loop, num_threads)

    total_conforming = 0
    for c in conforming_states:
        if c:
            total_conforming += 1

    actual_ratio = float(total_conforming) / len(conforming_states)

    # NOTE(kgriffs): We don't expect to be super precise due to
    #   the inprecision of time.sleep() and also having to take into
    #   account execution time of the other instructions in the
    #   loop. We do expect a few more conforming states vs. non-
    #   conforming since the sleep time + overall execution time
    #   makes the threads run a little behind the replenishment rate.
    assert target_ratio < actual_ratio < ratio_max
