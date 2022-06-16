# Contribute

In the remainder of this manual we assume you:

* have your own [GitHub account](https://github.com/join)
* work with [GitHub Desktop](https://desktop.github.com) or Git
* can work with [GeoPandas](https://geopandas.org) and [Pytest](https://www.pytest.org/)

Code-contributions can enter the main branch if:

1. they are provided with docstring documentation
2. are passing Flakes tests an Black styling
3. are covered Pytest

## Installation for development

To setup your development environment follow the instructions at [Installation for development](installation.md#installation-for-development)

## Small contributions

For small contributions we propose the following workflow:

1. Fork and clone and install a copy
2. Add and test new code
3. Commit your copy and request a merge

The remainder of this guide explains how to do it.

### Fork repo
Fork the respository to your own GitHub account:

1. Click `fork` in the upper-right of the rository.
2. Select your own github account

The repository is now available on your own github account. 

### Clone repo
Now clone your fork to your local drive. We do this with [GitHub Desktop](https://desktop.github.com). After [installation and authentication](https://docs.github.com/en/desktop/installing-and-configuring-github-desktop/overview/getting-started-with-github-desktop)
you can get a local copy by:

1. `Add` and `Clone repository...` in the top-left corner
2. Find your fork and clone it to an empty directory on your local drive
3. Press  clone`

![](images/clone.gif "Clone repository")

Verify if the repository is on your local drive. 

### Install copy
Install the module in the activated `validatietool` environment in develop-mode:

```
pip install -e .
```

__Now you're good to go!__

### Improve code
Make any code-contribution you deem necessary. Please don't forget to document your code with docstrings so they are documented.

### Test code
In the test-folder you add a test. A test-function starts with `test_`. In within the test-function you confirm if your new functionity is correct with `assert = True`. In this case

Within your activated environment you can test your function with pytest:

```
pytest --cov-report term-missing --cov=src tests/
```

As your function is correct, the test should not fail. You can confirm all lines of your new code are tested:

### Contribute
Now you can contribute by:
1. Committing your code in your own repository
2. Request a merge of your branch into the main branch of fewspy

## Large contributions
For significant contributions we are happy to consider adding you to the contributors of our repository!