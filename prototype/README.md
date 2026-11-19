# Python prototype

This directory contains the historical Python compiler. The corpus builder and the historical tests use it as a reference. The supported compiler entry points are [corboc](../corboc/README.md) and the [Rust frontend](../rust_frontend/README.md).

Run these commands from the repository root.

```sh
python3 prototype/crust.py check examples/while.crb --syntax-only
PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests
python3 validation/build_representation_corpus.py /tmp/corbo-representation-corpus.jsonl
```

Set `CRUST_SANITIZE=undefined` on the unittest command to enable UBSan in the tests that support it. The standalone scripts under [tests](../tests) that validate emitted C or copy modules into isolated mutation workspaces locate the prototype themselves.
