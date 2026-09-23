# AGENTS.md

## Project

Fewspy is a Python client for the Delft-FEWS PI REST Web Service.

Keep the library focused on providing a small, predictable Python interface to FEWS. Avoid adding application-specific logic that belongs in downstream projects.

## Development

* Follow the existing project structure, API patterns, naming and typing conventions.
* Always place imports at the top of the file, after module comments and docstrings, following [PEP 8: Imports](https://peps.python.org/pep-0008/#imports). Group standard library, third-party, and local imports separately, with a blank line between groups. Resolve circular dependencies through module organization rather than imports inside functions or methods.
* Prefer simple, explicit implementations over additional abstractions.
* Preserve backwards compatibility of the public API unless a breaking change is explicitly requested.
* Keep FEWS terminology and semantics intact; do not silently reinterpret FEWS concepts in the Python API.
* Preserve FEWS time-series metadata required to distinguish series. Do not assume `locationId` + `parameterId` uniquely identifies a FEWS time series.
* Keep asynchronous time-series retrieval asynchronous and avoid unnecessary sequential requests.
* Do not introduce new dependencies unless they provide a clear benefit that cannot reasonably be achieved with existing dependencies.

## Changes

For code changes:

* Add or update tests for changed behaviour.
* Test edge cases relevant to FEWS responses and metadata.
* Keep changes scoped to the requested functionality; avoid unrelated refactoring.
* Update documentation when the public API or user-visible behaviour changes.

Use the repository configuration as the source of truth for environments, dependencies, formatting, linting and test commands.
