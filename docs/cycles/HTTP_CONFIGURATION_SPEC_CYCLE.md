# HTTP parsing and configuration override specification cycle

## Scope

User-approved design recording only. Core: configurable module constants and
lexical constant overrides. STD/API: HTTP request and response parsing blocks.
No implementation, compiler test, runtime test or platform validation requested
or performed. No independent safety-audit result is claimed.

## Recorded decisions

- CC1–CC7: opt-in configuration defaults, compile-time typed replacements,
  nested lexical inheritance, isolated transitive call specialization, derived
  constant evaluation where supported and retained object configuration.
- HTTP: structural reader contract; request()/response(); owned bounded head
  storage; no storage or Limits argument; optional streaming body readers.
- Header-based body indication does not resolve request-dependent semantics.
  The application handles HEAD and other exchange context.
- Request/header default bounds and a complete lexical-scope example.

## Specification checks

Local documentation links, required production declarations/references,
annotation spelling, complete example presence and whitespace were checked.
These checks do not run or validate the proposed syntax with corboc.
The matrix and implementation checklist explicitly retain that boundary.

## Interactions and remaining work

N1/N6: replacements must be typed compile-time values, not runtime state.
N2/N4/N7: a parsed message owns its head storage and borrows its reader;
configuration changes neither move semantics nor cleanup/dependency obligations.
N8: helper calls and escaping objects must preserve the effective specialization.
G1/G2/G9: static bounds inform placement; they do not guarantee available region
space or require eager commitment of the full budget.

Compiler and HTTP implementation remain pending. This decision does not specify
new constant-expression operations, response status-line/body budget constants,
close-delimited body/handoff APIs, final error/header traversal APIs, async
signatures or a server architecture. Existing executable evidence is unchanged.
