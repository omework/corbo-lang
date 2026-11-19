[Français](G11_DATASTACK_BENCHMARK-fr.md)

<a id="g11--coûts-de-la-datastack-et-des-régions"></a>

# G11 — Costs of the datatack and the regions

The following numbers precede the addition of the P1 guard page.
runtime now adds a `mprotect` when booking each
The benches remain executable with this runtime.

The [bank C]](../benchmarks/datastack.c) includes both files of the runtime used
by the backend Rust. It compares a classic datastack and a band of regions
In each pair, the two modes reserve 256 Mio for the
data, use the same spacing and write one byte per page on the
First Mio of each active location. The band reserves in addition its
metadata. Reuse cycles verify the identity of addresses.
The hole measurement fills all slots, returns the penultimate and takes it back,
keeping the last one busy.

Measures of 12 November 2026 on macOS 26.6.2 arm64, Homebrew Clang 20.1.3.
16 Kio pages. Median of 25 processes by mode and configuration, with
The time of the
cycle is divided by the number of active locations. Unused capacity
in the active regions `actifs × (taille − 1 Mio)` for this charge.

| Taille × actifs | Unused capacity | Fixed reservation / regions (μs) | First fixed access / regions (μs) | Fixed Reaccess / Regions (μs) | Fixed cycle / regions (ns by location) | Recapture of hole (ns) |
|---|---:|---:|---:|---:|---:|---:|
| 4 Mio × 8 | 24 Mio | 1,46 / 2,50 | 382 / 398 | 2,04 / 2,21 | 1,46 / 2,42 | 16,48 |
| 16 Mio × 8 | 120 Mio | 1,33 / 2,42 | 388 / 389 | 2,00 / 2,04 | 1,43 / 2,46 | 5,65 |
| 16 Mio × 16 | 240 Mio | 1,42 / 2,50 | 793 / 767 | 4,29 / 4,58 | 1,42 / 2,31 | 5,55 |
| 64 Mio × 4 | 252 Mio | 1,33 / 2,38 | 185 / 186 | 0,83 / 0,88 | 1,50 / 2,52 | 2,17 |

The classic datastack makes a `mmap`In the RSS media
The reservation adds 16 and 32 Kio respectively.
access adds exactly the volume affected to RSS media after booking
The backup keeps this RSS.
The reaccess has zero faults in the median. The final disassembly calls
one and two respectively `munmap`. The medians range from 64 to 202 μs for the
classic datastack and 71 to 208 μs for the band.

The group return in the band, which includes the restitution of each slot and
the restoration of the cursor, measures 83 to 166 ns in median. Writing alone
the classic cursor is at the resolution of the chronometer.
a hole recovery includes the linear scanning of the current index.
is that of the process and includes the noise of the instrumentation pages.
The bench is working on a single thread and a persistent band.
cleaning of objects, closed strips by way of telescope output and cost of
The medians are not enough to cover the entire programme.
to establish an overall performance gain.

## Reproduction

```sh
clang -std=c11 -O2 -Wall -Wextra -Werror benchmarks/datastack.c -o /tmp/crust-datastack
for args in '4 8' '16 8' '16 16' '64 4'; do
    set -- $args
    for i in $(seq 1 25); do
        if [ $((i % 2)) -eq 1 ]; then
            modes='fixed regions'
        else
            modes='regions fixed'
        fi
        for mode in $modes; do
            /tmp/crust-datastack "$mode" "$@"
        done
    done
done
```

CSV columns in order. Mode, size (Mio), active, page size,
capacity, bytes covered by writings, mmap, munmap, booking time,
duration of first access, defects in first access, duration of the withdrawal, duration of the
reaccess, cycle duration per location, reaccess defects, duration of the
disassembly, RSS variations after reservation, first access, back and disassembly,
time of return and recovery of a hole. Durations are ns and RSS
In bytes. RSS columns are available on macOS.

