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
import time


class AbstractStorage(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_token_count(self, key):
        """Query the current token count for the given bucket.

        Note that the bucket is not replenished first, so the count
        will be what it was the last time replenish() was called.

        Args:
            key (str): Name of the bucket to query.

        Returns:
            float: Number of tokens currently in the bucket (may be
            fractional).
        """

    @abc.abstractmethod
    def replenish(self, key, rate, capacity):
        """Add tokens to a bucket per the given rate.

        Conceptually, tokens are added to the bucket at a rate of one
        every 1/rate seconds. To accomplish this without requiring an
        out-of-band timer, ``replenish()`` simply calculates the number
        of tokens that should have been added since the last time the
        bucket was replenished.

        Args:
            key (str): Name of the bucket to replenish.
            rate (float): Number of tokens per second to add to the
                bucket. Over time, the number of tokens that can be
                consumed is limited by this rate.
            capacity (int): Maximum number of tokens that the bucket
                can hold. Once the bucket if full, additional tokens
                are discarded.
        """

    @abc.abstractmethod
    def consume(self, key, num_tokens):
        """Attempt to take one or more tokens from a bucket.

        Args:
            key (str): Name of the bucket to replenish.
            num_tokens (int): Number of tokens to try to consume from
                the bucket. If the bucket contains fewer than the
                requested number, no tokens are removed (i.e., it's all
                or nothing).

        Returns:
            bool: True if the requested number of tokens were removed
            from the bucket (conforming), otherwise False (non-
            conforming).
        """


class StorageBase(AbstractStorage):
    __metaclass__ = abc.ABCMeta

    # any object that implements __getitem__, __setitem__
    # (and should raise KeyError from __getitem__ if key not found)
    bucket_provider_cls = dict

    def __init__(self):
        self._buckets = self.bucket_provider_cls()

    def get_token_count(self, key):
        """Query the current token count for the given bucket.

        Note that the bucket is not replenished first, so the count
        will be what it was the last time replenish() was called.

        Args:
            key (str): Name of the bucket to query.

        Returns:
            float: Number of tokens currently in the bucket (may be
            fractional).
        """
        try:
            return self._buckets[key][0]
        except KeyError:
            pass

        return 0

    def replenish(self, key, rate, capacity):
        """Add tokens to a bucket per the given rate.

        This method is exposed for use by the token_bucket.Limiter
        class.
        """

        try:
            # NOTE(kgriffs): Correctness of this algorithm assumes
            #   that the calculation of the current time is performed
            #   in the same order as the updates based on that
            #   timestamp, across all threads. If an older "now"
            #   completes before a newer "now", the lower token
            #   count will overwrite the newer, effectively reducing
            #   the bucket's capacity temporarily, by a minor amount.
            #
            #   While a lock could be used to fix this race condition,
            #   one isn't used here for the following reasons:
            #
            #       1. The condition above will rarely occur, since
            #          the window of opportunity is quite small and
            #          even so requires many threads contending for a
            #          relatively small number of bucket keys.
            #       2. When the condition does occur, the difference
            #          in timestamps will be quite small, resulting in
            #          a negligible loss in tokens.
            #       3. Depending on the order in which instructions
            #          are interleaved between threads, the condition
            #          can be detected and mitigated by comparing
            #          timestamps. This mitigation is implemented below,
            #          and serves to further minimize the effect of this
            #          race condition to negligible levels.
            #       4. While locking introduces only a small amount of
            #          overhead (less than a microsecond), there's no
            #          reason to waste those CPU cycles in light of the
            #          points above.
            #       5. If a lock were used, it would only be held for
            #          a microsecond or less. We are unlikely to see
            #          much contention for the lock during such a short
            #          time window, but we might as well remove the
            #          possibility in light of the points above.

            tokens_in_bucket, last_replenished_at = self._buckets[key]
        except KeyError:
            self._buckets[key] = (capacity, time.time())
        else:
            now = time.time()

            # NOTE(kgriffs): This will detect many, but not all,
            #   manifestations of the race condition. If a later
            #   timestamp was already used to update the bucket, don't
            #   regress by setting the token count to a smaller number.
            if now < last_replenished_at:  # pragma: no cover
                return

            self._buckets[key] = (
                # Limit to capacity
                min(
                    capacity,

                    # NOTE(kgriffs): The new value is the current number
                    #   of tokens in the bucket plus the number of
                    #   tokens generated since last time. Fractional
                    #   tokens are permitted in order to improve
                    #   accuracy (now is a float, and rate may be also).
                    tokens_in_bucket + (rate * (now - last_replenished_at))
                ),

                # Update the timestamp for use next time
                now
            )

    def consume(self, key, num_tokens):
        """Attempt to take one or more tokens from a bucket.

        This method is exposed for use by the token_bucket.Limiter
        class.
        """

        # NOTE(kgriffs): Assume that the key will be present, since
        #   replenish() will always be called before consume().
        tokens_in_bucket, timestamp = self._buckets[key]
        if tokens_in_bucket < num_tokens:
            return False

        # NOTE(kgriffs): In a multi-threaded application, it is
        #   possible for two threads to interleave such that they
        #   both pass the check above, while in reality if executed
        #   linearly, the second thread would not pass the check
        #   since the first thread was able to consume the remaining
        #   tokens in the bucket.
        #
        #   When this race condition occurs, the count in the bucket
        #   will go negative, effectively resulting in a slight
        #   reduction in capacity.
        #
        #   While a lock could be used to fix this race condition,
        #   one isn't used here for the following reasons:
        #
        #       1. The condition above will rarely occur, since
        #          the window of opportunity is quite small.
        #       2. When the condition does occur, the tokens will
        #          usually be quickly replenished since the rate tends
        #          to be much larger relative to the number of tokens
        #          that are consumed by any one request, and due to (1)
        #          the condition is very rarely likely to happen
        #          multiple times in a row.
        #       3. In the case of bursting across a large number of
        #          threads, the likelihood for this race condition
        #          will increase. Even so, the burst will be quickly
        #          negated as requests become non-conforming, allowing
        #          the bucket to be replenished.
        #       4. While locking introduces only a small amount of
        #          overhead (less than a microsecond), there's no
        #          reason to waste those CPU cycles in light of the
        #          points above.
        #       5. If a lock were used, it would only be held for
        #          less than a microsecond. We are unlikely to see
        #          much contention for the lock during such a short
        #          time window, but we might as well remove the
        #          possibility given the points above.

        self._buckets[key] = (tokens_in_bucket - num_tokens, timestamp)
        return True
