#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Forward runtime resource generation to the separately maintained compiler."""
import subprocess
import sys
from compiler_location import compiler_root
raise SystemExit(subprocess.run([sys.executable, compiler_root() / "scripts/runtime_sources.py",
                                *sys.argv[1:]]).returncode)
