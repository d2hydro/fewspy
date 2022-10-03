# Fewspy

A Python API for the [Deltares FEWS PI REST Web Service](https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service).

Fewspy is build for speed; time-series requests are handled asynchronous, giving the results you need much faster.

---

**Documentation**: [https://d2hydro.github.io/fewspy](https://d2hydro.github.io/fewspy)

**Source Code**: [https://github.com/d2hydro/fewspy](https://github.com/d2hydro/fewspy)

---

## Installation

Fewspy can be installed with pip in any environment with the following Python-packages properly installed:

* requests
* nest-asyncio
* aiohttp
* pandas
* geopandas

In that activated environment you can add fewspy via pip by:
```
pip install fewspy
```
We recommend to build your environment using [Anaconda](https://www.anaconda.com/). You can build an environment ánd install fewspy by conda in one go using this <a href="https://github.com/d2hydro/fewspy/blob/main/envs/environment.yml" target="_blank">environment.yml</a> from the command-line:
```
conda env create -f environment.yml
```
## About

Fewspy is developed and maintained by [D2Hydro](https://d2hydro.nl/) and freely available under an Open Source <a href="https://github.com/d2hydro/fewspy/blob/main/LICENSE" target="_blank">MIT license</a>.