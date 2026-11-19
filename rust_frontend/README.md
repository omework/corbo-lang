[Français](README-fr.md)

<a id="frontend-rust-de-crust"></a>

# Corbo Frontend Rust

The crate exposes `frontend(source, mode)`. It produces tokens with
their bytes positions, an indexed syntactic tree and a tree
static with scopes, links and execution points. The facts
structured include uses, named travels, catches,
borrowings, pools, projections, calls, writings and exits.
Types, sources and effects that require resolution
semantics are established by a separate pass. The package loader uses the `toml` crate to read manifests. Modes `program`, `block` and
`signature` stop at the tree.

From the root of the repository, compile and then display a tree.

```sh
CARGO_TARGET_DIR=build/rust_frontend cargo build --offline --manifest-path rust_frontend/Cargo.toml
printf '%s\n' 'fn main() { print(7); }' | build/rust_frontend/debug/corbo-frontend program
```

Modes `block` and `signature` read autonomous fragments.
Mode `--batch` is used for comparison with the corpus.

```sh
python3 validation/build_representation_corpus.py
python3 validation/compare_rust_frontend.py
```

The comparator produces `build/rust_frontend_comparison.jsonl`.
It compares the following of the standardized leximes, the parents and lines
d-input of the telescopes, the names of the local links in their order,
accounts for borrowings, pools, candidate addresses and
named trips, and the links of these trips.
See [cycle report]](../docs/cycles/CORE_COMPOSITION_CYCLE.md#frontend-rust-et-comparaison-du-corpus)
for deviations and limitations of this comparison.

<a id="vérification-et-génération-c"></a>

## Verification and generation C

`check` check the supported subset.
`emit-c` applies the same verifier before issuing C on
the standard output. The generator receives a `VerifiedProgram`.

```sh
build/rust_frontend/debug/corbo-frontend check < programme.crb
build/rust_frontend/debug/corbo-frontend emit-c < programme.crb > programme.c
cc -std=c11 -pthread programme.c -lm -o programme
```

The current scope covers `bool`, `i32`, `i64`, `u8`, `u16`, `u32`,
`u64`, `f32`, `f64` and their references
in synchronous functions. It includes blocks, branches,
`while`, `loop` with or without result, movement and
The Commission has already taken a number of decisions concerning the application of the Treaty to the Community.
possible source parameters and substitutes them for the call.
C uses Clang or CCG overflow intrinsics to
addition, subtraction and multiplication.
follows the future uses of local references through the branches,
The reference used in the course of a study is the following:
next iteration keeps its reservation.
may use an approximation of their provenances.

For synchronous fixed aggregates, post-AST analysis follows
travel to the destination scope and can share a location
between exclusive arms that feed the same recipient. When a function
built its result, the caller provides typed output locations.
A relay propagates these locations or keeps the address of a result
transmitted from a parameter.

The plan also places the links, parameters and results materialized by the
The scalar results of the study are
blocks, branches and calls can relay the address of the receiver.
temporary calculation remain expressions or temporary C.

The runtime reserves an anonymous virtual beach with `mmap` First
need. An inaccessible page protects the end of each data range. Each reservation advances an aligned cursor after checking for
the capacity. The block exits, returns, `break` and `continue` restaurent
The receiver's anticipated locations are reserved before
this brand and remain accessible after restoration.

Optional Ownership `#(datastack: size=...)` sets the capacity in units
binaires `K`, `M` ou `G`. Without it, the compiler composes the reservations
post-AST, their alignments, scope paths and accessible calls
since `main`. The C evaluates this terminal at start with sizes and
Target ABI alignments. Accessible recursive calls give a
unknown terminal. In this case, the runtime uses the available pages if
the platform exposes them by `sysconf`, or physical pages, divided
by the number of CPUs online.

`python3 validation/check_rust_datastack_capacity.py` compares capacity
maximum selection observed in C controls.

The tables, enums and nested structures can bear references.
The verifier tracks their provenance and last use by position.
A contract links the position of the argument to the position of the result.
A dynamic index keeps the sources of all possible boxes.
Direct borrowings keep the reservation of their storage root.
A re-borrowing of a stored reference may be limited to a field or a field of
box, including through a borrowed aggregate.

A local pool reserves its entire area in the datatack, with a cursor
and a register of separate slots per variant for enums.
`match &allocation` reads the tag and payload of the variant directly
a game borrowed binds the aggregated fields by reference,
with the transfer right of the match recipient. Functions receive pools by loan
and may consume or return `A<T>`. Un transfert d’`A<T>`
keeps the slot and associates its cleaning with the receiver, provided that
Pool and dependencies of value survive.

To reproduce the targeted controls, execute
`python3 validation/check_rust_placement_dependencies.py` after
construction of the frontend. Unsolved recursive contracts retain
All candidate sources.

The `Vector<T>` With fixed elements without dependencies and `String` established
by `pool<T>.new()` place their descriptor in the pool slot and their
The transfer of the allowance shall be retained in a separate region.
the region and its limit. Cleaning restores the area before the slot of the
Pool. Frontend supports `push`, `len` and indexed reading of the
vecteurs ainsi que `push_str` on a UTF-8 literal and `byte_len` for
`String`.

`region_size` and `region_stack_size` above their deduced limits.
The post-AST composes the peak of occupation of the regions with the transfers
exclusive arms contribute by their maximum.
When coexistence remains undetermined, the plan directs acquisitions
The Commission has already taken the view that the Commission's proposal is not sufficient to ensure that the Commission's proposals are properly implemented.
Unbounded growth uses 100 Mio template in the absence
configuration.

`#(stack_region: max_size=..., count=...)` can reserve a dedicated area
The plan calculates a local capacity when
`count` is omitted. If the locations of the annotated area are occupied,
Runtime can open a dedicated region of the same template.
The template of a value triggers the limit diagnosis.

Optional thresholds `reclaim_threshold` and `region_reclaim_threshold`
enable automatic return of free pages. `#(free_pages)` the
also asks below the threshold, after cleaning the block.
virtual remain reserved.

The `HashMap<K,V>` with primitive, borrowed or allocated values place their descriptor via the
same post-AST plan. L-linked index and entries occupy a region.
The live entries keep their address and the table re-uses the
The backend lowers the locations removed. `insert`, `get`, `get_mut` and
`remove`, with a result `Option`. A borrowed result protects the
table until its last use.

The reference and reference vectors `A<T>` maintain the dependencies of
the elements. Cleaning releases the allowances possessed in order
Inverse integration before returning the region of the vector.
The auditor retains the union of dependencies at control junctions.
`pop` and `remove` extract the handles from `Vector<A<T>>`. The
sources of the table and vector remain conservative after
replacement or extraction.

`python3 validation/check_rust_regions.py` and
`python3 validation/check_rust_region_collections.py` exercent ces chemins
synchrones.

`runtime::thread({ ... })` lowers a synchronous worker pthread block.
His handle can cross telescopes and calls. The block captures by
`move nom;` fixed values, including those with slots
In case of failure of launch, the catches owned are
The results of the project can be used to finance loans or grants.
and dimension the worker's datatacks.

The call for a `async fn` creates an inactive Future. `runtime::spawn`
l , entered in the runtime line and returns a `Handle<R>` with
`join()`. `runtime::spawn_blocking` Launches Future on a thread
dedicated in async context and returns a `AsyncHandle<R>` with `.await`.
Ces deux formes produisent `Result<R, runtime::Error>`. Un `.await`
direct consumes an inactive Future and produces directly `R`.
The post-AST plan retains the recovery points, temporary and
The scope marks of blocks, branches and loops.

One `HashMap` can pass a task by value in
The fixed catch and results may be used for borrowing and borrowing purposes.
own slots `A<T>`. The result only retains the
the responsibility to clean up the
slots move from capture to status and then to receiver in case of transfer.
An aggregate placed in a pool or added to a vector transmits slots
The cleaning makes the children slots before the container.
the container.

One `async fn` Call the others `async fn` creating a Future.
She can wait directly with `.await` or throw it on a thread
dedicated with `runtime::spawn_blocking` Then wait for his handle.
Direct call from a `fn` synchronous from a `async fn` is prohibited
in the core.

Compile C programs that run a thread with `-pthread`.
`python3 validation/check_rust_native_regions.py` and
`python3 validation/check_rust_task_regions.py` Replay witnesses.

To compile a multi-file project, pass the package directory to `check` or
`emit-c`. See [packages and modules](../docs/MODULES.md).
