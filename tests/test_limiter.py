import functools
import time
import uuid

import pytest

import token_bucket


@pytest.mark.parametrize(
    'rate,capacity',
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
def test_general_functionality(rate, capacity):
    key = 'key'
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    assert storage.get_token_count(key) == 0

    consume_one = functools.partial(limiter.consume, key)

    # NOTE(kgriffs) Trigger creation of the bucket and then
    #   sleep to ensure it is at full capacity before testing it.
    consume_one()
    time.sleep(float(capacity) / rate)

    # NOTE(kgriffs): This works because we can consume at a much
    #   higher rate relative to the replenishment rate, such that we
    #   easily consume the total capacity before a single token can
    #   be replenished.
    def consume_all():
        for i in range(capacity + 3):
            conforming = consume_one()

            # NOTE(kgriffs): One past the end should be non-conforming,
            #   but sometimes an extra token or two can be generated, so
            #   only check a couple past the end for non-conforming.
            if i < capacity:
                assert conforming
            elif i > capacity + 1:
                assert not conforming

    # Check non-conforming after consuming all of the tokens
    consume_all()

    # Let the bucket replenish 1 token
    time.sleep(1.0 / rate)
    assert consume_one()

    # NOTE(kgriffs): Occasionally enough time will have elapsed to
    #   cause an additional token to be generated. Clear that one
    #   out if it is there.
    consume_one()

    assert storage.get_token_count(key) < 1.0

    # NOTE(kgriffs): Let the bucket replenish all the tokens; do this
    #   twice to verify that the bucket is limited to capacity.
    for __ in range(2):
        time.sleep(float(capacity) / rate)
        storage.replenish(key, rate, capacity)
        assert int(storage.get_token_count(key)) == capacity

    consume_all()


@pytest.mark.parametrize('capacity', [1, 2, 4, 10])
def test_consume_multiple_tokens_at_a_time(capacity):
    rate = 100
    num_tokens = capacity
    key = 'key'
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
        time.sleep(1.0 / rate * num_tokens)


def test_different_keys():
    rate = 10
    capacity = 10

    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate, capacity, storage)

    keys = [
        uuid.uuid4().bytes,
        '3084"5tj jafsb: f',
        b'77752098',
        'whiz:bang',
        b'x',
    ]

    # The last two should be non-conforming
    for i in range(capacity + 2):
        for k in keys:
            conforming = limiter.consume(k)

            if i < capacity:
                assert conforming
            else:
                assert not conforming


def test_input_validation_storage_type():
    class DoesNotInheritFromStorageBase(object):
        pass

    with pytest.raises(TypeError):
        token_bucket.Limiter(1, 1, DoesNotInheritFromStorageBase())


@pytest.mark.parametrize(
    'rate,capacity,etype',
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
        ('x', 'y', TypeError),
        (
            'x',
            -1,
            (ValueError, TypeError),
        ),  # Params could be checked in any order
        (-1, 'y', (ValueError, TypeError)),  # ^^^
        ('x', 1, TypeError),
        (1, 'y', TypeError),
        ('x', None, TypeError),
        (None, 'y', TypeError),
        (None, None, TypeError),
        (None, 1, TypeError),
        (1, None, TypeError),
    ],
)
def test_input_validation_rate_and_capacity(rate, capacity, etype):
    with pytest.raises(etype):
        token_bucket.Limiter(rate, capacity, token_bucket.MemoryStorage())


@pytest.mark.parametrize(
    'key,num_tokens,etype',
    [
        ('', 1, ValueError),
        ('', 0, ValueError),
        ('x', 0, ValueError),
        ('x', -1, ValueError),
        ('x', -2, ValueError),
        (
            -1,
            None,
            (ValueError, TypeError),
        ),  # Params could be checked in any order
        (None, -1, (ValueError, TypeError)),  # ^^^
        (None, 1, TypeError),
        (1, None, TypeError),
    ],
)
def test_input_validation_on_consume(key, num_tokens, etype):
    limiter = token_bucket.Limiter(1, 1, token_bucket.MemoryStorage())
    with pytest.raises(etype):
        limiter.consume(key, num_tokens)
