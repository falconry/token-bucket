|Build Status| |PyPi| |codecov.io|

A Token Bucket Implementation for Python Web Apps
=================================================

The ``token-bucket`` package provides an implementation of the
`token bucket algorithm <https://en.wikipedia.org/wiki/Token_bucket>`_
suitable for use in web applications for shaping or policing request
rates. This implementation does not require the use of an independent
timer thread to manage the bucket state.

Compared to other rate-limiting algorithms that use a simple counter,
the token bucket algorithm provides the following advantages:

* The thundering herd problem is avoided since bucket capacity is
  replenished gradually, rather than being immediately refilled at the
  beginning of each epoch as is common with simple fixed window
  counters.
* Burst duration can be explicitly controlled.

Moving window algorithms are resistant to bursting, but at the cost of
additional processing and memory overhead vs. the token bucket
algorithm which uses a simple, fast counter per key. The latter approach
does allow for bursting, but only for a controlled duration.

.. |Build Status| image:: https://github.com/falconry/token-bucket/workflows/tests/badge.svg
   :target: https://github.com/falconry/token-bucket/actions?query=workflow%3A%22tests%22

.. |PyPi| image:: https://img.shields.io/pypi/v/token-bucket.svg
   :target: https://pypi.python.org/pypi/token-bucket

.. |codecov.io| image:: https://codecov.io/gh/falconry/token-bucket/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/falconry/token-bucket
