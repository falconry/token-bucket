import datetime
import functools
from typing import Type
import uuid

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
import pytest

import token_bucket


@pytest.fixture
def frozen_time():
    with freeze_time() as ft:
        yield ft


@pytest.mark.parametrize(
    ("rate", "capacity"),
    [
        (0.3, 1),
        (1, 1),
        (2.5, 1),  # Fractional rates are valid
        (10, 100),  # Long recovery time after bursting
        (10, 10),
        (10, 1),  # Disallow bursting
        (100, 100),
        (100, 10),
        (100, 1),  # Disallow bursting
    ],
)
def test_general_functionality(
    rate: int, capacity: int, frozen_time: FrozenDateTimeFactory
):
    key = "key"
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    assert storage.get_token_count(key) == 0

    consume_one = functools.partial(limiter.consume, key)

    # NOTE(kgriffs) Trigger creation of the bucket.
    storage.replenish(key, rate, capacity)
    assert storage.get_token_count(key) == capacity

    def consume_all():
        conforming = limiter.consume(key, num_tokens=capacity)
        assert conforming
        for _ in range(3):
            conforming = consume_one()
            assert not conforming

    # Check non-conforming after consuming all of the tokens
    consume_all()

    # Let the bucket replenish 1 token
    frozen_time.tick(delta=datetime.timedelta(seconds=(1.5 / rate)))
    assert consume_one()
    assert storage.get_token_count(key) < 1.0

    # NOTE(kgriffs): Let the bucket replenish all the tokens; do this
    #   twice to verify that the bucket is limited to capacity.
    for __ in range(2):
        frozen_time.tick(delta=datetime.timedelta(seconds=((capacity + 0.5) / rate)))
        storage.replenish(key, rate, capacity)
        assert int(storage.get_token_count(key)) == capacity

    consume_all()


@pytest.mark.parametrize("capacity", [1, 2, 4, 10])
def test_consume_multiple_tokens_at_a_time(
    capacity: int, frozen_time: FrozenDateTimeFactory
):
    rate = 100
    num_tokens = capacity
    key = "key"
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    assert not limiter.consume(key, num_tokens=capacity + 1)

    # NOTE(kgriffs): Should be able to conform indefinitely since we
    #   are matching the replenishment rate; verify for five seconds
    #   only.
    for __ in range(int(rate * 5 / num_tokens)):
        assert limiter.consume(key, num_tokens=num_tokens)
        assert storage.get_token_count(key) < 1.0

        # Sleep long enough to generate num_tokens
        frozen_time.tick(
            delta=datetime.timedelta(seconds=(1.0 / rate * (num_tokens + 0.1)))
        )


def test_different_keys():
    rate = 10
    capacity = 10

    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    keys = [
        uuid.uuid4().bytes,
        '3084"5tj jafsb: f',
        b"77752098",
        "whiz:bang",
        b"x",
    ]

    # The last two should be non-conforming
    for k in keys:
        assert limiter.consume(k, capacity)
        for _ in range(2):
            assert not limiter.consume(k)


@pytest.mark.parametrize(
    ("rate", "capacity", "etype"),
    [
        (0, 0, ValueError),
        (0, 1, ValueError),
        (1, 0, ValueError),
        (-1, -1, ValueError),
        (-1, 0, ValueError),
        (0, -1, ValueError),
        (-2, -2, ValueError),
        (-2, 0, ValueError),
        (0, -2, ValueError),
    ],
)
def test_input_validation_rate_and_capacity(
    rate: float, capacity: int, etype: Type[Exception]
):
    with pytest.raises(etype):
        token_bucket.Limiter(rate, capacity, token_bucket.MemoryStorage())


@pytest.mark.parametrize(
    ("key", "num_tokens", "etype"),
    [
        ("x", 0, ValueError),
        ("x", -1, ValueError),
        ("x", -2, ValueError),
    ],
)
def test_input_validation_on_consume(
    key: bytes, num_tokens: int, etype: Type[Exception]
):
    limiter = token_bucket.Limiter(1, 1, token_bucket.MemoryStorage())
    with pytest.raises(etype):
        limiter.consume(key, num_tokens)
