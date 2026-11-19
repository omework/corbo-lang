[English](G11_DATASTACK_BENCHMARK.md)

# G11 — Coûts de la datastack et des régions

Les chiffres ci-dessous précèdent l’ajout de la page de garde P1. Le
runtime ajoute désormais un `mprotect` lors de la réservation de chaque
plage de données. Les bancs restent exécutables avec ce runtime.

Le [banc C](../benchmarks/datastack.c) inclut les deux fichiers du runtime utilisé
par le backend Rust. Il compare une datastack classique et une bande de régions
réutilisable. Dans chaque paire, les deux modes réservent 256 Mio pour les
données, emploient le même espacement et écrivent un octet par page sur le
premier Mio de chaque emplacement actif. La bande réserve en plus ses
métadonnées. Les cycles de réutilisation vérifient l'identité des adresses.
La mesure du trou remplit tous les slots, rend l'avant-dernier et le reprend,
en gardant le dernier occupé.

Mesures du 12 novembre 2026 sur macOS 26.6.2 arm64, Homebrew Clang 20.1.3,
pages de 16 Kio. Médianes de 25 processus par mode et configuration, avec
ordre alterné et 200 000 cycles de réutilisation par processus. Le temps du
cycle est divisé par le nombre d'emplacements actifs. La capacité inutilisée
dans les régions actives vaut `actifs × (taille − 1 Mio)` pour cette charge.

| Taille × actifs | Capacité inutilisée | Réservation fixe / régions (µs) | Premier accès fixe / régions (µs) | Réaccès fixe / régions (µs) | Cycle fixe / régions (ns par emplacement) | Reprise du trou (ns) |
|---|---:|---:|---:|---:|---:|---:|
| 4 Mio × 8 | 24 Mio | 1,46 / 2,50 | 382 / 398 | 2,04 / 2,21 | 1,46 / 2,42 | 16,48 |
| 16 Mio × 8 | 120 Mio | 1,33 / 2,42 | 388 / 389 | 2,00 / 2,04 | 1,43 / 2,46 | 5,65 |
| 16 Mio × 16 | 240 Mio | 1,42 / 2,50 | 793 / 767 | 4,29 / 4,58 | 1,42 / 2,31 | 5,55 |
| 64 Mio × 4 | 252 Mio | 1,33 / 2,38 | 185 / 186 | 0,83 / 0,88 | 1,50 / 2,52 | 2,17 |

La datastack classique fait un `mmap`, la bande deux. Dans les médianes RSS
du processus, la réservation ajoute respectivement 16 et 32 Kio. Le premier
accès ajoute exactement le volume touché aux médianes RSS après réservation
et produit un défaut par page écrite (256 à 1 024). Le recul conserve ce RSS.
Le réaccès présente zéro défaut en médiane. Le démontage final appelle
respectivement un et deux `munmap`. Ses médianes vont de 64 à 202 µs pour la
datastack classique et de 71 à 208 µs pour la bande.

Le retour groupé dans la bande, qui inclut la restitution de chaque slot et
la restauration du curseur, mesure 83 à 166 ns en médiane. L'écriture seule
du curseur classique se situe à la résolution du chronomètre. Le coût de
reprise d'un trou inclut le balayage linéaire de l'index actuel. La mesure RSS
est celle du processus et comprend le bruit des pages de l'instrumentation.
Le banc travaille sur un seul thread et une bande persistante. La contention,
le nettoyage des objets, les bandes fermées par sortie de scope et le coût de
programmes entiers restent hors de cette mesure. Les médianes ne suffisent pas
à établir un gain de performance global.

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

Colonnes CSV dans l'ordre. Mode, taille (Mio), actifs, taille de page,
capacité, octets couverts par les écritures, mmap, munmap, durée de réservation,
durée du premier accès, défauts du premier accès, durée du recul, durée du
réaccès, durée du cycle par emplacement, défauts du réaccès, durée du
démontage, variations RSS après réservation, premier accès, recul et démontage,
durée de restitution et reprise d'un trou. Les durées sont en ns et les RSS
en octets. Les colonnes RSS sont disponibles sur macOS.

Les deux modes ont également exécuté la configuration 16 Mio × 8 avec
`-O1 -g -fsanitize=undefined -fno-sanitize-recover=all` sans diagnostic.
Cette mesure couvre le runtime appelé directement. Le compilateur et les
règles de placement ne changent pas.