Both modes also executed the 16 Mio × 8 configuration with
`-O1 -g -fsanitize=undefined -fno-sanitize-recover=all` without diagnosis.
This measure covers the runtime directly called. The compiler and the
investment rules do not change.

<a id="contention-du-mutex-des-régions"></a>

## Regional mutex restraint

Measures of 13 November 2026 on macOS 26.6.2 arm64, Homebrew Clang 20.1.3.
`-O2 -pthread`. The [banking]](../benchmarks/datastack_contention.c) uses the same
runtime with `CRUST_HAS_THREADS` and `CRUST_LOCAL _Thread_local`. Chaque
thread prepares its own band of eight regions of 1 Mio before departure.
The regional management mutex is global in the process.

Each thread runs 500,000 cycles. A cycle takes and then returns a region,
with two mutex acquisitions and a re-use verification of the
The chronometer covers the same address. No byte of the regions is written.
first start at the last loop completion. The creation of threads,
The tape reservation and disassembly are off timer.

| Threads | Median time (ms) | Median total flow (million cycles/s) | Min–max flow |
|---:|---:|---:|---:|
| 1 | 3,87 | 129,10 | 50,56–130,07 |
| 2 | 13,85 | 72,20 | 40,24–76,25 |
| 4 | 81,27 | 24,61 | 16,80–31,20 |
| 8 | 106,60 | 37,52 | 37,02–38,03 |

Eleven processes per configuration, with alternating order. At eight threads, the
The total flow rate is 29% of that of the thread alone.
and eight threads are specific to this series. The dynamometer measures the flow rate of the
loop and does not time the wait in each acquisition of the mutex.
The order and topology of hearts have not been isolated.
describe tight loop requests and do not predict the flow of a
programme Corbo complet.

```sh
clang -std=c11 -O2 -Wall -Wextra -Werror -pthread benchmarks/datastack_contention.c -o /tmp/crust-contention
for trial in $(seq 1 11); do
    if [ $((trial % 2)) -eq 1 ]; then
        set -- 1 2 4 8
    else
        set -- 8 4 2 1
    fi
    for workers do
        /tmp/crust-contention "$workers"
    done
done
```

Each CSV line gives the number of threads, the number of cycles per thread
and duration in nanoseconds. An eight threads run with
`-O1 -g -fsanitize=undefined -fno-sanitize-recover=all -pthread` has completed
without diagnosis.

<a id="mutex-par-datastack-à-régions"></a>

## Mutex by datastack to regions

Comparison of November 13, 2026 with the same bench, on the same machine.
Fifteen pairs per configuration, alternating the order of the two executables.
The table shows the series performed after the end of the regressions of the backend.
The charge remains at 500,000 take and refund per thread.

| Threads | Global mutex, median [min–max] | Mutex per datatack, median [min–max] | Median ratio |
|---:|---:|---:|---:|
| 1 | 123,79 [114,03–127,39] | 128,01 [118,76–129,27] | 1,03× |
| 2 | 71,08 [57,35–76,16] | 243,96 [228,26–254,58] | 3,43× |
| 4 | 18,83 [13,69–30,44] | 458,61 [456,00–459,35] | 24,36× |
| 8 | 37,68 [37,41–38,62] | 742,53 [734,21–914,70] | 19,71× |

Flow rates are in millions of cycles per second for all threads.
At one thread, the beaches overlap. The multi-thread gain concerns
separate datastacks. Operations on a single datastack share
The bench measures a flow rate and does not measure time
The following are the main features of the application:

To reproduce the comparison, compile the same bench twice with the
above control. For the global tell-tale, use
`rust_frontend/src/region_storage.c` of the commit `7e45ced` in a copy
of the tree containing the dynamometer and `datastack.c`. Alternate both
binary 15 times for each number of threads 1, 2, 4 and 8.

The open datastack remains alive via its scope or working context.
After closing, each living slot keeps her alive until she
The closure and the last refund decide under mutex
which destroys the datastack, then releases the mutex before destroying it.

