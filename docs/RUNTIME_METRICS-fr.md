[English](RUNTIME_METRICS.md)

# Métriques mémoire du runtime

`runtime::metrics::memory_stats() -> MemoryStats` échantillonne les datastacks
fixes et données de régions gérées par Corbo dans tout le processus. Le paquet est
fourni avec la STD dans `stdlib/src/runtime/metrics/`. Imports et noms qualifiés
utilisent la résolution habituelle. Les accesseurs renvoient des octets en `usize` :

- `reserved()` : plages d’adresses virtuelles réservées, arrondies aux pages,
  des datastacks fixes et bandes de régions ; inclut les pages engagées.
- `committed()` : pages actuellement engagées/accessibles dans ces plages,
  indépendamment de la mémoire physique résidente du processus (RSS).
- `occupied()` : étendue des curseurs fixes, alignement et métadonnées de pools
  compris, moins les slots inutilisés des pools, plus les longueurs des régions
  actives multipliées par la taille de leurs éléments.

```rust
use runtime::metrics::{MemoryStats, memory_stats};

fn main() {
    let stats: MemoryStats = memory_stats();
    print(stats.reserved());
    print(stats.committed());
    print(stats.occupied());
}
```

Les compteurs agrègent les stacks actives ou suspendues de tous les threads et les
bandes partagées. Les changements de contexte ne comptent pas deux fois un curseur
restauré. Croissance, pop/remove, destruction, recul du curseur et restitution des
pages mettent à jour les compteurs. Les lectures ne font aucune allocation, ne
parcourent pas de descripteurs mutables et ne prennent pas de mutex global. Les
mises à jour ajoutent des opérations atomiques aux transitions concernées.

Les champs sont échantillonnés séparément : pendant des mutations concurrentes,
ils peuvent correspondre à des instants voisins. Comparer leurs relations ou
soustraire deux échantillons exige que les workers concernés soient au repos.
La soustraction des trous de pools sature à zéro si un échantillon chevauche une
mise à jour. Ces métriques ne constituent pas une garantie de durée de vie ou de
synchronisation.

Sont exclus les stacks système des threads, registres/locaux C natifs, allocations
étrangères et métadonnées scheduler/réacteur mappées séparément. La mémoire réservée
ou engagée peut subsister après la libération des valeurs. L’API C équivalente est
`corbo_memory_stats() -> CorboMemoryStats`. Le nouveau bookkeeping de pool/contexte
fait passer l’ABI C expérimentale à la version 2 : recompiler les consommateurs C
avec l’en-tête et le runtime correspondants.

Validation ciblée : huit observations Corbo, puis un témoin C ABI identique sur
les implémentations C et Corbo, sous O1/UBSan fatal. Chaque témoin ABI lance trois
workers pour 30 000 cycles claim/release et des lectures concurrentes ; les
compteurs finaux reviennent à zéro. Le témoin API couvre aussi croissance/pop,
fin de scope et suspension async. Il s’exécute sur macOS ARM64/x86-64, Linux
x86-64 et Windows x86-64 sous Wine. Windows ARM64 est compilé seulement.
Aucun benchmark, TSan ou preuve générale de concurrence n’est revendiqué.
Résultats dans `validation/runtime_metrics/`.
