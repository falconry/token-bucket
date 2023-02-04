# Copyright 2016 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .storage_base import StorageBase


class Limiter(object):
    """Limits demand for a finite resource via keyed token buckets.

    A limiter manages a set of token buckets that have an identical
    rate, capacity, and storage backend. Each bucket is referenced
    by a key, allowing for the independent tracking and limiting
    of multiple consumers of a resource.

    Args:
        rate (float): Number of tokens per second to add to the
            bucket. Over time, the number of tokens that can be
            consumed is limited by this rate. Each token represents
            some percentage of a finite resource that may be
            utilized by a consumer.
        capacity (int): Maximum number of tokens that the bucket
            can hold. Once the bucket is full, additional tokens
            are discarded.

            The bucket capacity has a direct impact on burst duration.
            Let M be the maximum possible token request rate, r the
            token generation rate (tokens/sec), and b the bucket
            capacity.

            If r < M the maximum burst duration, in seconds, is:

                T = b / (M - r)

            Otherwise, if r >= M, it is not possible to exceed the
            replenishment rate, and therefore a consumer can burst
            at full speed indefinitely.

            The maximum number of tokens that any one burst may
            consume is:

                T * M

            See also: https://en.wikipedia.org/wiki/Token_bucket#Burst_size
        storage (token_bucket.StorageBase): A storage engine to use for
            persisting the token bucket data. The following engines are
            available out of the box:

                token_bucket.MemoryStorage
    """

    __slots__ = (
        "_rate",
        "_capacity",
        "_storage",
    )

    def __init__(self, rate, capacity, storage):
        if not isinstance(rate, (float, int)):
            raise TypeError("rate must be an int or float")

        if rate <= 0:
            raise ValueError("rate must be > 0")

        if not isinstance(capacity, int):
            raise TypeError("capacity must be an int")

        if capacity < 1:
            raise ValueError("capacity must be >= 1")

        if not isinstance(storage, StorageBase):
            raise TypeError("storage must be a subclass of StorageBase")

        self._rate = rate
        self._capacity = capacity
        self._storage = storage

    def consume(self, key, num_tokens=1):
        """Attempt to take one or more tokens from a bucket.

        If the specified token bucket does not yet exist, it will be
        created and initialized to full capacity before proceeding.

        Args:
            key (bytes): A string or bytes object that specifies the
                token bucket to consume from. If a global limit is
                desired for all consumers, the same key may be used
                for every call to consume(). Otherwise, a key based on
                consumer identity may be used to segregate limits.
        Keyword Args:
            num_tokens (int): The number of tokens to attempt to
                consume, defaulting to 1 if not specified. It may
                be appropriate to ask for more than one token according
                to the proportion of the resource that a given request
                will use, relative to other requests for the same
                resource.

        Returns:
            bool: True if the requested number of tokens were removed
            from the bucket (conforming), otherwise False (non-
            conforming). The entire number of tokens requested must
            be available in the bucket to be conforming. Otherwise,
            no tokens will be removed (it's all or nothing).
        """

        if not key:
            if key is None:
                raise TypeError("key may not be None")

            raise ValueError("key must not be a non-empty string or bytestring")

        if num_tokens is None:
            raise TypeError("num_tokens may not be None")

        if num_tokens < 1:
            raise ValueError("num_tokens must be >= 1")

        self._storage.replenish(key, self._rate, self._capacity)
        return self._storage.consume(key, num_tokens)
