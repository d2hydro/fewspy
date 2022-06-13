# setup.py shim, only required because PEP 517 doesn't support
# editable installs (pip install -e .)
import setuptools

setuptools.setup()
