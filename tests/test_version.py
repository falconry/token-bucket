import token_bucket


def test_version():
    version = token_bucket.__version__

    assert isinstance(version, str)

    numbers = version.split(".")
    assert len(numbers) == 3
    for n in numbers:
        # NOTE(kgriffs): Just check that these are ints by virtue
        # of the conversion not raising an error.
        int(n)
