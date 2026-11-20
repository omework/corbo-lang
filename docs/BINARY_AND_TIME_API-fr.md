[English](BINARY_AND_TIME_API.md)

# Encodage binaire et temps monotone

Ces API de STD utilisent les mécanismes existants. Elles n'ajoutent pas de
règle du core. La [référence générée](STDLIB.md) décrit leurs symboles et le
[rapport](cycles/BINARY_TIME_BOUNDED_CYCLE.md) précise la portée des validations.

## `std::encoding::binary`

Les méthodes `read_TYPE_le/be` et `write_TYPE_le/be` rendent l'ordre des octets
explicite, indépendamment de l'hôte : `u16`, `u32`, `u64`, `i32`, `i64`, `f32`,
`f64`. `u8` et `bool` utilisent `read_u8`, `write_u8`, `read_bool`, `write_bool`.
Des variantes `usize_le/be` sont disponibles sur les cibles 64 bits ; préférer
les largeurs fixes pour les formats disque/réseau.

Une lecture prend `&[u8]` et renvoie `Result<T, Error>`. Une écriture prend une
valeur et `&mut [u8]`, puis renvoie `Result<usize, Error>` (octets écrits).
Seul le préfixe requis est utilisé. `BufferTooSmall` signale un tampon trop
court ; une écriture trop courte ne modifie pas sa sortie. Les booléens utilisent
0/1, toute autre valeur donne `InvalidBoolean`. Entiers signés : complément à
deux ; flottants : représentation IEEE-754, sans conversion numérique.

Aucune allocation de sortie cachée. La sérialisation de structs est distincte :
le padding et le layout natifs ne constituent pas implicitement un format disque.

## Valeurs communes — `std::time`

`Duration::from_nanos`, `from_millis` et `from_secs` prennent des `u64` ;
`as_nanos(&self)` renvoie la durée en nanosecondes. Les débordements suivent
l'arithmétique contrôlée existante. Ces objets suivent les moves ordinaires.

`Instant::now() -> Result<Instant, Error>` lit une horloge monotone ;
`after(duration)` produit une échéance et `elapsed()` renvoie une durée via
`Result`. Il ne s'agit ni d'une date ni d'un timestamp portable.

## Attentes bloquantes — `std::time::sync`

`Timer::after(duration)` renvoie `Result<Timer, Error>` ; `Timer::at(instant)`
construit une échéance absolue. `wait(&self) -> Result<(), Error>` bloque le
thread et est réutilisable. `sleep(duration)` est la fonction de commodité.
Les interruptions/réveils précoces entraînent une nouvelle vérification de
l'échéance. Les attentes natives sont découpées en blocs de soixante secondes.

Les backends utilisent `@asm` : CLOCK_MONOTONIC/nanosleep sous Linux/macOS,
QueryPerformanceCounter/Frequency et Sleep sous Windows. La conversion
fractionnaire évite un produit 64 bits débordant ; durées et instants doivent
toujours tenir en nanosecondes `u64`. Les erreurs sont `ClockFailure`,
`WaitFailure` et `LaunchFailed` pour la création d'un worker async.

## Attentes async — `std::time`

`sleep(duration)` et `Timer::wait(&self)` sont async et renvoient
`Result<(), std::time::Error>`. Les constructeurs `after` et `at` conservent le
sens de la variante bloquante. L'appelant est suspendu, sans bloquer un poller.
L'implémentation initiale utilise `spawn_blocking` : un worker par attente
active, pas un réacteur de timers partagé. Le timer emprunté doit survivre à
l'attente ; les règles usuelles du runtime régissent les erreurs et le nettoyage.

Les dates civiles, calendriers, intervalles périodiques et annulations sont
hors périmètre. Aucune nouvelle primitive ni interface de scheduler ajoutée.
Les exemples complets figurent dans la version anglaise et les fixtures de
validation associées.
