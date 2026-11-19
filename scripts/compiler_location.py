# SPDX-License-Identifier: MIT OR Apache-2.0
"""Find the separately checked-out self-hosted compiler for development tools."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compiler_root():
    configured = os.environ.get("CORBOC_SOURCE_ROOT")
    path = Path(configured).expanduser().resolve() if configured else ROOT.parent / "corboc"
    if not (path / "package.toml").is_file() or not (path / "src/main.crb").is_file():
        raise RuntimeError(
            "The compiler is maintained in https://github.com/omework/corboc. "
            "Clone it beside this checkout or set CORBOC_SOURCE_ROOT."
        )
    return path
