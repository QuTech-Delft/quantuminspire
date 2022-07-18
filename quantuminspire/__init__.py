"""quantuminspire.

SDK for the Quantum Inspire platform.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    pass
