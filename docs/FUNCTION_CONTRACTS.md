[Français](FUNCTION_CONTRACTS-fr.md)

<a id="contrats-mémoire-des-fonctions--inventaire-et-proposition"></a>

# Function memory contracts: inventory and proposal

The inventory describes the nature of the project.
The current compiler. The focus is to infer contracts since
the operations of the body, without adding annotation of provenance to the signatures.
Summary of source effects and results are now implemented according to the
[EFFECTS.md](EFFECTS.md), [RESULTS.md](RESULTS.md) and
[SOURCE_CONSTRAINTS.md](SOURCE_CONSTRAINTS.md). A passage from the auditor on
[body with symbolic entries](FUNCTION_BODIES.md) is also in place.
[Verification of calls from contracts only](MODULAR_CALLS.md) is
Now in place for the current subset; the backend C remains specialized.

<a id="problème-observé"></a>

## Observed problem

The compiler validates signatures and infers source effects before the
calls. Memory checker now runs all bodies with entries
It also keeps controls when a call is made.
provides its actual allocations and sources, and then produces a specialized C version.

The two examples of the initial inventory are now rejected even without
call: the analysis of the effects detects the reset via a read source, and
stress analysis runs through readings and detects the unknown name.

```rust
fn broken() { print(missing); } // Variable inconnue, même sans appel.
```

```rust
fn clear(memory: &Allocator) { memory.reset(); } // Source non mutable.
```

Unused body movements and borrowings are now controlled by
The sub-calls of this
pass only use their contracts, with mode verification, types,
constraints and compatibility of storage of the sources provided.
The body is still running through the body to produce the C and maintain its consistency controls.

<a id="ce-que-les-signatures-expriment-déjà"></a>

## What signatures already express

| Notation actuelle | Information already expressed |
| --- | --- |
| `n: Int` | Copy of an Int; no access to the caller storage by this parameter. |
| `data: &Int` ou `&E` | The amount of the allowance is taken from the amount of the allowance. |
| `data: &mut Int` ou `&mut E` | Exclusive mutable borrowing; does not confer the right to replace or transfer the allowance. |
| `data: -> Int` ou `-> E` | Explicit transfer to the entrance; the appellant's former access is consumed. The provenance and cleaning accompany the allowance. |
| `memory: &Allocator` ou `&Pool<T>` | Reading access to a source; no allocation or reset via this access. |
| `memory: &mut Allocator` ou `&mut Pool<T>` | Authorizes source operations, including allocation, explicit destruction by the source and reset. |
| `-> Int` | Return of a copied value. |
| `-> <- Int` ou `-> <- E` | Return of an allowance of the type declared, received by the appellant. |
| Retour omis ou `-> Void` | No results. |

The already general controls include the existence of types, modes and
the explicit parameters, duplicated parameters and constraints on `main`. The rules
of exclusivity, order of arguments and lifespan continue to apply
each call; they do not require a new annotation for each use.

<a id="informations-du-contrat-et-état-actuel"></a>

## Contract information and current status

| Information | Current status and need for full independent audit |
| --- | --- |
| Types available by each source | Requirements now inferred in the summary; compatibility verified after substitution of the concrete sources to the call. |
| Source of the return allowance | Symbolic alternatives now inferred, substituted with the sources of arguments and applied to the concrete result. |
| Identity of result | Guaranteeed symbolic returns now inferred, verified on the roots of origin, and nominal identities retained at receptions. |
| Reset sources, including conditionally | Effects now inferred once per function, propagated by substitution in subcalls and used for C catches. |
| Parameter source relationships | `memory.drop(-> data)` requires a single source equal to `memory`A selection of returns retains the union of possible sources, which are now inferred and substituted for calls. |
| Possible incompatible sources | If a function resets a source and reads a loan, it must prove that this source is not the source of the loan, or refuse the combination; the order of operations now allows to infer the distinction required, then the concrete control checks it. |
| Routes of termination | `may_return` is inferred for the analysis of effects; returned types and cleanings are controlled with symbolic inputs then to the actual calls. |