## Contention du mutex des régions

Mesures du 13 novembre 2026 sur macOS 26.6.2 arm64, Homebrew Clang 20.1.3,
`-O2 -pthread`. Le [banc](../benchmarks/datastack_contention.c) utilise le même
runtime avec `CRUST_HAS_THREADS` et `CRUST_LOCAL _Thread_local`. Chaque
thread prépare sa propre bande de huit régions de 1 Mio avant le départ.
Le mutex de gestion des régions est global au processus.

Chaque thread exécute 500 000 cycles. Un cycle prend puis rend une région,
avec deux acquisitions du mutex et une vérification de réutilisation de la
même adresse. Aucun octet des régions n'est écrit. Le chronomètre couvre du
premier début au dernier achèvement des boucles. La création des threads,
la réservation des bandes et leur démontage sont hors chronomètre.

| Threads | Temps médian (ms) | Débit total médian (millions de cycles/s) | Min–max du débit |
|---:|---:|---:|---:|
| 1 | 3,87 | 129,10 | 50,56–130,07 |
| 2 | 13,85 | 72,20 | 40,24–76,25 |
| 4 | 81,27 | 24,61 | 16,80–31,20 |
| 8 | 106,60 | 37,52 | 37,02–38,03 |

Onze processus par configuration, avec ordre alterné. À huit threads, le
débit total atteint 29 % de celui du thread seul. La remontée entre quatre
et huit threads est propre à cette série. Le banc mesure le débit de la
boucle et ne chronomètre pas l'attente dans chaque acquisition du mutex.
L'ordonnancement et la topologie des cœurs n'ont pas été isolés. Les chiffres
décrivent des demandes en boucle serrée et ne prédisent pas le débit d'un
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

Chaque ligne CSV donne le nombre de threads, le nombre de cycles par thread
et la durée en nanosecondes. Une exécution à huit threads avec
`-O1 -g -fsanitize=undefined -fno-sanitize-recover=all -pthread` a terminé
sans diagnostic.

## Mutex par datastack à régions

Comparaison du 13 novembre 2026 avec le même banc, sur la même machine.
Quinze paires par configuration, en alternant l'ordre des deux exécutables.
Le tableau reprend la série exécutée après la fin des régressions du backend.
La charge reste à 500 000 prises et restitutions par thread.

| Threads | Mutex global, médiane [min–max] | Mutex par datastack, médiane [min–max] | Rapport des médianes |
|---:|---:|---:|---:|
| 1 | 123,79 [114,03–127,39] | 128,01 [118,76–129,27] | 1,03× |
| 2 | 71,08 [57,35–76,16] | 243,96 [228,26–254,58] | 3,43× |
| 4 | 18,83 [13,69–30,44] | 458,61 [456,00–459,35] | 24,36× |
| 8 | 37,68 [37,41–38,62] | 742,53 [734,21–914,70] | 19,71× |

Les débits sont en millions de cycles par seconde pour l'ensemble des threads.
À un thread, les plages se recouvrent. Le gain à plusieurs threads concerne
des datastacks distinctes. Les opérations sur une même datastack partagent
toujours son mutex. Le banc mesure un débit et ne mesure pas le temps
d'attente individuel ni le débit d'une application.

Pour reproduire le comparatif, compiler le même banc deux fois avec la
commande ci-dessus. Pour le témoin global, utiliser
`rust_frontend/src/region_storage.c` du commit `7e45ced` dans une copie
de l'arborescence contenant le banc et `datastack.c`. Alterner les deux
binaires 15 fois pour chacun des nombres de threads 1, 2, 4 et 8.

La datastack ouverte reste vivante via son scope ou son contexte de travail.
Après fermeture, chaque slot vivant la maintient en vie jusqu'à sa
restitution. La fermeture et la dernière restitution décident sous mutex
qui détruit la datastack, puis libèrent le mutex avant de le détruire.

Les six suites de validation C du backend Rust passent à `-O0` et `-O2`
sous UBSan. Le banc à huit threads et un témoin direct de 2 000 fermetures
concurrentes avec restitution depuis un autre thread passent également sous
UBSan. L'exécution combinée ASan/UBSan du banc a été interrompue sans résultat.


