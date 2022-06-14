# fewspy
A Python API for the Deltares FEWS PI REST Web Service

## Install

1. Make sure you have all requirements in [environment.yml](envs/environment.yml)  installed in a Anaconda environment:
```
conda env create -f environment.yml
```
2. Click on download button in the GitHub repository and download the source code to archive
3. Unzip the code
4. `cd` into the main project directory (e.g. `fewspy-master`)
5. Run: `pip install .` from that directory

## Install for development

1. Make sure you have the fewspy development environment installed, using the [environment_dev.yml](envs/environment_dev.yml). By e.g. Anaconda:
```
conda env create -f environment_dev.yml
```
2. Make sure you have git [Git](https://gitforwindows.org/) installed.
3. Clone the *fewspy*, e.g. via GIT:
```
git clone https://github.com/d2hydro/fewspy.git
```

4. Now `cd` to the clone on your disk and install in dev-mode (so with **-e**):

```
cd fewspy
pip install -e .
```