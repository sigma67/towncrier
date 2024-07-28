# Copyright (c) Amber Brown, 2015
# See LICENSE for details.

"""
Responsible for getting the version and name from a project.
"""

from __future__ import annotations

import contextlib
import importlib.metadata as importlib_metadata
import sys

from importlib import import_module
from importlib.metadata import version as metadata_version
from types import ModuleType


if sys.version_info >= (3, 10):
    from importlib.metadata import packages_distributions
else:
    from importlib_metadata import packages_distributions  # type: ignore


def _get_package(package_dir: str, package: str) -> ModuleType:
    try:
        module = import_module(package)
    except ImportError:
        # Package is not already available / installed.
        # Force importing it based on the source files.
        sys.path.insert(0, package_dir)

        try:
            module = import_module(package)
        except ImportError as e:
            err = f"tried to import {package}, but ran into this error: {e}"
            # NOTE: this might be redirected via "towncrier --draft > …".
            print(f"ERROR: {err}")
            raise
        finally:
            sys.path.pop(0)

    return module


def _get_metadata_version(package: str) -> str | None:
    """
    Try to get the version from the package metadata.
    """
    distributions = packages_distributions()
    distribution_names = distributions.get(package)
    if not distribution_names or len(distribution_names) != 1:
        # We can only determine the version if there is exactly one matching distribution.
        return None
    return metadata_version(distribution_names[0])


def get_version(package_dir: str, package: str) -> str:
    """
    Get the version of a package.

    Try to extract the version from the distribution version metadata that matches
    `package`, then fall back to looking for the package in `package_dir`.
    """
    version: str

    # First try to get the version from the package metadata.
    if version := _get_metadata_version(package):
        return version

    # When no version if found, fall back to looking for the package in `package_dir`.
    module = _get_package(package_dir, package)
    version = getattr(module, "__version__", None)
    if not version:
        try:
            version = importlib_metadata.version(package)
        except importlib_metadata.PackageNotFoundError:
            raise Exception(
                f"No __version__ or metadata version info for the '{package}' package."
            )

    if isinstance(version, str):
        return version.strip()

    if isinstance(version, tuple):
        return ".".join(map(str, version)).strip()

    # Try duck-typing as an Incremental version.
    if hasattr(version, "base"):
        try:
            version = str(version.base()).strip()
            # Incremental uses `X.Y.rcN`.
            # Standardize on importlib (and PEP440) use of `X.YrcN`:
            return version.replace(".rc", "rc")  # type: ignore
        except TypeError:
            pass

    raise Exception(
        "Version must be a string, tuple, or an Incremental Version."
        " If you can't provide that, use the --version argument and specify one."
    )


def get_project_name(package_dir: str, package: str) -> str:
    module = _get_package(package_dir, package)
    version = getattr(module, "__version__", None)
    # Incremental has support for package names, try duck-typing it.
    with contextlib.suppress(AttributeError):
        return str(version.package)  # type: ignore

    return package.title()
