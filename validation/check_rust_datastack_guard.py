#!/usr/bin/env python3
"""Check logical bounds and the operating system guard on both datastacks."""

import itertools
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    env = {**os.environ, "UBSAN_OPTIONS": "handle_segv=0:handle_sigbus=0"}
    with tempfile.TemporaryDirectory() as directory:
        binary = Path(directory) / "datastack_guard"
        for optimization in ("-O0", "-O2"):
            subprocess.run([
                "cc", "-I", ROOT, "-std=c11", optimization,
                "-Wall", "-Wextra", "-Werror",
                "-fsanitize=undefined", "-fno-sanitize-recover=all",
                ROOT / "validation/datastack_guard.c", "-o", binary,
            ], check=True)
            for stack, alignment, mode in itertools.product(
                ("fixed", "regions"), ("aligned", "partial"), ("ok", "overflow", "read", "write")
            ):
                result = subprocess.run(
                    [binary, stack, alignment, mode], capture_output=True,
                    text=True, timeout=5, env=env,
                )
                if mode == "ok":
                    valid = result.returncode == 0
                elif mode == "overflow":
                    valid = result.returncode == 1 and "corbo: limite de la datastack" in result.stderr
                else:
                    valid = result.returncode in (-signal.SIGSEGV, -signal.SIGBUS)
                assert valid, (stack, alignment, mode, result)
            print(f"{optimization}: 16 scénarios P1 confirmés")


if __name__ == "__main__":
    main()
