# fewspy
A Python API for the Deltares FEWS PI REST Web Service

## Installation
1. Make sure you have git [Git](https://gitforwindows.org/) installed.
2. Make sure you have a copy of [Anaconda](https://www.anaconda.com/) or [Miniconda](https://veranostech.github.io/docs-korean-conda-docs/docs/build/html/miniconda.html) installed.
3. Clone the *fewspy*, e.g. via GIT:
```
git clone https://github.com/d2hydro/fewspy.git
```
Developers continue to [Install for development](#install-for-development).

For regular use continue below
### Install for Regular use
4. Make sure you have all requirements in [environment.yml](envs/environment.yml)  installed in a Anaconda environment:
```
conda env create -f environment.yml
```
5. Activate the environment in the Command Prompt (or Anaconda Prompt) by:
```
conda activate fewspy
```
6. Now navigate to the clone on your disk and install **fewspy** (so with **-e**):
```
cd path\to\fewspy
pip install .
```
<h3 id="install-for-development">Install for development</h3>

4. Make sure you have the fewspy development environment installed, using the [environment_dev.yml](envs/environment_dev.yml). By e.g. Anaconda:
```
conda env create -f environment_dev.yml
```
5. Activate the environment in the Command Prompt (or Anaconda Prompt) by:
```
conda activate fewspy
```
6. Now `cd` to the clone on your disk and install **fewspy** in dev-mode (so with **-e**):

```
cd path\to\fewspy
pip install -e .
```