The change in the value of a `&mut Int` Don't destroy his allowance.
Distinguishing it from a reset invalidation.
means not reset all its source, and does not require to pass separately
an allocator for cleaning.

<a id="contenu-minimal-proposé-dun-contrat"></a>

## Proposed minimum content of a contract

The contract represents properties of all the calls allowed, with
symbolic identities and sources rather than objects of a particular call.
It shall contain:

1. The types and modes already written in the signature.
2. The types that each source must be able to allocate, regardless of choice
   concrete backend (tas, stack, compatible pool).
3. The relationship required between the sources of the parameters: equality or
   distinction, when the body depends on it.
4. The source of the allocated result, and separately the possible guarantee of
   exactly return an allowance transferred to the entrance.
5. The effects of invalidation on sources: no reset, or
   possible reset of such source. A possible effect should be
   kept even if a particular path does not execute it.
6. The necessary information on returns and paths without continuation.

The precise representation of the results can be richer than their syntax
public: new result in a source, restitution of an incoming identity,
or selection between candidates. A guarantee of identity must not be announced
if all the return routes concerned respect it.

A source annotation describes a storage dependency.
not maintain a mutable loan from the allocator throughout the life of the object
returned: this would contradict the A4 rule for re-use of the source.

<a id="exemple--construire-une-allocation"></a>

### Example: Build an allowance

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}
```

The contract must establish: Int Living result, source `memory`, allocation
created by this invocation, no reset of the source.
The last property is not sufficient for the mutable to establish.

The contract must also require that: `memory` may allocate Int.
reproduced: this signature is currently accepted with `allocator()` and
`pool<Int>(1)`but his body is refused with `pool<E>(1)`. The generic type
`Allocator` This guarantee is not yet provided by itself.
allocates only a temporary Int then destroys it has the same requirement, even
The independent audit must therefore retain the right to
this requirement as a condition of compatibility with the appeal.

This is the type of storage accepted, not sufficient evidence of capacity:
the runtime shutdown on exhaustion remains the current choice.

<a id="exemple--restituer-une-allocation-reçue"></a>

### Example: returning an allowance received

```rust
fn forward(mut data: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- data; }
    return <- data;
}
```

The contract must establish: former consummated access to the entrance, same allowance
returned on all returns, same source and same address. This must remain
The recent audit
demonstrated why systematically replacing this identity with an identity
The absence of such a system would result in the loss of current valid transfers.

### Exemple : choisir entre deux allocations

```rust
fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
```

The two old accesses are consumed.
the other one is cleaned. The prototype now retains the union of sources
The undersigned contract must retain this union.
that the result is always `a`, ni toujours `b`.

<a id="exemple--réinitialiser-une-source"></a>

### Example: Reset Source

```rust
fn clear(memory: &mut Allocator) {
    memory.reset();
}
```

The effect is that the appellant's allowance for this source, even if it is
are not arguments of `clear`. The verification of the appeal must therefore be
control future uses and invalidate the access concerned. A wrapper who
appelle `clear` shall have the same effect.

Conditional reset is a possible effect.
old accesses cannot be used without sufficient proof, and the
cleaning C must distinguish the paths where the objects were destroyed.

<a id="exemple--relation-entre-source-et-emprunt"></a>

### Example: Source-borrow relationship

```rust
fn clear_then_read(memory: &mut Allocator, data: &Int) -> Int {
    memory.reset();
    return *data;
}
```

The function can work when `data` Depends on another source.
can't accept the case where `data` from `memory`. Modular verification
does not implicitly assume that two parameters have sources
It must have the required relationship, or refuse that body.

<a id="orientation-retenue--contrats-inférés-depuis-le-corps"></a>

## Guidance: contracts inferred from the body

`new`, borrowing, transfers, returns and `reset` are recognised transactions
They feed its monitoring of allocations and sources.
The source of the result must be deducted from this monitoring; the proposed rating
initialement `from memory` is not retained for functions whose body
is available.

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}
```

