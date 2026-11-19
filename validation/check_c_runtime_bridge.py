#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compatibility entry point; implementation is maintained in corboc."""
from pathlib import Path
import runpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compiler_location import compiler_root
runpy.run_path(str(compiler_root() / "validation" / Path(__file__).name), run_name="__main__")
