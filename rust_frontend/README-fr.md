[English](README.md)

# Frontend Rust de Corbo

Le crate expose `frontend(source, mode)`. Il produit les tokens avec
leurs positions en octets, un arbre syntaxique indexé et un arbre
statique avec scopes, liaisons et points d’exécution. Les faits
structurés comprennent les usages, déplacements nommés, captures,
emprunts, pools, projections, appels, écritures et sorties.
Les types, provenances et effets qui demandent une résolution
sémantique sont établis par une passe séparée. Le crate utilise la
bibliothèque standard de Rust. Les modes `program`, `block` et
`signature` s’arrêtent à l’arbre.

Depuis la racine du dépôt, compiler puis afficher un arbre.

```sh
CARGO_TARGET_DIR=build/rust_frontend cargo build --offline --manifest-path rust_frontend/Cargo.toml
printf '%s\n' 'fn main() { print(7); }' | build/rust_frontend/debug/corbo-frontend program
```

Les modes `block` et `signature` lisent des fragments autonomes.
Le mode `--batch` sert à la comparaison avec le corpus.

```sh
python3 validation/build_representation_corpus.py
python3 validation/compare_rust_frontend.py
```

Le comparateur produit `build/rust_frontend_comparison.jsonl`.
Il compare la suite des lexèmes normalisés, les parents et lignes
d’entrée des scopes, les noms des liaisons locales dans leur ordre,
les comptes d’emprunts, de pools, d’adresses candidates et de
déplacements nommés, ainsi que les liens de ces déplacements.
Voir le [rapport de cycle](../docs/cycles/CORE_COMPOSITION_CYCLE.md#frontend-rust-et-comparaison-du-corpus)
pour les écarts et limites de cette comparaison.

## Vérification et génération C

`check` vérifie le sous-ensemble pris en charge.
`emit-c` applique le même vérificateur avant d’émettre le C sur
la sortie standard. Le générateur reçoit un `VerifiedProgram`.

```sh
build/rust_frontend/debug/corbo-frontend check < programme.crb
build/rust_frontend/debug/corbo-frontend emit-c < programme.crb > programme.c
cc -std=c11 -pthread programme.c -lm -o programme
```

Le périmètre actuel couvre `bool`, `i32`, `i64`, `u8`, `u16`, `u32`,
`u64`, `f32`, `f64` et leurs références
dans les fonctions synchrones. Il comprend les blocs, les branches,
`while`, `loop` avec ou sans résultat, les déplacements et les
réemprunts explicites. Un contrat de retour emprunté conserve les
paramètres de provenance possibles et les substitue à l’appel.
Le C utilise les intrinsics de débordement de Clang ou GCC pour
l’addition, la soustraction et la multiplication. Le graphe de contrôle
suit les usages futurs des références locales à travers les branches,
les sorties et les reprises. Une référence encore utilisée lors d’une
itération suivante garde sa réservation. Les signatures récursives
peuvent utiliser une approximation de leurs provenances.

Pour les agrégats fixes synchrones, l’analyse post-AST suit
les déplacements jusqu’au scope de destination et peut partager un emplacement
entre les bras exclusifs qui alimentent un même receveur. Quand une fonction
construit son résultat, l’appelant fournit des emplacements de sortie typés.
Un relais propage ces emplacements ou conserve l’adresse d’un résultat
transmis depuis un paramètre.

Le plan place aussi les liaisons, paramètres et résultats matérialisés des
primitifs et de leurs références. Les résultats scalaires de
blocs, branches et appels peuvent relayer l’adresse du receveur. Les
temporaires de calcul restent des expressions ou des temporaires C.

Le runtime réserve une plage virtuelle anonyme avec `mmap` au premier
besoin. Une page inaccessible protège la fin de chaque plage de données. Chaque réservation avance un curseur aligné après vérification de
la capacité. Les sorties de bloc, retours, `break` et `continue` restaurent
leur marque. Les emplacements anticipés du receveur sont réservés avant
cette marque et restent accessibles après la restauration.

La propriété facultative `#(datastack: size=...)` fixe la capacité en unités
binaires `K`, `M` ou `G`. Sans elle, le compilateur compose les réservations
post-AST, leurs alignements, les chemins de scope et les appels accessibles
depuis `main`. Le C évalue cette borne au démarrage avec les tailles et
alignements de l’ABI cible. Les appels récursifs accessibles donnent une
borne inconnue. Dans ce cas, le runtime utilise les pages disponibles si
la plateforme les expose par `sysconf`, ou les pages physiques, divisées
par le nombre de CPU en ligne.

`python3 validation/check_rust_datastack_capacity.py` compare la capacité
choisie au maximum observé dans les témoins C.

Les tableaux, enums et structures imbriquées peuvent porter des références.
Le vérificateur suit leur provenance et leur dernier usage par position.
Un contrat relie la position de l’argument à la position du résultat.
Un indice dynamique conserve les provenances de toutes les cases possibles.
Les emprunts directs gardent la réservation de leur racine de stockage.
Un réemprunt d’une référence stockée peut être limité à un champ ou à une
case, y compris à travers un agrégat lui-même emprunté.

Un pool local réserve sa zone entière dans la datastack, avec un curseur
et un registre de slots distincts par variante pour les enums.
`match &allocation` lit le tag et le payload de la variante directement
dans son slot. Un match emprunté lie les champs agrégés par référence,
avec le droit de mutation du receveur du match. Les fonctions reçoivent les pools par emprunt
et peuvent consommer ou retourner des `A<T>`. Un transfert d’`A<T>`
conserve le slot et associe son nettoyage au receveur, sous réserve que
le pool et les dépendances de la valeur survivent.

Pour reproduire les témoins ciblés, exécuter
`python3 validation/check_rust_placement_dependencies.py` après la
construction du frontend. Les contrats récursifs non résolus conservent
toutes les provenances candidates.

Les `Vector<T>` à éléments fixes sans dépendances et les `String` créés
par `pool<T>.new()` placent leur descripteur dans le slot du pool et leur
contenu dans une région distincte. Le transfert de l’allocation conserve
la région et sa limite. Le nettoyage restitue la région avant le slot du
pool. Le frontend prend en charge `push`, `len` et la lecture indexée des
vecteurs ainsi que `push_str` sur un littéral UTF-8 et `byte_len` pour
`String`.

`region_size` et `region_stack_size` priment sur leurs bornes déduites.
Le post-AST compose le pic d'occupation des régions avec les transferts
et les appels. Les bras exclusifs contribuent par leur maximum.
Lorsque la coexistence reste indéterminée, le plan dirige les acquisitions
concernées vers des régions dédiées qui héritent du gabarit courant.
Une croissance non bornée utilise le gabarit de 100 Mio en l'absence
de configuration.

`#(stack_region: max_size=..., count=...)` peut réserver une zone dédiée
héritée par les enfants. Le plan calcule une capacité locale quand
`count` est omis. Si les emplacements de la zone annotée sont occupés,
le runtime peut ouvrir une région dédiée du même gabarit. Le dépassement
du gabarit d'une valeur déclenche le diagnostic de limite.

Les seuils facultatifs `reclaim_threshold` et `region_reclaim_threshold`
activent la restitution automatique des pages libres. `#(free_pages)` la
demande aussi sous le seuil, après le nettoyage du bloc. Les adresses
virtuelles restent réservées.

Les `HashMap<K,V>` à valeurs primitives, empruntées ou allouées placent leur descripteur via le
même plan post-AST. L’index chaîné et les entrées occupent une région.
Les entrées vivantes gardent leur adresse et la table réutilise les
emplacements retirés. Le backend abaisse `insert`, `get`, `get_mut` et
`remove`, avec un résultat `Option`. Un résultat emprunté protège la
table jusqu’à son dernier usage.

Les vecteurs de références et de `A<T>` conservent les dépendances de
leurs éléments. Le nettoyage libère les allocations possédées en ordre
inverse d’insertion avant de restituer la région du vecteur. Le
vérificateur conserve l’union des dépendances aux jonctions de contrôle.
`pop` et `remove` extraient les handles de `Vector<A<T>>`. Les
provenances de la table et du vecteur restent conservatrices après
un remplacement ou une extraction.

`python3 validation/check_rust_regions.py` et
`python3 validation/check_rust_region_collections.py` exercent ces chemins
synchrones.

`runtime::thread({ ... })` abaisse un bloc synchrone en worker pthread.
Son handle peut traverser des scopes et des appels. Le bloc capture par
`move nom;` des valeurs fixes, y compris celles qui possèdent des slots
de pool. En cas d’échec du lancement, les captures possédées sont
détruites. Ses résultats peuvent porter des emprunts ou des allocations. Le plan post-AST compte l’état régional
et dimensionne les datastacks du worker.

L’appel d’une `async fn` crée une Future inactive. `runtime::spawn`
l’inscrit dans la file du runtime et retourne un `Handle<R>` avec
`join()`. `runtime::spawn_blocking` lance une Future sur un thread
dédié en contexte async et retourne un `AsyncHandle<R>` avec `.await`.
Ces deux formes produisent `Result<R, runtime::Error>`. Un `.await`
direct consomme une Future inactive et produit directement `R`.
Le plan post-AST conserve les points de reprise, les temporaires et
les marques de scope des blocs, branches et boucles.

Une `HashMap` peut traverser une tâche par valeur en
conservant sa région d’origine. Les captures et résultats fixes peuvent porter des emprunts et
posséder des slots `A<T>`. Le résultat conserve uniquement les
dépendances déduites du contrat. La responsabilité de nettoyer les
slots passe de la capture à l’état, puis au receveur en cas de transfert.
Un agrégat placé dans un pool ou ajouté à un vecteur transmet les slots
qu’il possède au conteneur. Le nettoyage rend les slots enfants avant
celui du conteneur.

Une `async fn` appelle les autres `async fn` en créant une Future.
Elle peut l’attendre directement avec `.await` ou la lancer sur un thread
dédié avec `runtime::spawn_blocking` puis attendre son handle.
L’appel direct d’une `fn` synchrone depuis une `async fn` est interdit
dans le core.

Compiler le C des programmes qui lancent un thread avec `-pthread`.
`python3 validation/check_rust_native_regions.py` et
`python3 validation/check_rust_task_regions.py` rejouent les témoins.
