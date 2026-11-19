"""Exercise the async socket backend and the address parser on loopback."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from check_rust_assembly import ROOT, FRONTEND


FIXTURES = Path(__file__).parent / "fixtures/async_network"


def emit(frontend, package, target):
    command = [frontend, "emit-c", package]
    if target:
        command.extend(["--target", target])
    return subprocess.run(command, capture_output=True, text=True, timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--frontend", type=Path, default=FRONTEND)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--runner", default="")
    parser.add_argument("--compile-only", action="store_true")
    parser.add_argument("--ubsan", action="store_true")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    windows = "windows" in args.target if args.target else os.name == "nt"
    extension = ".exe" if windows else ""

    with tempfile.TemporaryDirectory(prefix="din-async-net-") as work:
        package = Path(work)
        (package / "src").mkdir()
        (package / "package.toml").write_text('[package]\nname = "async_net_probe"\n')
        main_source = package / "src/main.crb"
        generated = package / "program.c"
        for case, expected in [("tcp", ["42", "1", "1", "true"]), ("udp", ["1", "1"]),
                               ("address", ["8042", "2130706433", "3", "5"])]:
            source = (FIXTURES / f"{case}.crb").read_text()
            main_source.write_text(source)
            compiled = emit(args.frontend, package, args.target)
            assert compiled.returncode == 0, compiled.stderr
            implementations = {"rust": compiled.stdout}
            if args.corboc and case == "address":
                result = subprocess.run(
                    [args.corboc, "--emit-package-c", package, "--stdlib-dir", ROOT / "stdlib/src"],
                    capture_output=True, text=True, timeout=60,
                )
                assert result.returncode == 0, (result.returncode, result.stderr, result.stdout[:300])
                implementations["crust"] = result.stdout

            for implementation, code in implementations.items():
                generated.write_text(code)
                for opt in ("-O0", "-O2"):
                    label = f"{case}-{implementation}-{opt[1:]}"
                    options = ["-fsanitize=undefined", "-fno-sanitize-recover=all"] if args.ubsan else []
                    output_dir = args.artifacts or package
                    output_dir.mkdir(parents=True, exist_ok=True)
                    binary = (output_dir / (label + extension)).resolve()
                    link = ["-lws2_32"] if windows else ["-lm"]
                    subprocess.run(
                        [*shlex.split(args.cc), "-std=c11", "-pthread", opt, *options, generated,
                         *link, "-o", binary], check=True, timeout=60,
                    )
                    if not args.compile_only:
                        result = subprocess.run([*shlex.split(args.runner), binary], capture_output=True,
                                                text=True, timeout=30)
                        assert (result.returncode, result.stdout.splitlines()) == (0, expected), (
                            label, result.returncode, result.stdout, result.stderr,
                        )
                    print(f"{label}: {'linked' if args.compile_only else 'passed'}", flush=True)

        source = (FIXTURES / "tcp.crb").read_text()
        before_drop = source.replace("    drop(connection);\n", "", 1)
        for half in ("reading", "writing"):
            join = f"    match {half}.join() {{"
            main_source.write_text(before_drop.replace(join, f"    drop(connection);\n{join}", 1))
            rejected = emit(args.frontend, package, args.target)
            assert rejected.returncode != 0 and "emprunt" in rejected.stderr, rejected.stderr
            print(f"drop before {half} join: rejected", flush=True)

        main_source.write_text(
            "use std::sys::net::reactor;\n"
            "fn main() {}\n"
        )
        rejected = emit(args.frontend, package, args.target)
        assert rejected.returncode != 0 and "private platform component" in rejected.stderr, rejected.stderr
        print("import of platform reactor: rejected", flush=True)


if __name__ == "__main__":
    main()
