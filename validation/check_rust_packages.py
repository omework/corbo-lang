#!/usr/bin/env python3
"""Exercise single-package loading, visibility, aliases and collision diagnostics."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"


def check_dependencies(workspace):
    def package(directory, name, body, entry="lib.crb"):
        (directory / "src").mkdir(parents=True)
        (directory / "package.toml").write_text(f'[package]\nname = "{name}"\n')
        (directory / "src" / entry).write_text(body)
        return directory / "package.toml"

    def git(directory, *args):
        return subprocess.check_output(
            ["git", "-C", directory, *args], text=True, stderr=subprocess.PIPE
        ).strip()

    def append(path, text):
        with path.open("a") as stream:
            stream.write(text)

    remote = workspace / "remote"
    package(remote, "pinned", "pub fn value()->i64 { 42 }")
    git(remote, "init", "-q")
    git(remote, "add", ".")
    git(remote, "-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-qm", "pinned")
    rev = git(remote, "rev-parse", "HEAD")
    (remote / "src/lib.crb").write_text("pub fn value()->i64 { 999 }")
    git(remote, "add", ".")
    git(remote, "-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-qm", "later")
    leaf = package(workspace / "leaf", "leaf", "pub fn value()->i64 { 45 }")
    middle = package(workspace / "middle", "middle",
                     "use leaf::value; pub fn score()->i64 { value() }")
    append(middle, '[dependencies]\nleaf = { path = "../leaf" }\n')
    root = workspace / "app"
    entry = "src/main.crb"
    manifest = package(root, "app", """
        use std::num::min_i64;
        use middle::score;
        use pinned::value;
        fn main() { print(min_i64(score(), value())); }
    """, "main.crb")
    append(manifest, f'[dependencies]\nmiddle = {{ path = "../middle" }}\n'
                     f'pinned = {{ git = "../remote", rev = "{rev}" }}\n')
    baseline = manifest.read_text()

    result = subprocess.run([FRONTEND, "emit-c", root], cwd=workspace,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    source, binary = workspace / "dependencies.c", workspace / "dependencies"
    source.write_text(result.stdout)
    for optimization in ("-O0", "-O2"):
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                        "-fsanitize=undefined", "-fno-sanitize-recover=all", source, "-o", binary],
                       check=True)
        result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
        assert (result.returncode, result.stdout) == (0, "42\n"), result

    program = (root / entry).read_text()
    for source_text, toml_text, diagnostic in [
        ("use leaf::value; fn main() {}", baseline, "not declared as a direct dependency"),
        (program, baseline.replace(rev, "main"), "full Git commit ID"),
        (program, baseline.replace(rev, "0" * 40), "git fetch failed"),
        (program, baseline.replace('middle =', 'wrong ='), "expected package wrong, found middle"),
        (program, baseline + 'std = { path = "../leaf" }\n', "invalid dependency name std"),
        (program, baseline.replace('path = "../middle"', 'path = "../middle", rev = "main"'),
         "expected exactly path, or git and rev"),
    ]:
        (root / entry).write_text(source_text)
        manifest.write_text(toml_text)
        result = subprocess.run([FRONTEND, "check", root], capture_output=True, text=True)
        assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
    (root / entry).write_text(program)
    manifest.write_text(baseline)
    append(leaf, '[dependencies]\napp = { path = "../app" }\n')
    result = subprocess.run([FRONTEND, "check", root], capture_output=True, text=True)
    assert result.returncode != 0 and "dependency cycle" in result.stderr, result.stderr
    print("path, pinned Git and bundled std executed under UBSan at -O0 and -O2, 7 refusals confirmed")


def check_target_selection(root):
    entry = root / "src/main.crb"
    program = """
        #(if: target.family == "unix" {
            use server::http::status as health;
        })
        #(if: target.os == "windows" {
            use server::config::status as health;
        })
        #(if: target.arch == "x86_64" {
            fn arch_code() -> i64 { 64 }
        })
        #(if: target.arch == "aarch64" {
            fn arch_code() -> i64 { 128 }
        })
        #(if: target.os == "never" {
            use missing::unavailable as health;
            fn arch_code() -> i64 { nonexistent() }
        })
        fn main() { print(health()); print(arch_code()); }
    """
    entry.write_text(program)
    for target, expected in [
        ("x86_64-unknown-freebsd", "200\n64\n"),
        ("aarch64-pc-windows-msvc", "201\n128\n"),
    ]:
        result = subprocess.run([FRONTEND, "emit-c", root, "--target", target],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        if "windows" in target:
            # This case selects Windows std as well. Compile and run it
            # with the Windows toolchain in check_rust_file.py.
            assert "CreateFileW" in result.stdout
            assert "INT64_C(201)" in result.stdout and "INT64_C(128)" in result.stdout
            continue
        source, binary = root / "target.c", root / "target-program"
        source.write_text(result.stdout)
        subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        source, "-o", binary], check=True)
        result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
        assert (result.returncode, result.stdout) == (0, expected), result
    for candidate, expected in [
        (program.replace('target.os == "windows"', 'target.os == "linux"'), "import collision for health"),
        (program.replace("target.family", "target.vendor", 1), "unknown target property"),
        ('#(if: target.os == "linux") { fn main() {} }', "malformed target condition"),
    ]:
        entry.write_text(candidate)
        result = subprocess.run([FRONTEND, "check", root, "--target", "x86_64-unknown-linux-gnu"],
                                capture_output=True, text=True)
        assert result.returncode != 0 and expected in result.stderr, result.stderr
    print("Unix target selection executed under UBSan, Windows selection checked, three refusals confirmed")


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "package.toml").write_text('[package]\nname = "server"\n')
        for module in ("http", "config"):
            (root / "src" / module).mkdir(parents=True)
        (root / "src/http/status.crb").write_text(
            "pub fn status()->i64 { base() } pub struct Point { x: i64 }"
        )
        (root / "src/http/base.crb").write_text("fn base()->i64 { 200 }")
        (root / "src/config/status.crb").write_text("pub fn status()->i64 { 201 }")
        entry = root / "src/main.crb"
        entry.write_text("""
            use server::http::{status as health, Point as point};
            use server::config as conf;
            fn main() {
                let p: point = point { x: health() };
                let health = 1;
                print(p.x);
                print(conf::status() + health);
                print(server::http::status());
            }
        """)
        result = subprocess.run([FRONTEND, "emit-c", root], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        source, binary = root / "program.c", root / "program"
        source.write_text(result.stdout)
        for optimization in ("-O0", "-O2"):
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                 "-fsanitize=undefined", "-fno-sanitize-recover=all", source, "-o", binary],
                check=True,
            )
            result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
            assert (result.returncode, result.stdout) == (0, "200\n202\n200\n"), result

        cases = [
            ("use server::http::status; use server::config::status; fn main() {}",
             ("import collision for status", "server::http::status", "server::config::status")),
            ("use server::http::{status as item, Point as item}; fn main() {}",
             ("import collision for item",)),
            ("use server::http::status; fn status() {} fn main() {}",
             ("conflicts with local declaration status",)),
            ("use server::http::base; fn main() {}",
             ("private component server::http::base",)),
            ("use server::http; fn main() { print(http::base()); }",
             ("private component server::http::base",)),
            ("use server::missing; fn main() {}",
             ("unknown import or component",)),
            ("use std::net::missing; fn main() {}",
             ("unknown import or component std::net::missing",)),
            ("use server::http; pub fn http() {} fn main() {}",
             ("ambiguous path server::http",)),
            ("fn other() {}", ("missing synchronous main",)),
        ]
        for program, expected in cases:
            entry.write_text(program)
            result = subprocess.run([FRONTEND, "check", root], capture_output=True, text=True)
            assert result.returncode != 0 and all(
                message in result.stderr for message in expected
            ), (program, result.stderr)
        print(f"1 package executed under UBSan at -O0 and -O2, {len(cases)} refusals confirmed")
        check_target_selection(root)
        check_dependencies(root)


if __name__ == "__main__":
    main()