The six C validation suites of the backend Rust move to `-O0` and `-O2`
UBSan. The eight threads bench and a direct indicator of 2,000 closures
competitors with restitution from another thread also pass under
UBSan. The combined ASan/UBSan run of the bench was interrupted without result.


### Suivi ASan

Compilation with `-fsanitize=address,undefined` succeeds with Homebrew
Clang and Apple Clang. Runtime exceeds time without output. Blockage
The two compilers are reproduced on a C-reduced program
`int main(void) { puts("main"); }` (with `<stdio.h>`), without Corbo code.
The Homebrew bench at 1, 2, 4 and 8 threads exceeds eight seconds per test.
At eight threads, it also exceeds 12 seconds outside sandbox.
The leak detection did not complete the two test of the dynamometer.
The precise cause remains unknown. ASan remains to be executed on an environment
where the minimum tell-tale starts. UBSan results remain those recorded
ci-dessus.

<a id="restitution-de-pages-après-recul"></a>

## Pages returned after hindsight

Measures on macOS 26.6.2 arm64 after the addition of the guard.
[datastack_reclaim.c](../benchmarks/datastack_reclaim.c) uses runtime
Each test is 1, 8 and 64 Mio, with a similar allocation.
alive, then recovers a suffix of entire pages.
The bank checks that the neighbouring allowance is kept
the content and the next peak re-uses the same addresses.
combination of datastack and policy is executed in 51 processes,
with mixed order (grain 11). Rewriting immediately follows the
residence measure, without artificial memory pressure.

| Datastack to regions | 1 Mio · call / rewrite (μs) | 8 Mio · call / rewrite (μs) | 64 Mio · call / rewrite (μs) |
|---|---:|---:|---:|
| Conservation | — / 0,04 | — / 1,96 | — / 17,29 |
| MADV_DONTNEED | 5,00 / 22,17 | 20,71 / 166,42 | 181,83 / 1 427,29 |
| MADV_FREE_REUSABLE then MADV_FREE_REUSE | 6,04 / 15,67 | 23,88 / 94,46 | 204,96 / 813,67 |
| Anonymous repackaging at the same address | 2,46 / 38,75 | 13,25 / 314,50 | 102,33 / 2 397,75 |
| Repackaging at the threshold of 16 Mio | — / 0,04 | — / 1,96 | 102,12 / 2 417,00 |

Median. The call timer excludes the slider's back and the
memory records. Rewrite includes `MADV_FREE_REUSE` in mode
At 64 Mio, the p90 of the remapping is 123.08 μs and the p90 of the remapping is 123.08 μs.
At 8 Mio these p90 are 15.29 and 348.62 μs.

In the two datastacks, `MADV_DONTNEED` leaves RSS, physical fingerprint
The mean value of the area recorded and the residence of the range was unchanged.
`MADV_FREE_REUSABLE` keeps the RSS and removes from the recorded footprint
the marked volume reusable. The remapping makes pass the residence of the
range to zero and reduce RSS to the corresponding volume. Next access
causes 64, 512 and 4,096 page defects after retreading, respectively,
against zero in the middle for other modes. On the classic datastack,
The medians of remapping are 2.67 / 13.17 / 101.67 μs and rewriting
38,88 / 309,29 / 2 389,71 μs for the same sizes.