In the independent verification, `memory` is a symbolic source.
The result is that source. At the call, this symbolic source is
This link is not a transferable loan
the source maintained for the entire life of the result.

The same principle allows the preparation of other information in the contract:

- An entry identity on all returns is maintained.
- Separate candidates remain distinct; the relationship between their sources
  The requirements of the current rules are constraints to be checked at the call.
- Operations `new` require the types that a source must accept, including
  for temporary workers who have not returned.
- Operations `reset` cause invalidation effects, to be spread to
  through sub-calls and to check against future usages of the appellant.

The intention remains in the explicit operations of the body.
constraints on equality and distinction of sources are now implemented
and tested; calls now use these contracts without browsing the bodies.
A statement
without a body, including external ones, would require a contract provided otherwise;
External C calls remain out of the prototype.

<a id="cas-suivant--sélectionner-entre-deux-allocations-reçues"></a>

## Next case: select between two allowances received

For `choose(a: -> Int, b: -> Int, n: Int) -> <- Int`, retournant `a` ou `b`
The following two candidates are retained by one branch and the union of
The initial proposed constraint on equality of sources
is abandoned. No additional allocator parameter is required.

The two old accesses are consumed at the entrance. The result does not promise
the identity of `a` or the `b`. The unreturned candidate is destroyed on the
path executed. Each possible source remains protected against invalidation
This union is now incompatible with future uses of the result.
Implemented for concrete sources and symbolic summaries of results;
the verification of contracts calls is also in place. See
[PROVENANCES.md](PROVENANCES.md) and [MODULAR_CALLS.md](MODULAR_CALLS.md).

<a id="procédé-dimplémentation-proposé"></a>

## Proposed Implementation Process

1. Represent contracts separately from concrete objects and issue C.
2. For the current non-recursive function graph, check the bodies, y
   including unused, with symbolic parameters and contracts of
   Refused contracts that were not met.
3. To the appeals, substitute actual allocations/sources, check the
   relationships, types of loans and loans, then apply the effects and the receipt of the result.
4. Compare this new control to the current specialized test analysis
   accepted/refused and traces C. Any differences must be examined.
5. First, keep the specialized backend C. Do not remove this specialization.
   that after defining an equivalent runtime mechanism for effects.

Checking a function independently does not immediately require a single
function C shared by all calls. The current backend passes pointers
and indicators for cleaning the appellant's allowances to a caller that can be
a source. A generic C function cannot simply call the
Reset low level: it waits for the destroyers to be executed.

The physical list of the pool does not give logical order by scopes alone
and receptions imposed on the reset. A generic backend would require a protocol
cleaning system preserving this order, or another representation explicitly
This difficulty must not delay the separation of the
and its contracts.

<a id="validation-à-prévoir"></a>

## Validation to be expected

- Body errors detected even without a call.
- Same contract verified for actual sources of different types/capacity
  without reinterpreting its warranties in each appeal.
- Source of coherent result on all returns; local source refused.
- Identity preserved for guaranteed refunds and no old access
  reactivated at an explicit reception.
- Relationships of identical/distinct sources verified to calls.
- Alloyable type requirements verified without reanalysis of body: Int admitted
  on compatible/stack/pool Int and refused on a pool of another type.
- Direct, conditional and transitive effects; protection of borrowing
  and arguments prepared; destruction and clean-up exactly once.
- Trace and destruction order with backend C.

[direct returns &Int](DIRECT_BORROW_RETURNS.md) are now implemented
with `reference_targets` and child verification → parent. [back &mut Int](MUTABLE_BORROW_RETURNS.md) now keep the mode
exclusive and the same target identities. Recursion, transitive graphs
and the separate compilation remain delayed.
&Int immutable fields have a dedicated subset in
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md) ; their origin in a parameter
is kept in contracts. [Alloted returns of &Int carriers](BORROWED_RETURNS.md)
are also available for already sustainable targets in the parent.
