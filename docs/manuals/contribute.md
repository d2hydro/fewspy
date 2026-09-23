# Contribute

In the remainder of this manual we assume you:

* have your own [GitHub account](https://github.com/join)
* work with [GitHub Desktop](https://desktop.github.com) or Git
* can work with [GeoPandas](https://geopandas.org) and [Pytest](https://www.pytest.org/)

Code-contributions can enter the main branch if:

1. they are provided with docstring documentation
2. pass the Ruff lint and formatting pre-commit hooks
3. are covered Pytest

## Installation for development

To setup your development environment follow the instructions at [Installation for development](installation.md#installation-for-development)

Install the Pixi environment and enable the Git hooks once per clone:

```console
pixi install --locked
pixi run pre-commit install
```

Before completing a change, run `pixi run lint` to run pre-commit on all tracked
Python files and notebooks, then run the relevant tests (`pixi run tests` for
the full suite). Hooks can modify files; review their edits and rerun until they
pass. CI runs the same pre-commit command.

Ruff is adapted to fewspy's Python 3.10 minimum,
120-character lines, and tests' use of assertions and subprocesses. `PLC0415`
rejects imports inside functions and classes; `E402` checks import placement at
module level, and `I` checks ordering. Conditional module-level imports for Python
compatibility remain allowed. Narrow, commented `noqa` exceptions retain existing
request timeout/TLS behavior, XML parsing, read-only public mutable defaults,
legacy event-loop exception handling, and trusted pickle fixtures. These behaviors
are deliberately not changed as part of adopting linting.

## Package dependency validation

The dependency audit found that the previous metadata allowed Pydantic 1 even
though the code uses Pydantic 2 APIs (`field_validator`, `model_validate`), and
omitted the directly imported NumPy, Shapely and urllib3 packages. It also declared
Python 3.9 support despite using evaluated `X | None` annotations, which require
Python 3.10. The existing coverage job only tested the Pixi environment, not a
clean installation of the published package dependencies.

Clean-install validation also exposed an import failure on Python 3.10: the
`TimeStepDict` TypedDict was decorated as a dataclass. It is now a plain TypedDict
from `typing_extensions`, which Pydantic requires on Python versions below 3.12.
`typing-extensions` is therefore also declared directly (already a Pydantic
dependency).
The cache also used Python 3.11's `hashlib.file_digest`; incremental SHA-256
hashing preserves the same file hashes on Python 3.10.

The metadata declares Python 3.10–3.14 and Pydantic >=2, and explicitly lists
those direct dependencies. Runtime dependencies without version constraints have
not had their oldest compatible versions established.

`test-cov.yml` retains Pixi coverage and also installs `.[tests]` into a fresh
virtual environment on every supported Python version, runs `pip check`, and runs
the test suite outside the checkout so it imports the installed package. An extra
Python 3.10 job tests the Pydantic 2.0 minimum; this is
not a minimum-version test of the entire dependency graph. Some tests contact the
public FEWS service and therefore require network access and service availability.

The Pixi development/test environment uses Python 3.14 on Windows and Linux.
Run `pixi run tests` and `pixi run build` to test and build in that environment.
The package CI matrix retains Python 3.10–3.13 alongside Python 3.14.

Python 3.14 validation exposed a blocker in `nest-asyncio` 1.6.0: its patch breaks
asyncio task tracking, causing aiohttp requests to fail with "Timeout context
manager should be used inside a task". On Python 3.14, fewspy therefore uses
[`nest-asyncio2`](https://github.com/Chaoses-Ib/nest-asyncio2) >=1.7.2, which fixes
that compatibility issue while retaining nested event-loop support. Older Python
versions continue using `nest-asyncio`. Other existing Pixi dependency versions
are retained; compiled packages use Python 3.14 builds where required.

Dependabot checks the root Python package manifest and GitHub Actions weekly;
it does not manage Pixi. Its pull requests run the same PR tests without secrets;
the Codecov upload is skipped for Dependabot. Unconstrained dependencies may not
produce version-update PRs, and this configuration does not audit every resolved
transitive dependency for vulnerabilities. Repository-level Dependabot alerts and
security updates are managed separately in GitHub settings. See the
[supported manifests](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
and [Dependabot Actions restrictions](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-on-actions).

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