Reproduction on macOS with the compilation command at the head of the bench.
Launch binary with a policy among `keep whose valuable remap
threshold` et un type parmi `The CSV sets out the measures by
size in bytes and nanoseconds. This bench measures contiguous suffixes
aligned on pages on a single thread. Memory pressure, restraint
and scattered holes remain out of measure. The threshold of 16 Mio is
an experimental adjustment of the bench.

<a id="trous-dispersés-charge-mémoire-et-appels-parallèles"></a>

### Dispersed holes, memory load and parallel calls

Complementary series on the same Mac, with 31 performances per configuration
and mixed order (grain 11). `regions`, `scattered` and
`pressure` The five policies above are taken up. `scattered`,
eight free regions alternate with eight living regions.
page is identical to the contiguous mode. The bench checks the eight pages
sentinels after rewriting and checking reassigned addresses.

| Pages rendues | Contiguous, median repackaging | Eight scattered remappings, median | Contiguous / dispersed rewriting |
|---:|---:|---:|---:|
| 1 Mio | 2,75 µs | 10,21 µs | 39,75 / 36,33 µs |
| 8 Mio | 13,21 µs | 17,33 µs | 318,54 / 321,12 µs |
| 64 Mio | 105,79 µs | 107,54 µs | 2 719,92 / 2 701,79 µs |

Remapping reduces the median residence of free pages in the
The differences in rewriting between provisions are small.
in this series.

In mode `pressure`, the process touches and preserves **256 Mio** additional
between restitution and residence, until the end of the rewriting.
At 64 Mio, the pages retained, recommended by MADV_DONTNEED or marked
Reusables remain resident in the median.
0.49 ms, 1.90 ms and 1.12 ms respectively, with zero median defect.
The remapping gives a zero residence, 4,096 defects and 2.44 ms of
rewriting. The extra load did not establish a regime of eviction
No conclusions on compression, swap or pressure
severe memory.

Mode `parallel` allocates to each thread a disjunct region of 8 Mio
in the same datastack. All start together and run 64 cycles of
touch and then retread. Calls are made directly to the kernel.
aggregate time covers the loop and join, after creating threads.
Latency per thread is the average of its 64 calls.
the median and p90 of these averages over 31 processes.

| Threads | Call by thread, median / p90 | Aggregate flow rate, cycles/s |
|---:|---:|---:|
| 1 | 37,28 / 39,16 µs | 3 052 |
| 2 | 41,86 / 45,13 µs | 5 437 |
| 4 | 49,27 / 54,13 µs | 8 554 |
| 8 | 70,22 / 75,92 µs | 9 980 |

Flow includes page defects at the next cycle and competition
The bench does not isolate the internal locking of the core.
There is no return policy integrated into the running to this extent.

To reproduce, compile with the control at the head of the bench, then pass
a policy and fashion, for example `/tmp/crust-reclaim remap scattered`
ou `/tmp/crust-reclaim reusable pressure`. The columns of residence and
The RSS and fingerprint are recorded.
prior to the additional charge allowance, and the beach residence
later. For the parallel series, launch `/tmp/crust-reclaim parallel 8`
and repeat for 1, 2, 4 and 8 threads. Durations are in nanoseconds.

<a id="restitution-intégrée-sur-un-programme-crust"></a>

### Integrated return on a Corbo programme

Program run on macOS arm64, C compiled to `-O2`. Il initialise un
8 Mio table by iteration, reads its last element and prints 300.
The measures cover the entire process, including start-up.
execution by mode, in mixed order (grain 11).

```rust
#(datastack:size=64M)
fn main(){
    let mut n:i64=0;
    while n<300 {
        let data:[i64;1048576]=[7;1048576];
        n=n+data[1048575]-6;
    }
    print(n);
}
```

| Politique | Median | p90 |
|---|---:|---:|
| Conservation | 20,95 ms | 21,92 ms |
| 4 Mio threshold | 108,83 ms | 142,74 ms |
| `#(free_pages)` on the body of the buckle | 107,64 ms | 118,48 ms |

To reproduce, add `reclaim_threshold=4M` with overall annotation
ou placer `#(free_pages)` before the buckle body clasps,
then compile each variant with `corbo-frontend emit-c` and
`cc -O2 -std=c11`. A separate series with a threshold of 8 Mio a
measured 20.65 ms in median. The beginning of the temporary range is not
aligned on a page. The inner rounding of the suffix leaves less
This scenario requires classical and
Reuse space immediately, at each iteration.
