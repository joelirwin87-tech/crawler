"""Compatibility shim exposing setuptools._distutils as distutils for Python 3.12+."""
from __future__ import annotations

from setuptools._distutils import *  # noqa: F401,F403
from setuptools._distutils import __all__  # type: ignore[attr-defined]
from setuptools._distutils import __file__  # type: ignore[attr-defined]
from setuptools._distutils import __path__  # type: ignore[attr-defined]
