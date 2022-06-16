from importlib.metadata import version, PackageNotFoundError

from .api import Api

try:
    __version__ = version("fewspy")
except PackageNotFoundError:
    # package is not installed
    pass