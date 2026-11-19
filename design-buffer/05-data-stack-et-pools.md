[Français](05-data-stack-et-pools-fr.md)

<a id="brouillon-05--data-stack-et-pools-typés"></a>

# Draft 05 — Data stack and typified pools

Decisions selected in the workshop, to be included on request.
completes the [skinning broiler 03](03-depilement-des-scopes.md)
and the [04 bounty on the pools of states async](04-async-et-select.md).

<a id="contrat-de-stockage"></a>

## Storage contract

- Values created outside of a pool use the default data stack.
  The compiler manages stacking, depilation and placement.
  classic stack is not a public type and the programmer does not
  It's not built with `stack(octets)`.
- Fixed size values may be invested to promote recovery
  If the compiler determines that certain values are
  destroyed first, it piles them last when the placement on the
  If not, the usual depilation is enough. This choice of optimization
  is distinct from the validity of the program.
- A local structure can be transferred to the parent with `<-`, comme
  a local painting. `T`, for example `Point`. Data
  stack reserves its location in the beach of the parent according to the
  draft 03. Loans and dependencies remain verified at
  Every border.
- Programmer chooses a pool by writing `pool<T>(n)` then
  `pool.new(...)`. The pool remains in its creation scope. A function
  who allocates in this pool receives it in `&mut Pool<T>`. The generic type
  `Allocator` and custom allocators are removed from this API.
- `pool.new(...)` produit un `A<T>`. The allowance shall keep its address
  and its source when transferring.
  after destruction, the slot can be reused even if it is
  For a pool typed with a narrow, exhaustion stops the
  program with a diagnosis.
- `ref()` and `mut_ref()` borrow the handle `A<T>`. `vref()` and
  `mut_vref()` borrow the content `T`. Borrowing allocation
  mutable modified content `T` In place. These four methods form
  The borrowing API retained for `A<T>`.
- For a `Vector<T>` local, the descriptor of fixed size lives on the
  data stack. It contains a reference to the growing data,
  The vector has no field
  `capacity`. L’annotation `stack_region` sets the maximum size
  of each region via `max_size` and can reserve a number
  d’emplacements via `count`. The descriptor and management metadata
  stored elsewhere occupy their own spaces.

## Cas admis

<a id="transférer-une-structure-locale-et-consommer-une-liaison-locale"></a>

### Transfer local structure and use local connection

```rust
struct Point {
    x: Int,
    y: Int,
}

fn creer_local() -> <- Point {
    let point = Point { x: 10, y: 20 };
    return <- point;
}

fn main() {
    let point = creer_local();
    print(point.x);

    let tampon = [0; 4096];
    print(tampon[0]);
    drop(-> tampon);

    let suivant = [1; 4096];
    print(suivant[0]);
}
```

`drop` ends the life of `tampon` even if its value is copyable.
The compiler decides on the placement of `suivant`.

<a id="injecter-un-pool-typé-et-réutiliser-un-slot-intérieur"></a>

### Inject a typed pool and reuse an indoor slot

```rust
struct Point {
    x: Int,
    y: Int,
}

fn creer(points: &mut Pool<Point>, x: Int) -> <- A<Point> {
    let point = points.new(x: x, y: 20);
    return <- point;
}

fn main() {
    let mut points = pool<Point>(2);
    let a = creer(&mut points, 10);
    let b = creer(&mut points, 30);

    drop(-> a);
    let c = creer(&mut points, 50);

    print(b.x);
    print(c.x);
    drop(-> c);
    drop(-> b);
}
```

The pool stays in `main`. The slot rendered by `a` peut accueillir
`c` pendant que `b` Stay alive.

<a id="cas-refusés"></a>

## Cases rejected

| Cas | Motif |
| --- | --- |
| `let mut memoire = stack(1024);` | The data stack is managed by the compiler and does not have a public constructor. |
| A signature with `&mut Allocator`. | The explicit passage of a source uses a typed pool. |
| `pool<Point>()` comme constructeur public. | The form without capacity has been ruled out. |
| `let autre = <- points;` or a return that transfers the pool itself. | The pool stays in its creative scope and goes by borrowing. |
| Faire retourner `creer_local` with the type `-> <- A<Point>`. | Un `Point` local transferred retains its type and does not acquire pool origin. |
| Retourner un `A<Point>` created in a local pool at the function. | The pool would be closed before the recipient finished the allowance. |
| Lire `tampon[0]` after `drop(-> tampon)`. | The transfer to `drop` consumes the connection. |

Request a third allocation from the pool of two slots before destroying
`a` ou `b` is a case of exhaustion.
diagnostic selon E1.

<a id="règles-à-mettre-à-jour-lors-de-lintégration"></a>

## Rules to be updated when integrating

- **I2, V1 and T6.** Describe the implicit data stack, the explicit choice
  and returns of local structures with `<-`. Conserver
  D1 life-span constraints.
- **L6, L7, P3 and P4.** Include explicit consumption of a value
  local. Distinguish destruction, recovery of a data suffix
  stack and re-use of a pool slot.
- **A1–A4, A6 and P8.** Describe signatures `&mut Pool<T>`, the
  source of allowances and the life of the pool in its scope.
  Migrating historical passages that expose `Allocator`, `stack(...)`
  ou `new(source)`.
- **H2.** Maintaining the distinction between debt from the handle and debt
  content. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md)
- **G1, G5-G7 and G10, GR1-GR2 and TX21.** Distinguish the location of the
  descriptor of the growing data and clarify the scope
  the region boundary. Linking this precision to stability
  d) address and removal of draft 03.
- **AS7 and MT7.** Align references to the source of the regular data
  with the data stack implicit. For async states, apply the
  generation and dimensioning recorded in draft 04.

[LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md) ·
[GROWING_REGIONS.md](../docs/GROWING_REGIONS.md) ·
[FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md) ·
[ASYNC_MULTITHREAD_RULES.md](../docs/ASYNC_MULTITHREAD_RULES.md)

Examples of design examined on paper.