### Suivi ASan

La compilation avec `-fsanitize=address,undefined` réussit avec Homebrew
Clang et Apple Clang. L'exécution dépasse le délai sans sortie. Le blocage
se reproduit avec les deux compilateurs sur un programme C réduit à
`int main(void) { puts("main"); }` (avec `<stdio.h>`), sans code Corbo.
Le banc Homebrew à 1, 2, 4 et 8 threads dépasse huit secondes par essai.
À huit threads, il dépasse aussi douze secondes hors sandbox. Désactiver
la détection de fuites n'a pas permis de terminer les deux essais du banc.
La cause précise reste inconnue. ASan reste à exécuter sur un environnement
où le témoin minimal démarre. Les résultats UBSan restent ceux consignés
ci-dessus.

## Restitution de pages après recul

Mesures sur macOS 26.6.2 arm64 après l'ajout de la garde. Le banc
[datastack_reclaim.c](../benchmarks/datastack_reclaim.c) utilise le runtime
courant. Chaque essai touche 1, 8 et 64 Mio, avec une allocation voisine
vivante, puis récupère un suffixe de pages entières. La datastack à régions
rend huit régions contiguës. Le banc vérifie que l'allocation voisine garde
son contenu et que le prochain pic réutilise les mêmes adresses. Chaque
combinaison de datastack et de politique est exécutée dans 51 processus,
avec un ordre mélangé (graine 11). La réécriture suit immédiatement la
mesure de résidence, sans pression mémoire artificielle.

| Datastack à régions | 1 Mio · appel / réécriture (µs) | 8 Mio · appel / réécriture (µs) | 64 Mio · appel / réécriture (µs) |
|---|---:|---:|---:|
| Conservation | — / 0,04 | — / 1,96 | — / 17,29 |
| MADV_DONTNEED | 5,00 / 22,17 | 20,71 / 166,42 | 181,83 / 1 427,29 |
| MADV_FREE_REUSABLE puis MADV_FREE_REUSE | 6,04 / 15,67 | 23,88 / 94,46 | 204,96 / 813,67 |
| Remappage anonyme à la même adresse | 2,46 / 38,75 | 13,25 / 314,50 | 102,33 / 2 397,75 |
| Remappage au seuil de 16 Mio | — / 0,04 | — / 1,96 | 102,12 / 2 417,00 |

Médianes. Le chronomètre de l'appel exclut le recul du curseur et les
relevés mémoire. La réécriture inclut `MADV_FREE_REUSE` dans le mode
reusable. À 64 Mio, le p90 du remappage est 123,08 µs et celui de la
réécriture 2 735,67 µs. À 8 Mio ces p90 sont 15,29 et 348,62 µs.

Dans les deux datastacks, `MADV_DONTNEED` laisse le RSS, l'empreinte physique
comptabilisée et la résidence de la plage inchangés en médiane.
`MADV_FREE_REUSABLE` conserve le RSS et retire de l'empreinte comptabilisée
le volume marqué réutilisable. Le remappage fait passer la résidence de la
plage à zéro et réduit le RSS du volume correspondant. Le prochain accès
provoque respectivement 64, 512 et 4 096 défauts de page après remappage,
contre zéro en médiane pour les autres modes. Sur la datastack classique,
les médianes de remappage sont 2,67 / 13,17 / 101,67 µs et les réécritures
38,88 / 309,29 / 2 389,71 µs pour les mêmes tailles.

Reproduction sur macOS avec la commande de compilation en tête du banc.
Lancer le binaire avec une politique parmi `keep dontneed reusable remap
threshold` et un type parmi `fixed regions`. Le CSV expose les mesures par
taille en octets et nanosecondes. Ce banc mesure des suffixes contigus
alignés sur les pages sur un seul thread. La pression mémoire, la contention
et les trous dispersés restent hors de la mesure. Le seuil de 16 Mio est
un réglage expérimental du banc.

### Trous dispersés, charge mémoire et appels parallèles

Série complémentaire sur le même Mac, avec 31 exécutions par configuration
et ordre mélangé (graine 11). Les modes `regions`, `scattered` et
`pressure` reprennent les cinq politiques ci-dessus. En mode `scattered`,
huit régions libres alternent avec huit régions vivantes. Le volume de
pages rendues est identique au mode contigu. Le banc vérifie les huit
sentinelles après la réécriture et contrôle les adresses réattribuées.

