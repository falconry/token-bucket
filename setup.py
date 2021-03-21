import imp
import io
from os import path

from setuptools import find_packages, setup

VERSION = imp.load_source('version', path.join('.', 'token_bucket', 'version.py'))
VERSION = VERSION.__version__


setup(
    name='token_bucket',
    version=VERSION,
    description='Very fast implementation of the token bucket algorithm.',
    long_description=io.open('README.rst', 'r', encoding='utf-8').read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='web http https cloud rate limiting token bucket throttling',
    author='kgriffs',
    url='https://github.com/falconry/token-bucket',
    license='Apache 2.0',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.5',
    install_requires=[],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)
