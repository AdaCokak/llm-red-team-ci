"""Shared pytest environment configuration."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "JSII_RUNTIME_PACKAGE_CACHE_ROOT",
    str(PROJECT_ROOT / ".jsii-cache"),
)
