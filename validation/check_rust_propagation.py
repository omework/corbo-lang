"""Check postfix propagation in the Rust compiler and in the generated C."""

from pathlib import Path
import subprocess
import tempfile

from check_rust_destructors import FRONTEND


def main():
    fixtures = Path(__file__).with_name("fixtures")
    cases = {
        "propagation": "91\n92\n5\n105\n7\n3\n6\ntrue\n3\n90\n6\n7\ntrue\n9\n10\n11\n8\n22\n91\n8\n13\n",
        "propagation_owned": "16\n15\n2\n33\n1\n1\n3\n4\n2\n2\n5\n6\n7\n43\n44\n",
    }
    with tempfile.TemporaryDirectory(prefix="din-propagation-") as directory:
        source = Path(directory) / "program.c"
        binary = Path(directory) / "program"
        for name, expected in cases.items():
            program = (fixtures / f"{name}.crb").read_text()
            generated = subprocess.run([FRONTEND, "emit-c"], input=program, text=True,
                                       capture_output=True)
            assert generated.returncode == 0, generated.stderr
            source.write_text(generated.stdout)
            for optimization in ("-O0", "-O2"):
                subprocess.run(
                    ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                     "-fsanitize=undefined", "-fno-sanitize-recover=all", "-pthread",
                     source, "-lm", "-o", binary], check=True,
                )
                result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
                assert (result.returncode, result.stdout) == (0, expected), (name, result)

        package = Path(directory) / "package"
        module = package / "src/errors"
        module.mkdir(parents=True)
        (package / "package.toml").write_text('[package]\nname = "propagation"\n')
        (module / "types.crb").write_text("""
            pub enum Source { Failed }
            pub enum OtherSource { Failed }
            pub enum Destination { Failed, Other }
            impl Destination {
                fn from(value: Source) -> Destination { drop(value); Destination.Failed }
                fn from(value: OtherSource) -> Destination { drop(value); Destination.Other }
            }
            pub fn source() -> Result<i64, Source> { Err(Source.Failed) }
        """)
        (package / "src/main.crb").write_text("""
            use propagation::errors::{Destination as LocalError, OtherSource, source};
            fn run() -> Result<i64, LocalError> { Ok(source()?) }
            fn main() {
                match run() { Ok(_) => { print(0); }, Err(_) => { print(14); }, }
                let direct = LocalError::from(OtherSource.Failed);
                match direct {
                    LocalError.Failed => { print(0); },
                    LocalError.Other => { print(15); },
                }
            }
        """)
        built = subprocess.run([FRONTEND, "build", package, "-o", binary], capture_output=True, text=True)
        assert built.returncode == 0, built.stderr
        result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
        assert (result.returncode, result.stdout) == (0, "14\n15\n"), result

    shared = """
        enum Inner { Bad }
        enum Outer { Bad }
        fn number() -> Result<i64, Inner> { Err(Inner.Bad) }
        fn optional() -> Option<i64> { None }
        fn main() {}
    """
    refusals = [
        ("fn f() -> Result<i64, Inner> { Ok(42?) }", "? exige une valeur Result ou Option"),
        ("fn f() -> i64 { number()? }", "? exige un retour de la même famille"),
        ("fn f() -> Result<i64, Inner> { Ok(optional()?) }", "? exige un retour de la même famille"),
        ("fn f() -> Option<i64> { Some(number()?) }", "? exige un retour de la même famille"),
        ("fn f() -> Result<i64, Outer> { Ok(number()?) }", "Outer::from(Inner) -> Outer"),
        ("""impl Outer { fn from(error: &Inner) -> Outer { drop(error); Outer.Bad } }
            fn f() -> Result<i64, Outer> { Ok(number()?) }""", "Outer::from(Inner) -> Outer"),
        ("""impl Outer { fn from(error: Inner) -> Inner { error } }
            fn f() -> Result<i64, Outer> { Ok(number()?) }""", "Outer::from(Inner) -> Outer"),
        ("""impl Outer { fn from(error: Inner) -> Outer { drop(error); Outer.Bad } }
            impl Outer { fn from(other: Inner) -> Outer { drop(other); Outer.Bad } }""",
         "surcharge from dupliquée pour le même type source"),
        ("""impl Outer {
                fn from(error: Inner) -> Outer { drop(error); Outer.Bad }
                fn from(error: i64) -> Outer { drop(error); Outer.Bad }
            }
            fn invalid() -> Outer { Outer::from(true) }""", "aucune surcharge from pour ce type source"),
        ("""impl Outer {
                fn convert(error: Inner) -> Outer { drop(error); Outer.Bad }
                fn convert(error: i64) -> Outer { drop(error); Outer.Bad }
            }""", "nom de méthode en conflit"),
        ("""impl Outer {
                fn from(error: Inner) -> Outer { drop(error); Outer.Bad }
                fn from(error: i64) -> i64 { error }
            }""", "nom de méthode en conflit"),
        ("""fn f() -> Result<i64, Inner> {
                let value = number();
                let first = value?;
                Ok(first + value?)
            }""", "déplac"),
        ("""fn lift(target: &i64) -> Result<&i64, Inner> { Ok(target) }
            fn f() -> Result<&i64, Inner> {
                let local: i64 = 24;
                let reference = lift(&local)?;
                Ok(reference)
            }""", "cible locale"),
        ("""async fn worker(value: &i64) -> i64 { yield; *value }
            fn f() -> Result<i64, Inner> {
                let local: i64 = 24;
                let task = runtime::spawn(worker(&local));
                let n = number()?;
                drop(task.join());
                Ok(n)
            }""", "avant cette sortie"),
    ]
    for program, reason in refusals:
        result = subprocess.run([FRONTEND, "check"], input=shared + program, text=True,
                                capture_output=True)
        assert result.returncode != 0 and reason in result.stderr, (program, result.stderr)
    print(f"{len(cases)} propagation programs passed under UBSan at -O0 and -O2, "
          f"one package ran, {len(refusals)} refusals confirmed")


if __name__ == "__main__":
    main()
