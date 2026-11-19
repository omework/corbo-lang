# Initial Corbo repository snapshot

## Boundary

This repository starts with a parentless commit of the tracked din-lang tree at
`f905f1afd8c462f633e0ae09d5f058ad9de6c321`. The old Git history is not imported;
it remains available in [omework/din-lang](https://github.com/omework/din-lang).
The active compiler remains in [omework/corboc](https://github.com/omework/corboc).

All 5,083 source-tracked files were copied and compared byte for byte before
updating repository links. This includes the STD, both readable runtimes,
grammar, rules, licenses, examples, editor resources, historical frontends,
validation sources/artifacts and existing cycle reports. The old reports retain
their original paths, names, hashes and observations as historical evidence.
Ignored build products, caches, local configuration and the old `.git` directory
are excluded. No files are removed from the original checkout.

The intentional snapshot differences are README repository/clone instructions,
the compiler-repository guide, this migration record and its matrix entry.
No STD/runtime implementation, language grammar, normative rule or compiler
algorithm changes as part of this move.

## Handoff

The canonical language remote is `git@github.com:omework/corbo-lang.git`.
The companion compiler's source lock will point to this initial snapshot rather
than a din-lang revision. Its local `.deps/corbo` checkout can be advanced only
when clean; the old history remains in that cache until it is recreated.

## Validation scope

Snapshot completeness and unchanged compiler inputs passed comparison. Generated
STD/runtime reference freshness and README/source synchronization passed; the
UTF-8 text example executed successfully through the existing compiler on macOS
ARM64 with fatal UBSan. The companion compiler records the
new immutable source pin and the pinned build smoke check. No broad compiler or
safety campaign is warranted by this organization-only change.

Existing platform limitations and the status of independent audits remain as
recorded in the carried-over reports; this move makes no new safety claim.