| Pages rendues | Remappage contigu, médiane | Huit remappages dispersés, médiane | Réécriture contiguë / dispersée |
|---:|---:|---:|---:|
| 1 Mio | 2,75 µs | 10,21 µs | 39,75 / 36,33 µs |
| 8 Mio | 13,21 µs | 17,33 µs | 318,54 / 321,12 µs |
| 64 Mio | 105,79 µs | 107,54 µs | 2 719,92 / 2 701,79 µs |

Le remappage réduit à zéro la résidence médiane des pages libres dans les
deux dispositions. Les écarts de réécriture entre dispositions sont faibles
dans cette série.

En mode `pressure`, le processus touche et conserve **256 Mio** supplémentaires
entre la restitution et la mesure de résidence, jusqu'à la fin de la réécriture.
À 64 Mio, les pages conservées, conseillées par MADV_DONTNEED ou marquées
réutilisables restent résidentes en médiane. Les médianes de réécriture sont
respectivement 0,49 ms, 1,90 ms et 1,12 ms, avec zéro défaut en médiane.
Le remappage donne une résidence nulle, 4 096 défauts et 2,44 ms de
réécriture. La charge supplémentaire n'a pas établi un régime d'éviction
système. Aucune conclusion sur la compression, le swap ou la pression
mémoire sévère.

Le mode `parallel` attribue à chaque thread une région disjointe de 8 Mio
dans la même datastack. Tous démarrent ensemble et exécutent 64 cycles de
touch puis de remappage. Les appels se font directement au noyau. Le
temps agrégé couvre la boucle et le join, après création des threads.
La latence par thread est la moyenne de ses 64 appels. Le tableau donne
la médiane et le p90 de ces moyennes sur 31 processus.

| Threads | Appel par thread, médiane / p90 | Débit agrégé, cycles/s |
|---:|---:|---:|
| 1 | 37,28 / 39,16 µs | 3 052 |
| 2 | 41,86 / 45,13 µs | 5 437 |
| 4 | 49,27 / 54,13 µs | 8 554 |
| 8 | 70,22 / 75,92 µs | 9 980 |

Le débit inclut les défauts de page au cycle suivant et la concurrence
sur la VM. Le banc n'isole pas le verrouillage interne du noyau.
Il n'y a pas de politique de restitution intégrée au runtime dans cette mesure.

Pour reproduire, compiler avec la commande en tête du banc, puis passer
une politique et un mode, par exemple `/tmp/crust-reclaim remap scattered`
ou `/tmp/crust-reclaim reusable pressure`. Les colonnes de résidence et
d'empreinte sont exprimées en octets. Le RSS et l'empreinte sont relevés
avant l'allocation de charge supplémentaire, et la résidence de la plage
après. Pour la série parallèle, lancer `/tmp/crust-reclaim parallel 8`
et répéter pour 1, 2, 4 et 8 threads. Les durées sont en nanosecondes.

### Restitution intégrée sur un programme Corbo

Programme exécuté sur macOS arm64, C compilé à `-O2`. Il initialise un
tableau de 8 Mio par itération, lit son dernier élément et imprime 300.
Les mesures portent sur le processus entier, démarrage inclus. Quinze
exécutions par mode, en ordre mélangé (graine 11).

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

| Politique | Médiane | p90 |
|---|---:|---:|
| Conservation | 20,95 ms | 21,92 ms |
| Seuil de 4 Mio | 108,83 ms | 142,74 ms |
| `#(free_pages)` sur le corps de la boucle | 107,64 ms | 118,48 ms |

Pour reproduire, ajouter `reclaim_threshold=4M` à l’annotation globale
ou placer `#(free_pages)` avant les accolades du corps de boucle,
puis compiler chaque variante avec `corbo-frontend emit-c` et
`cc -O2 -std=c11`. Une série séparée avec un seuil de 8 Mio a
mesuré 20,65 ms en médiane. Le début de la plage temporaire n’est pas
aligné sur une page. L'arrondi intérieur du suffixe laisse donc moins
de 8 Mio éligibles. Ce scénario sollicite la datastack classique et
réutilise l’espace aussitôt, à chaque itération.
