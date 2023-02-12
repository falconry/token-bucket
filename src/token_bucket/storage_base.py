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

import abc
from typing import Union

KeyType = Union[str, bytes]


class StorageBase(abc.ABC):
    @abc.abstractmethod
    def get_token_count(self, key: KeyType) -> float:
        """Query the current token count for the given bucket.

        Note that the bucket is not replenished first, so the count
        will be what it was the last time replenish() was called.

        Args:
            key: Name of the bucket to query.

        Returns:
            Number of tokens currently in the bucket (may be
            fractional).
        """

    @abc.abstractmethod
    def replenish(self, key: KeyType, rate: float, capacity: int) -> None:
        """Add tokens to a bucket per the given rate.

        Conceptually, tokens are added to the bucket at a rate of one
        every 1/rate seconds. To accomplish this without requiring an
        out-of-band timer, ``replenish()`` simply calculates the number
        of tokens that should have been added since the last time the
        bucket was replenished.

        Args:
            key: Name of the bucket to replenish.
            rate: Number of tokens per second to add to the
                bucket. Over time, the number of tokens that can be
                consumed is limited by this rate.
            capacity: Maximum number of tokens that the bucket
                can hold. Once the bucket if full, additional tokens
                are discarded.
        """

    @abc.abstractmethod
    def consume(self, key: KeyType, num_tokens: int) -> bool:
        """Attempt to take one or more tokens from a bucket.

        Args:
            key: Name of the bucket to replenish.
            num_tokens: Number of tokens to try to consume from
                the bucket. If the bucket contains fewer than the
                requested number, no tokens are removed (i.e., it's all
                or nothing).

        Returns:
            True if the requested number of tokens were removed
            from the bucket (conforming), otherwise False (non-
            conforming).
        """
