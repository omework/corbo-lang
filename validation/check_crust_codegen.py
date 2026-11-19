"""Compare the native behavior of both backends on the accepted verifier corpus."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import tempfile
from textwrap import dedent

from check_crust_verifier import FRONTEND, PACKAGE, REGRESSIONS, STATIC_REGRESSIONS, corpus, rust_batch
from check_rust_task_regions import ACCEPTED as TASK_REGION_CASES


def accepted_cases():
    cases = {}
    for label, source in corpus():
        if len(source.encode()) <= 131072:
            cases.setdefault(source, label)
    for index, source in enumerate(STATIC_REGRESSIONS):
        cases.setdefault(source, f"static fixture {index}")
    for index, (source, _) in enumerate(REGRESSIONS):
        cases.setdefault(source, f"verifier fixture {index}")
    return [
        (cases[source], source)
        for source, verdict in zip(cases, rust_batch("verify", cases), strict=True)
        if verdict == "OK"
    ]


# These existing reachability tests specify an unconditional infinite loop.
# For them compare observable output up to the same execution deadline.
NONTERMINATING = {
    "fn main() { loop { continue; let mut unreachable = 1; } }",
    "fn main() { loop {} let mut unreachable = 1; }",
}

# The native task fixtures with list expectations have independent writers.
# Keep their existing oracle for the exact set and multiplicity of output lines.
UNORDERED_OUTPUT = {
    dedent(source).strip(): Counter((line + "\n").encode() for line in expected)
    for _, source, expected, _ in TASK_REGION_CASES if isinstance(expected, list)
}


def run(args, directory, input_bytes=b"", timeout=20):
    try:
        return subprocess.run(args, cwd=directory, input=input_bytes, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(args, 124, error.stdout or b"", b"timeout")


def execute(directory, timeout):
    try:
        process = subprocess.run(["./program"], cwd=directory, capture_output=True, timeout=timeout)
        return process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as error:
        return None, error.stdout or b"", error.stderr or b""


def output(process):
    return [process.returncode, process.stdout.decode(errors="backslashreplace"),
            process.stderr.decode(errors="backslashreplace")]


def compare_traces(source, rust, crust):
    unordered = UNORDERED_OUTPUT.get(dedent(source).strip())
    if unordered is None:
        return "match" if rust == crust else "execution"
    if (rust[0] == crust[0] == 0 and rust[2:] == crust[2:]
            and all(Counter(trace[1].splitlines(keepends=True)) == unordered for trace in (rust, crust))):
        return "unordered match"
    return "execution"


def compare(bootstrap, case, sanitize):
    label, source = case
    result = {"label": label, "source": source}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        (path / "input.crb").write_text(source)
        # Use separate working directories so files created by one executable
        # cannot affect the other executable's behavior.
        for name in ("rust", "crust"):
            (path / name).mkdir()
        reference = run([FRONTEND, "emit-c"], path, source.encode())
        emitted = run([bootstrap, "--emit-c", "input.crb"], path)
        if reference.returncode or not reference.stdout:
            result.update(status="Rust emission", diagnostic=output(reference))
        elif emitted.returncode or not emitted.stdout:
            result.update(status="unsupported" if emitted.returncode == 9 else "Crust emission",
                          diagnostic=output(emitted))
        else:
            flags = ["-std=c11", "-pthread", "-O2" if sanitize else "-O0"]
            if sanitize:
                flags += ["-fsanitize=undefined", "-fno-sanitize-recover=all"]
            for name, gen in (("rust", reference), ("crust", emitted)):
                build = run([os.environ.get("CC", "cc"), *flags, "-x", "c", "-", "-lm",
                             "-o", "program"], path / name, gen.stdout)
                if build.returncode:
                    return dict(result, status=f"{name} C build", diagnostic=output(build))
            actual = {}
            for name in ("rust", "crust"):
                directory = path / name
                executed = execute(directory, timeout=1 if source in NONTERMINATING else 20)
                files = {str(file.relative_to(directory)): file.read_bytes().hex()
                         for file in sorted(directory.rglob("*")) if file.is_file()
                         and file != directory / "program"}
                actual[name] = (*executed, files)
                code, stdout, stderr, _ = actual[name]
                result[name] = [code, stdout.decode(errors="backslashreplace"),
                                stderr.decode(errors="backslashreplace"), files]
            if any(trace[0] is None for trace in actual.values()):
                result["status"] = (
                    "bounded match" if source in NONTERMINATING and actual["rust"] == actual["crust"]
                    else "timeout"
                )
            elif any(b"UndefinedBehaviorSanitizer" in trace[2] or b"runtime error:" in trace[2]
                     for trace in actual.values()):
                result["status"] = "sanitizer"
            else:
                result["status"] = compare_traces(source, actual["rust"], actual["crust"])
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bootstrap", type=Path)
    cli.add_argument("--report", type=Path)
    cli.add_argument("--require-parity", action="store_true")
    cli.add_argument("--ubsan", action="store_true")
    cli.add_argument("--jobs", type=int, default=4)
    args = cli.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        bootstrap = args.bootstrap
        if bootstrap is None:
            bootstrap = Path(directory) / "corboc"
            subprocess.run([FRONTEND, "build", PACKAGE, "-o", bootstrap], check=True)
        bootstrap = bootstrap.resolve()
        cases = accepted_cases()
        print(f"{len(cases)} accepted programs", flush=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            rows = list(pool.map(lambda case: compare(bootstrap, case, args.ubsan), cases))
    counts = Counter(row["status"] for row in rows)
    print(", ".join(f"{count} {status}" for status, count in sorted(counts.items())))
    matches = {"match", "bounded match", "unordered match"}
    if args.report:
        args.report.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                       for row in rows if row["status"] not in matches))
    if args.require_parity and sum(counts[status] for status in matches) != len(cases):
        raise SystemExit("Executable parity is incomplete")


if __name__ == "__main__":
    main()
