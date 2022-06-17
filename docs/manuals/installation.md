# Installation

## Installation for regular use
Fewspy can be installed with pip in any environment with the following Python-packages properly installed:

* requests
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
<h2 id="installation-for-development">Installation for development</h2>
For development we recommend the following approach:

1. Make sure you have git [Git](https://gitforwindows.org/) installed.
2. Make sure you have a copy of [Anaconda](https://www.anaconda.com/) or [Miniconda](https://veranostech.github.io/docs-korean-conda-docs/docs/build/html/miniconda.html) installed.
3. Clone the **fewspy**, e.g. via GIT:

    ```
    git clone https://github.com/d2hydro/fewspy.git
    ```

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