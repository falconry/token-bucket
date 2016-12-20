Fast Token Bucket Implementation for Python |Build Status| |codecov.io|
=======================================================================

The ``token-bucket`` package provides an optimized implementation of the
`token bucket algorithm <http://falconframework.org/index.html>`_ that
does not require the use of a timer to manage the bucket state.

Compared to other rate-limiting algorithms that use a simple counter,
the token bucket algorithm provides the following advantages:

* The thundering herd problem is avoided since bucket capacity is
  replenished gradually, rather than being immediately refilled at the
  beginning of each epoch as is common with simple fixed window
  counters.
* Burst duration can be explicitly controlled

Moving window algorithms are resitant to bursting, but at the cost of
additional processing and memory overhead vs. the token bucket
algorithm which uses a simple, fast counter per key. The latter approach
does allow for bursting, but only for a controlled duration.

.. |Build Status| image:: https://travis-ci.org/falconry/token-bucket.svg
   :target: https://travis-ci.org/falconry/token-bucket
.. |codecov.io| image:: https://codecov.io/gh/falconry/token-bucket/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/falconry/token-bucket
