# Bounded inline UTF-8 strings — specification record

Scope: core/grammar design only, accepted by the user on 2026-11-20.

- Recorded TX23 in the UTF-8 specification and language-rule index (EN/FR).
- Extended EBNF generic arguments to admit integer literals for `String<N>`.
- Kept plain `String` growing; bounded content occupies fixed inline payload
  plus length metadata. Exceeding the byte bound is invalid without truncation.
- Left constructor/mutation APIs, exact layout/disk encoding and Copy
  classification unspecified; no general user constant-generics feature added.

No compiler, runtime or STD implementation changed. No executable tests,
platform runs or safety audit performed. The representation's exact layout and
future integration require subsequent work; current support is not claimed.

Follow-up: implementation and executed evidence are recorded in
[BINARY_TIME_BOUNDED_CYCLE.md](BINARY_TIME_BOUNDED_CYCLE.md). The statements above
describe the earlier specification-only step.
