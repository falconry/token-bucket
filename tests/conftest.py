import platform

from pytest import Config


def pytest_configure(config: Config):
    # When testing with PyPy and coverage, tests become incredible slow and
    # could break them. There are several issues reported with other plugins
    # too. So you should check carefully if PyPy support it.
    # https://github.com/pytest-dev/pytest-cov/issues/418
    # https://github.com/pytest-dev/pytest/issues/7675
    if platform.python_implementation() == "PyPy":
        cov = config.pluginmanager.get_plugin("_cov")

        # probably pytest_cov is not installed
        if cov:
            cov.options.no_cov = True

            if cov.cov_controller:
                cov.cov_controller.pause()
