# fewspy
A Python API for the Deltares FEWS PI REST Web Service

## Install

1. Click on download button in the GitHub repository and download the source code to archive
2. Unzip the code
3. `cd` into the main project directory (e.g. `fewspy-master`)
4. Run: `pip install .` from that directory

## Install for development

1. Make sure you have the fewspy development environment installed, using the environment_dev.yml. By e.g. Anaconda:
2. Make sure you have git for [Windows](https://gitforwindows.org/) or [Linux](https://git-scm.com/) installed.

```
conda env create -f environment_dev.yml
```

2. Clone the *fewspy*, e.g. via GIT:
```
git clone https://github.com/d2hydro/fewspy.git
```

3. Now `cd` to the clone on your disk and install in dev-mode (so with **-e**):

```
cd fewspy
pip install -e .
```