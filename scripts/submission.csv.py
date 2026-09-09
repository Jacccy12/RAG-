#!/usr/bin/env python3
"""Compatibility wrapper for optimize_submission_csv.py."""

from __future__ import annotations

import runpy
from pathlib import Path


runpy.run_path(str(Path(__file__).with_name("optimize_submission_csv.py")), run_name="__main__")
