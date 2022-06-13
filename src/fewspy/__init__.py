from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("fewspy")
except PackageNotFoundError:
    # package is not installed
    pass