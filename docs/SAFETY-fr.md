[English](SAFETY.md)

# Périmètre et vérification mémoire de Corbo

**Actualisation des emprunts mutables :** [MA1–MA6](MUTABLE_ACCESS-fr.md)
remplace l’exclusivité déduite du seul `&mut`. Les exemples et verdicts d’exclusion
rapportés dans les anciens cycles ci-dessous sont historiques ; ils ne définissent
pas la compatibilité actuelle des accès. Permissions, validité, synchronisation
et fins de branche se vérifient séparément.


## Annotations d’emprunt et littéraux à travers mut_vref

Le parseur accepte le préfixe d’emprunt dans l’annotation d’un `let`.
Le vérificateur synchrone compare le mode et le type de la cible à
l’emprunt produit. La passe numérique reconnaît le type de retour de
`vref()` et `mut_vref()` sur `A<T>`. Dans `*vue = 20`, le littéral
prend ainsi le type de la cible.

Les cas synchrones lisent `10` par une vue annotée, écrivent `20` via
une vue mutable annotée ou inférée, puis libèrent l’allocation. Les deux
entrées refusent un mode d’emprunt incompatible, une cible de mauvais
type, la confusion entre emprunt du contenu et du handle, un `drop`
avant la dernière lecture et un littéral hors des bornes de `i32`.
Un cas async exerce une annotation sur un emprunt numérique direct
utilisé après `yield`. Les méthodes `vref()` et `mut_vref()` sont
exercées dans le compilateur synchrone.

Deux tests ciblés à `-O0` et 55 tests à `-O2` passent, avec UBSan
pour les exécutions natives.

[Passe ciblée O0](../validation/core-borrow-annotations-o0.log) ·
[Régression O2](../validation/core-borrow-annotations-o2.log)

## Effets de dépendance après execution.await

N4–N5, AS8, RT5–RT6 et MT9. L'appelant async résout le contrat existant
de la tâche contre son mutex local. Le mutex est réservé dès la capture.
Le champ d'origine et les arguments empruntés restent vivants jusqu'à la
récupération du résultat. Le compilateur vérifie la durée de vie de chaque
cible écrite, y compris une cible remplacée avant la fin de la tâche.

Après l'attente, `Ok(())` retrouve la provenance de fin de tâche et
`Err(LaunchFailed)` retrouve celle d'origine. Sans discrimination, les
deux restent possibles. Une écriture conditionnelle conserve l'ancienne
cible sur les chemins sans écriture. Une nouvelle écriture invalide le
lien entre un ancien statut et le graphe actuel.

Le témoin teste le match direct et le résultat nommé immuable, avec un
`yield` dans la tâche et dans l'appelant. Avec la soumission ordinaire,
l'appelant détruit l'ancienne cible et relit `2` sous garde. En injectant
`EAGAIN` à la soumission du handle enfant, il détruit la nouvelle cible
et relit `1`. Les deux cibles sont détruites une seule fois. Les deux
entrées du compilateur refusent de détruire l'une des cibles ou le mutex
avant l'attente, de lire le mutex par un autre appel pendant cette
réservation, et de stocker une cible de portée trop courte. Les variantes
vérifient aussi les destructions inverses et les statuts ignorés ou périmés.

Le raccordement porte sur les tâches Void qui remplacent un champ
`&i32` d'un mutex local emprunté explicitement. L'appelant async retourne
Void ou un scalaire indépendant. Les lecteurs concurrents pendant la
réservation, les relais du handle, Select et l'attente directe de la tâche
inactive restent hors de ce périmètre. La passe ciblée à `-O0` exécute
4 méthodes et le rejeu à `-O2` en exécute 129. Les deux passent, avec
UBSan pour les oracles natifs.

[Passe ciblée O0](../validation/guarded-await-targeted-o0.log) ·
[Régression O2](../validation/guarded-await-regression-o2.log)

## Effets de dépendance des tâches sous garde

N4–N5, AS8, RT5–RT6 et MT9. Le contrat d'une tâche qui écrit
`charge.vue = &*nouvelle` sous garde identifie l'argument mutex, le champ
et l'argument qui fournit la cible. Le compilateur vérifie chaque cible
stockée par la tâche contre la durée du mutex chez l'appelant. Il réserve
le mutex aux accès de la tâche jusqu'à l'attente.

À la lecture du résultat de `join()`, les deux branches retrouvent des
graphes distincts. `Ok(())` utilise les provenances de fin de tâche.
`Err(LaunchFailed)` conserve les provenances initiales. Lorsque le statut
est ignoré ou que le graphe exact n'est plus identifiable, les deux
possibilités restent suivies. Un remplacement conditionnel conserve
également la provenance d'entrée sur les chemins sans écriture.

Le témoin vérifie le contrat inféré, puis exécute les chemins de succès
et d'échec de la première soumission avec un `match` direct et un résultat
nommé. Dans `Ok`, il détruit l'ancienne cible et relit `2` sous garde.
Dans `Err`, il détruit la nouvelle cible et relit `1`. Il vérifie la
destruction unique des deux allocations. Les deux entrées du compilateur
refusent la destruction de la cible encore stockée dans chaque bras,
sa destruction avant le join, un lecteur concurrent, une cible trop
courte, la destruction de l'ancienne cible quand l'écriture est
conditionnelle et cette même destruction quand le statut est ignoré.

Le premier rejeu élargi a retrouvé un refus sur le remplacement d'un champ
possédé après transfert du receveur dans un bloc enfant. Le calcul de durée
choisissait la liaison du parent alors que le receveur était désormais dans
l'enfant. La recherche repart de la portée la plus proche et le test
existant repasse aux deux niveaux d'optimisation.
[Premier rejeu](../validation/guarded-task-initial-o2.log)

Périmètre du lot. Écriture directe d'un champ partagé `&i32` depuis une
tâche Void, cible empruntée en paramètre et mutex possédé dans le code
synchrone qui crée la tâche et joint le handle. Les mutations de provenance
concurrentes, les relais de handle et l'attente async de ces effets restent
hors de ce périmètre. Les oracles natifs utilisent UBSan. Quatre méthodes
ciblées passent à `-O0`, deux à `-O2`, et le rejeu élargi passe sur
128 méthodes à `-O2`. Le témoin ASan du cycle précédent ne termine pas
dans cet environnement.

[Passe ciblée O0](../validation/guarded-task-targeted-o0.log) ·
[Passe ciblée O2](../validation/guarded-task-targeted-o2.log) ·
[Régression](../validation/guarded-task-regression-o2.log)

## Clôture du lot d'intégration du noyau

- Les remplacements de champs `&i32` et `A<Item>` dans la charge d'un mutex
  local mettent à jour l'emprunt et la provenance de l'allocation. Le même
  scénario passe avec `Mutex` et `AsyncMutex`, en écriture directe et via
  un auxiliaire synchrone. Il libère l'ancienne cible, réutilise le slot de
  l'ancien champ et vérifie une seule destruction du nouveau champ avant
  celle du mutex. Les deux entrées refusent le drop prématuré de la
  nouvelle cible, l'emprunt d'une cible trop courte et le transfert d'un
  champ dont le pool ne survit pas au mutex.
- La vérification exige un mutex local suivi sans autre emprunt et un
  réemprunt de la charge entière. Elle refuse le changement de provenance
  par une tâche enfant ou à travers un mutex partagé. La mutation du
  contenu derrière un emprunt mutable déjà installé reste couverte par
  le scénario concurrent du cycle précédent.
- L'EBNF et les entrées source du noyau excluent les quatre entrées
  expérimentales du scheduler. Les API Python et la CLI les exposent sur
  option. Les commandes `check`, `effects`, `emit-c` et `build` ont été
  vérifiées dans les deux profils sur la même source expérimentale.
- Treize exemples utilisent les déplacements par valeur et les primitives
  cibles. Les témoins sans annotation exercent les défauts `i64` et `f64`.
  Les deux familles de tests d'agrégats async ont été corrigées vers
  `A<T>`. Leurs fixtures historiques conservent les flèches employées par
  les variantes négatives. Le premier rejeu après migration textuelle des
  fixtures rompait les substitutions de ces tests et mélangeait les deux
  syntaxes. Les équivalents modernes vérifient le retour
  propriétaire et la consommation par une fonction sync après `yield`,
  avec réemploi du slot. Les deux cas d'enums en échec dans `test_crust`
  et les exemples historiques `borrowed_returns` et
  `mutable_reference_fields` ont reçu la même correction de type.

La passe finale exécute 29 tests ciblés à `-O0` et 170 tests à `-O2`.
Le rejeu de `test_crust` exécute 137 tests. Les trois passes réussissent
avec UBSan dans les oracles C.

Le témoin ASan minimal compile et dépasse cinq secondes à l'exécution.
La couverture de ce cycle repose sur UBSan et les oracles de sortie et de
destruction. L'audit indépendant reste distinct.

[Tests d'intégration](../validation/core-close-integration-o0.log) ·
[Cas ciblés](../validation/core-close-final-targeted-o0.log) ·
[Régression finale](../validation/core-close-final-regression-o2.log) ·
[Rejeu historique](../validation/core-close-legacy-ubsan.log) ·
[Exemples CLI](../validation/core-close-cli-examples.log) ·
[CLI du scheduler](../validation/core-close-cli-scheduler.log) ·
[Témoin ASan](../validation/core-close-asan-witness.log)

## Cycle des retours async et charges gardées

- Les retours d'emprunts numériques larges réutilisent les contrats de
  provenance des emprunts. Le résultat de l'attente utilise un membre C
  pointeur du type exact. Le test `u64` couvre l'attente directe, les deux
  attentes de handle et le retour par un auxiliaire après `join()`. Un
  test `f64` lit un champ aligné emprunté dans une structure. Les
  variantes invalides vérifient les réservations jusqu'au dernier usage
  et le refus du retour d'une cible locale.
- Une charge gardée représentée conserve les cibles empruntées et les
  sources de ses descendants possédés. Les cas sync, async et async local
  vérifient l'accès au champ emprunté et à l'enfant possédé, la destruction
  unique et le réemploi de son pool. Deux tâches modifient une cible
  empruntée mutable sous le verrou du même mutex. Le remplacement d'un
  champ de dépendance par une nouvelle provenance reste refusé sous garde,
  y compris par un appel dont le contrat indique ce remplacement.
- Deux programmes valides étaient refusés avec le diagnostic de source
  locale trop courte. Ils retournent une structure dont la création est
  précédée ou suivie d'un `if` de lecture. Le compilateur réserve maintenant
  le slot parent quand le chemin rejoint le transfert avec le même
  producteur. Le test contrôle la construction dans la réservation et
  l'ordre de récupération. Les cas non reproduits restent au plan existant.

La passe ciblée à `-O0` a exécuté 24 méthodes avec succès. À `-O2`,
190 méthodes de régression passent, ainsi que les compléments de 38
méthodes sur le placement et 27 sur les retours d'emprunts. L'oracle C
utilise UBSan avec arrêt au premier signalement.
[Passe ciblée](../validation/core-dependencies-returns-o0.log) ·
[Placement](../validation/core-dependencies-placement-o2.log) ·
[Régression](../validation/core-dependencies-returns-o2.log) ·
[Rejeu des retours](../validation/core-dependencies-reference-replay-o2.log)

## Cycle du runtime intégré · 9 novembre 2026

Périmètre. Runtime intégré de RT2–RT8 et interactions avec les
`.await` directs, les mutex et Select. Le contexte de poll est représenté
dans le C par un ticket de réveil qui identifie l'entrée et sa génération.
Un poll enfant hérite de la cible de son parent.

- La suite de disponibilité compare le runtime à un modèle indépendant
  sur 2 401 traces de quatre actions. Les essais synchronisés vérifient
  les réveils pendant le poll, la fusion des notifications et la reprise
  sur un autre thread sans poll simultané. Les suites FIFO et Select
  exercent également leurs modèles et les tickets périmés après réemploi.
- Le nouveau test force le `Pending` d'un mutex dans une chaîne de deux
  `.await` directs. Il vérifie que la file a retiré la racine avant la
  libération du mutex et que le ticket du mutex désigne la racine.
  Les deux pools des enfants sont vides à la complétion. Le slot racine
  et sa capture propriétaire sont encore occupés. Le `join` extrait
  `17`, détruit la capture une fois, rend les deux slots et permet le
  réemploi de l'adresse de la capture.
- Les tests de nettoyage exercent les captures inactives et suspendues,
  les échecs de lancement et les obligations d'attente à travers les
  appels. Les tests de Select rejouent le nettoyage des branches
  perdantes et le refus d'abandonner un handle lancé.

Le test de la chaîne d'attentes passe à `-O0` et `-O2`, en complément
des 70 méthodes à `-O0` et 124 méthodes à `-O2` des deux passes réussies.
La régression à `-O2` couvre aussi le noyau mémoire et le placement
des résultats async. L'oracle compile en C11 avec UBSan et s'arrête au
premier signalement. Aucun écart de comportement n'a nécessité de
modification du runtime dans ce périmètre.
[Passe ciblée](../validation/core-builtin-runtime-o0.log) ·
[Régression à O2](../validation/core-builtin-runtime-o2.log) ·
[Chaîne d'attentes à O0](../validation/core-builtin-runtime-direct-await-o0.log) ·
[Chaîne d'attentes à O2](../validation/core-builtin-runtime-direct-await-o2.log)

Le témoin ASan compile et dépasse le délai de cinq secondes à l'exécution.
Les résultats de ce cycle concernent les scénarios et ordonnancements
exercés. [Témoin ASan](../validation/core-builtin-runtime-asan.log)

## Dernier lot du noyau · 9 novembre 2026

Ce lot raccorde RT3, les emprunts numériques du brouillon 07, MT9 et le
placement parent de L7 sur les branches qui continuent. Les signatures et
les règles de langage restent celles des documents normatifs.

- Le vérificateur suit la possibilité qu'une installation ou un lancement
  ait déjà eu lieu. Il fusionne les chemins qui continuent et réanalyse les
  reprises de boucle. Les appels opaques propagent l'effet de lancement
  déduit du corps. Ce résumé est conservateur quand un auxiliaire lance
  une tâche seulement sur un chemin qui ne revient jamais. Le garde-fou
  runtime demeure. Les branches exclusives peuvent installer des instances
  différentes si leur stockage appartient à `main`.
- Les champs du profil numérique sont espacés à l'alignement de `Cell`.
  Ce choix du backend C maintient aussi l'alignement des projections de
  structures imbriquées. Un champ `u64` est emprunté par un auxiliaire sync
  puis capturé par une tâche. Un autre cas prête un scalaire local et refuse
  d'en faire une copie par bloc `move` avant le join.
- Le mutex de structure prend la valeur locale à son adresse d'origine.
  Sa destruction détruit la charge. Les réemprunts de garde retiennent
  cette dernière, et une tâche qui retourne une valeur copiée peut libérer
  la garde après la fin de ses références locales.
- Le plan de réservation d'un `if` peut exclure une branche qui quitte
  la fonction. Le test vérifie que le C construit le résultat dans la
  réservation du parent, que le temporaire est récupéré avant le résultat
  et que le chemin de retour libère la réservation inutilisée.

La passe initiale a relevé des fixtures d'installation qui déclaraient un
second scheduler inutilisé. Les fixtures ont été corrigées pour atteindre
le contrôle voulu. Une régression élargie à 89 méthodes a aussi produit
21 échecs et 8 erreurs de sous-tests dans les suites historiques
`test_async_owned_struct_returns` et `test_async_owned_struct_sync_calls`.
Le vérificateur rejette leurs compositions de paramètres locaux `T` et
d'allocations de pool `A<T>`. Ces deux suites restent en échec et leurs
fixtures ont été conservées.
[Journal de la passe élargie](../validation/core-final-lot-placement-o2.log)

Les 19 méthodes ciblées à `-O0` et les 63 méthodes du rejeu de placement
à `-O2` passent. La régression du noyau a exécuté 219 méthodes à `-O2`
en 160,7 secondes. Le complément après le raccordement du dernier retour
de champ a rejoué 26 méthodes à `-O2`. Ces deux passes ont réussi.
L'oracle C utilise UBSan avec arrêt au premier signalement.
[Passe ciblée](../validation/core-final-lot-o0.log) ·
[Rejeu du placement](../validation/core-final-lot-placement-replay-o2.log) ·
[Régression du noyau](../validation/core-final-lot-verified-o2.log) ·
[Complément emprunts de champs](../validation/core-final-lot-fields-o2.log)

Restent ouverts le poll et la file programmables, les retours d'emprunts
numériques larges depuis une tâche, les charges de mutex qui portent des
dépendances et la généralisation du placement anticipé. Le témoin ASan du
cycle précédent reste le dernier contrôle ASan exécuté.

## Cycle d'intégration du noyau · 9 novembre 2026

Périmètre de cette passe. Noyau numérique du brouillon 07, transferts par
valeur des threads natifs, scheduler RT2–RT5, mutex MT9 et frontière
scalaire FFI1–FFI6. La [matrice](VERIFICATION_MATRIX.md#intégration-du-noyau)
relie chaque lot à ses cas. Les API de collections ont servi de régression
quand elles exerçaient une règle du noyau.

- Le programme du noyau utilise les largeurs numériques cibles par défaut.
  Les marqueurs historiques et `--legacy-numeric` gardent un chemin de
  compatibilité. `try_from` utilise l'erreur du noyau dans le nouveau profil.
  Les résultats conservent leur largeur dans les états async, y compris
  sur un join natif imbriqué.
- Le code C reçoit des signatures scalaires et Void, compile les sources
  fournies à `build` ou `run` en objets puis les lie. Le périmètre lexical
  de `unsafe` est contrôlé avant l'abaissement. Les tests CLI compilent
  et lient avec le compilateur C natif. L'oracle C exécute les cas
  de code généré sous UBSan et interrompt l'exécution au premier signalement.
- L'installation d'un scheduler relie ses trois callbacks au runtime sous
  mutex. Le backend C de cette passe fournit la file FIFO et les boucles
  de poll. `runtime::start_poller()` démarre et enregistre un poller de
  cette file, jusqu'à 64 pour cette implémentation. `future.enqueue()`
  remet la tâche au backend, et `future.launch_failed()` déclenche son
  nettoyage et publie `LaunchFailed` via le handle. `spawn_blocking` utilise
  le chemin dédié aux opérations bloquantes. Le thread natif contourne
  les callbacks. L'ordre et l'unicité d'installation sont contrôlés à
  l'exécution. Le stockage d'une instance installée doit appartenir
  directement à `main` et son état ne peut pas contenir d'emprunts.
  Les essais rejouent aussi deux branches d'installation exclusives,
  deux diagnostics d'installation et un lancement depuis une tâche avec
  récupération d'un succès et d'un échec par `.await`.
  [Essais du scheduler](../validation/core-integration-scheduler-smoke.log)
- Les tests source des mutex exercent des charges scalaires. Les tests
  runtime séparés exercent l'affinité de la garde sync, le réveil après
  libération d'une garde async sur un autre thread et la destruction
  des réservations dans Select.

Les écarts rencontrés et corrigés comprennent l'écriture d'un résultat de
join numérique via un pointeur de mauvais type, l'alignement du champ
`i32` suivant un petit scalaire, l'appel de fonction scalaire large depuis
un état async et la libération tardive d'une garde au retour d'une tâche.
La première régression C a également relevé que le runtime autonome
dépendait d'un diagnostic du code généré. Le diagnostic du scheduler est
désormais local au runtime. [Rejeu des primitives C](../validation/core-integration-runtime-replay.log)

La passe ciblée compte 13 méthodes à `-O0` et le rejeu des primitives C
22 méthodes à `-O2`. La régression finale à `-O2` a exécuté 213 méthodes
en 154,5 secondes, toutes réussies. Elle couvre aussi le noyau mémoire, les
tableaux fixes, les appels sync depuis un thread et Select.
L'essai de
`build --c-source` a produit un binaire dont la sortie est `301`.
[Passe ciblée](../validation/core-integration-o0.log) ·
[Régression finale](../validation/core-integration-verified-o2.log) ·
[Commande build](../validation/core-integration-ffi-build.log)

Le témoin ASan minimal compile, puis dépasse le délai de cinq secondes
à l'exécution dans cet environnement. [Journal du témoin](../validation/core-integration-asan-witness.log)

Limites restantes. Le poll d'une `Future` et la file d'un scheduler écrit
en Corbo restent ouverts. Les charges non scalaires des mutex, les
réemprunts de garde hors `i32`, les emprunts directs de champs numériques
larges et certaines compositions async restent à raccorder. Le placement
anticipé général et le retrait du profil historique restent suivis dans la
[checklist](IMPLEMENTATION_CHECKLIST.md). Les tests couvrent les programmes
et interactions listés. Une preuve générale, les campagnes de mutations et
l'audit indépendant sont hors de cette passe.

## Cycle de la grammaire du noyau

La [grammaire EBNF](../CORE_GRAMMAR.ebnf) décrit le noyau cible, y compris
les formes async. Elle n'est pas utilisée pour compiler les programmes.
Les contrôles du compilateur, notamment les types, les durées de vie et
les obligations d'attente, s'appliquent après la reconnaissance syntaxique.

Un lecteur EBNF temporaire a traduit les productions en règles de
reconnaissance et les a exercées sur 18 sources. Onze sont reconnues,
dont `yield;` dans une fonction ordinaire, qui doit échouer à la
validation contextuelle. Les sept autres sont rejetées. Le journal
conserve chaque source et son résultat attendu.
[Vérification de la grammaire](../validation/core-grammar-check.log)

Quatre sources reconnues ont également été vérifiées, traduites en C et
exécutées sous UBSan avec le compilateur actuel, après substitution
d'`Int` à `i32`. Elles couvrent le transfert nommé, le bloc de capture,
Select et le thread natif sans capture. Le compilateur rejette bien
`yield;` en contexte synchrone. Ces exécutions concernent le prototype.
[Vérification du prototype](../validation/core-grammar-prototype.log)

Après arbitrage, la grammaire a été complétée pour les littéraux flottants
et les deux formes de captures de thread. Le lecteur EBNF a rejoué les 18
cas initiaux et 14 cas supplémentaires, sans écart. Les nouveaux cas
incluent les cinq formes de flottant, un `let` annoté `f32`, la distinction
avec `1..3`, les captures nommées ou déduites, ainsi que les refus d'un
exposant incomplet, d'un suffixe de type et d'une ancienne tête de captures.
Ce contrôle porte sur la syntaxe. Le compilateur reste à adapter.
[Journal du complément](../validation/core-grammar-floats-and-thread-moves.log)

Après le retrait de la notation exponentielle, la vérification syntaxique
a rejoué 33 cas sans écart. `1.5`, `1.` et `.5` restent reconnus, `1..3`
reste un intervalle et les formes avec `e` ou `E` sont rejetées.
[Journal des littéraux décimaux](../validation/core-grammar-decimal-floats.log)

Quatre cas ont ensuite vérifié la syntaxe de la négation booléenne
`!` et sa distinction de `!=`, sans écart. La reconnaissance
syntaxique d'une condition entière ne valide pas son type.
[Journal des conditions](../validation/core-grammar-boolean.log)

Cinq cas ont vérifié les formes des opérateurs bit à bit, sans écart.
Les cas combinent l'emprunt, les comparaisons et les opérateurs logiques.
[Journal des opérateurs bit à bit](../validation/core-grammar-bitwise.log)

Cinq cas de syntaxe des décalages passent. Ils distinguent les opérateurs
des chevrons de comparaison ou de types imbriqués et séparent la syntaxe
du contrôle du nombre de positions.
[Journal des décalages](../validation/core-grammar-shifts.log)

Six cas vérifient la syntaxe des affectations composées, sans écart.
Ils couvrent les cinq opérateurs, un accès indexé et un déréférencement.
[Journal des affectations composées](../validation/core-grammar-compound-assignment.log)

L'EBNF couvre maintenant les formes source de RT3, MT9, FFI1–FFI5 et le
nom public de l'erreur numérique. Le lecteur EBNF a rejoué 53 cas
archivés et exécuté 15 nouveaux cas, sans écart. Huit sont reconnus,
dont deux qui relèvent d'un rejet contextuel, et sept sont refusés par
la grammaire. Ce passage exerce la reconnaissance syntaxique. Il ne
valide ni le compilateur pour ces nouvelles formes, ni l'option
`--c-source` de FFI6.
[Journal des interfaces](../validation/core-grammar-interfaces.log)

## Cycle des déplacements par valeur

Les nouvelles formes du [brouillon 02](../design-buffer/02-marqueur-transfert.md)
sont abaissées vers les opérations internes déjà vérifiées. Les signatures
identifient les paramètres reçus par valeur et les résultats propriétaires.
Les blocs `move` calculent les captures lexicales avant l'analyse des
contrats. Le vérificateur garde la responsabilité des contrôles de durée
de vie, d'exclusivité et de nettoyage. Le déplacement transmet le même
objet. Un scalaire capturé possède sa propre copie dans le bloc.

| Exécution | Résultat |
| --- | --- |
| Passe ciblée initiale O0/UBSan | 8 méthodes réussies. [Journal](../validation/value-moves-targeted-first.log) |
| Régression O2/UBSan des fonctions, agrégats, emprunts, boucles et tâches | 158 méthodes réussies en 183,533 s. [Journal](../validation/value-moves-regression.log) |
| Rejeu O2/UBSan après raccordement des arguments tableaux et correction des fixtures | 38 méthodes réussies en 37,748 s. [Journal](../validation/value-moves-final.log) |
| Rejeu O2/UBSan avec résultat de bloc calculé par un appel | 38 méthodes réussies en 22,758 s. [Journal](../validation/value-moves-final-replay.log) |
| Passe finale O0/UBSan, avec allocation directe comme résultat de bloc | 9 méthodes réussies en 4,076 s. [Journal](../validation/value-moves-targeted-final.log) |

La suite moderne exécute onze programmes natifs. Elle vérifie douze
variantes invalides aux deux entrées du compilateur, notamment le deuxième
usage après déplacement, une capture avant le dernier usage d'un emprunt,
un pool trop court et un `move a;` après l'entrée du bloc. Les assertions
sur le C exécuté vérifient l'identité de l'allocation, la destruction
unique et le réemploi du slot. Les cas async exercent l'attente et la
copie d'un scalaire à travers `yield`.
[Tests](../tests/test_value_moves.py)

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest -v \
  test_value_moves test_core_memory test_spawn_blocking \
  test_strict_structure_returns test_local_enums
```

Le premier passage étendu a démarré avant la stabilisation de la
compatibilité et des attentes de tests. Son bilan est de 593 méthodes
avec 29 échecs d'assertion et 37 erreurs, sous-tests compris. Les 51
méthodes historiques en échec de `test_foundation_rules` ont ensuite été
rejouées sur le compilateur actuel et sur une copie antérieure au
chantier. Les identifiants des 15 échecs d'assertion et 10 erreurs
restants coïncident entre les deux exécutions. Ils restent ouverts.
Les autres échecs du premier passage portaient notamment sur des
tests qui exigeaient encore la présence de flèches.
[Premier passage](../validation/value-moves-regression-first.log) ·
[Ancienne version](../validation/value-moves-historical-baseline.log) ·
[Rejeu actuel](../validation/value-moves-historical-current.log)

Le compilateur sélectionne la grammaire historique pour une source avec
flèches de transfert ou avec la compatibilité reset activée. Une source
avec `move` utilise la grammaire moderne. Les appels de collections,
les formes de capture de thread natif et les captures async d'emprunts
n'ont pas fait l'objet d'une migration générale dans ce cycle. Les
résultats couvrent les cas exercés. ASan et l'audit adversarial ne font pas
partie des passes de ce cycle.

## Cycle de validation du noyau mémoire — 8 novembre 2026

Le cycle porte sur les transitions N1–N8 et leur composition dans les cas
retenus, avec les API de collections existantes. La grille est une synthèse
des règles. Aucune règle normative n'a changé.
[Règles](LANGUAGE_RULES.md) · [Matrice](VERIFICATION_MATRIX.md)

- Le profil par défaut a exécuté dix programmes C ciblés. Dix-neuf variantes
  invalides sont refusées avec le diagnostic attendu aux deux entrées
  `verify_program` et `compile_source`. Les assertions vérifient notamment
  les valeurs, l'identité d'adresse, l'ordre de destruction et le réemploi
  d'un slot. La passe ciblée après correction comprend aussi le cas de
  provenance historique, soit dix méthodes réussies en 4,087 s.
  [Tests](../tests/test_core_memory.py) · [Journal](../validation/core-memory-shadow-targeted.log)
- Dans le C du transfert, le relais retourne le même `Cell *`. L'appelant
  détruit la valeur avant la réutilisation du slot. Dans le remplacement,
  l'appel et `cell_new` précèdent `cell_drop` de l'ancienne allocation.
  `cell_drop_impl` exécute les destructions avant `cell_release_storage`.
  [Transfert](../validation/core-memory-transfer.c) · [Remplacement](../validation/core-memory-replacement.c)
- L'ancienne assertion du retour `T` recevait un diagnostic plus précis
  d'incompatibilité `T / A<T>`. Les deux entrées refusaient déjà le programme.
  L'assertion a été ajustée et les six méthodes de ce module ont réussi.
  [Passe initiale](../validation/core-memory-regression.log) · [Rejeu](../validation/core-memory-diagnostic-replay.log)
- Trois fixtures historiques remplaçaient la première valeur sans l'utiliser.
  Chacune lit désormais cette valeur, conformément à U1. Le cas avec masquage
  révélait ensuite un refus incorrect. L'analyse du compilateur traite
  désormais le nom comme masqué jusqu'à la fin du bloc, en tenant compte
  des sorties qui empêchent d'atteindre l'usage extérieur. Le test courant
  exerce l'usage extérieur accepté et les refus quand seul le nom intérieur
  est lu ou quand un retour empêche l'usage extérieur.
  [Refus initial](../validation/core-memory-legacy-flow-replay.log) · [Rejeu ciblé](../validation/core-memory-shadow-targeted.log)
- La passe ASan+UBSan du profil historique a été interrompue après des
  dépassements de délai. Un exécutable C minimal instrumenté, qui affiche
  une ligne puis termine, a reproduit le délai sans sortie. La cause
  environnementale précise n'a pas été établie. Le résultat ASan est
  non concluant. Les suites retenues utilisent UBSan avec arrêt au premier
  diagnostic dans les harnais instrumentés.
  [Contrôle du harnais](../validation/core-memory-asan-toolchain.log) · [Journal interrompu](../validation/core-memory-legacy-flow.log)

Les quatre passes finales ont rendu le code 0. Le manifeste conserve les
commandes, les variables des harnais et les 415 empreintes Python, identiques
avant et après les passes. Le compilateur C utilisé est Clang 20.1.3 sur arm64.
[Manifeste](../validation/core-memory-final.json)

| Passe | Méthodes réussies | Temps unittest | Configuration et journal |
| --- | ---: | ---: | --- |
| Noyau, contrats, Select et lancement | 111 | 96,775 s | [O2/UBSan](../validation/core-memory-final-regression.log), avec variantes historiques dans les refus de spawn_blocking |
| Threads natifs et réveils | 23 | 24,242 s | [O0/UBSan](../validation/core-memory-final-threads.log) |
| Placement, limites et nettoyage en suspension | 32 | 29,612 s | [UBSan](../validation/core-memory-final-storage.log), O2 et O0/O2 pour les sondes de régions |
| Boucles, jonctions et usage des receveurs | 42 | 47,333 s | [O0/UBSan](../validation/core-memory-final-legacy-flow.log), principalement profil de compatibilité |

Les modèles existants ont été rejoués pour les exigences de stockage, le
poll et le nettoyage de Select, les intervalles des deux curseurs, le
nettoyage en suspension et les remplacements de receveurs. Les scénarios
générés conservent les graines déclarées dans leurs tests, dont 9081, 2219
et 6077 pour les intervalles de stockage, et 20261103 pour les jonctions.

Les preuves d'exécution couvrent les chemins exercés. Le placement anticipé
général et les garanties concurrentes au-delà des scénarios testés restent
ouverts. La construction publique des mutex et l'interface publique du
scheduler personnalisé restent à arbitrer. La campagne de mutations et
l'audit adversarial approfondi relèvent du lab indépendant.

## Historique de l'audit initial — 1er novembre 2026

## Statut

Corbo vise à générer du C respectant des règles mémoire vérifiées avant émission.
Les tests, les invariants exécutables du vérificateur et les contrôles du runtime
apportent des éléments vérifiables. Ils ne constituent pas une preuve formelle
que tous les programmes acceptés sont sûrs.

L'audit initial cherchait des contre-exemples sans ajouter de fonctionnalité.
Les évolutions suivantes sont désormais implémentées et testées séparément :
reset collectif, destruction de l'ancienne allocation après évaluation d'une
réaffectation et expressions dans les arguments évaluées de gauche à droite.
Les instructions `if / else` avec effets mémoire et retours Void/scalaires ou
d'allocations de même type avec suivi des sources possibles sont
désormais ajoutées dans le périmètre borné décrit ci-dessous.
Les expressions `if` peuvent aussi fournir une allocation de même
type à un receveur, via un `<-` final dans chaque branche qui continue.
`loop`, `while`, `break` et `continue` ajoutent des reprises analysées jusqu'à stabilisation,
un nettoyage par itération et des sorties distinctes des retours de fonction.

## Sous-ensemble concerné

- Exécution synchrone, blocs lexicaux, fonctions non récursives et `main`.
- Résumés symboliques des effets externes de sources, inférés pour toutes les
  fonctions et propagés dans les sous-appels, même sans appel concret.
- Résumés symboliques des résultats alloués : origines neuves, identités entrantes
  restituées ou sélectionnées, propagation et vérification des origines aux appels.
- Contraintes symboliques d’égalité et de distinction entre sources, inférées
  dans l’ordre des opérations et vérifiées pour toutes les provenances aux appels.
- Vérification des déplacements, emprunts et transitions mémoire de chaque corps
  avec des entrées symboliques, même sans appel réel. Les contrôles concrets par
  spécialisation restent actifs aux appels ; les corps inutilisés ne sont pas émis.
- Expressions dans les arguments évaluées de gauche à droite, avec protection
  des allocations et emprunts préparés jusqu'à l'appel.
- Entiers Int32, allocations explicites d'Int et enums à champs Int, &Int ou &mut Int.
- Lecture `*data` du contenu Int d'une allocation ou d'un emprunt valide.
- Sources locales explicitement choisies : tas, data stack ou pool typé.
- Emprunts en lecture et mutables, déplacements et transferts directs entre
  activations parentes/enfants.
- Destruction automatique, `drop` explicite et destruction collective par
  `reset`, avec refus des accès futurs aux allocations concernées.
- Branches `if / else`, comparaisons Int, conditions littérales et retours
  Void/scalaires ou d'allocations de même type ; jonction et nettoyage conditionnel.
- Expressions `if / else` fournissant une allocation à un receveur, y compris
  `else if`, les transferts du parent et les branches quittant la fonction.
- `loop`, `while`, `break` et `continue` non étiquetés, avec résultats de `break` pour `loop` : reprise analysée, nettoyage
  des itérations et réunion des sorties ; divergence sans résultat fictif.
- `match` exhaustif. Avec `&mut`, les bras peuvent écrire dans les cibles de
  leurs projections mutables via `.set()` ou les réemprunter par un appel
  `Void`. Les arguments nommés restent des projections du bras.
  [Validation](MATCH_MUTABLE.md).

Les retours d'emprunts vers d'autres types que Int, champs de référence
autres que &Int/&mut Int, graphes transitifs de
dépendances, destructeurs utilisateur, collections, `for`,
labels de boucle, threads, async et appels C externes ne font pas partie de ce
sous-ensemble. Ils ne doivent pas être considérés couverts par les tests actuels.
Les champs &Int immuables sont décrits dans [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md).
Le transfert automatique de leurs dépendances est interdit par D1 ; les retours de
fonctions sont désormais admis pour des cibles déjà assez durables dans la
destination. Le refus est une règle du langage, et non une promotion différée.

Les [retours directs &Int](DIRECT_BORROW_RETURNS.md) suivent les identités des
cibles et les vérifient à chaque frontière enfant → parent, sans allocation ni
promotion implicite. Leurs usages futurs protègent toutes les cibles possibles,
y compris à travers plusieurs appels et un stockage dans un champ &Int.

## Obligations et contrôles

| Obligation | Mécanisme actuel | Éléments de validation |
| --- | --- | --- |
| Allocation rattachée à un scope actif | État des allocations, vérifié aux frontières des instructions et des scopes | Tests des blocs, appels, retours et nettoyages |
| Source vivante pendant la vie de l'allocation | Provenance conservée ; refus d'échapper à une source locale ; invariant d'état | Transferts depuis sources trop courtes, paramètres et pools d'enum |
| Un accès direct utilisable par allocation | Invalidation lors des déplacements ; accès local distinct lors d'un transfert descendant | Régressions sur retours avec receveur explicite et retours ordinaires |
| Emprunt mutable exclusif | Dernières utilisations, contrôle des accès et aliases d'arguments, suspension pendant les réemprunts | Lectures, écritures, appels imbriqués et tentatives de déplacement |
| Pas d'accès après destruction ni double destruction | État partagé de l'allocation, invalidation des accès consommés, retrait du nettoyage final | `drop`, reset collectif, effets des appels et réutilisation de slots |
| Accès valide sur tous les chemins qui continuent | États séparés des branches, jonction, indicateurs de nettoyage indépendants des slots | Destructions conditionnelles, retours, emprunts, appels et pools d'enum |
| Type et initialisation cohérents | Source typée, validation des champs et des signatures | Variantes, champs manquants/dupliqués, mauvais pools et retours |
| Accès aux champs dans la bonne variante | Schéma connu et `match` exhaustif traduit en `switch` | Lectures de chaque variante et refus de patterns incorrects |
| Stockage stable et borné | Réservations virtuelles, strides alignés, contrôles de capacité et page de garde | Comparaisons d'adresses, épuisements, oracle du runtime |
| Index libre et curseur cohérents | Retrait des slots du suffixe avant recul, liste intrusive des emplacements libres | Séquences arbitraires et oracle indépendant du compilateur |

Les invariants exécutables du vérificateur partagent son modèle d'état : ils
détectent des incohérences de ce modèle, sans prouver indépendamment que son
analyse de durée de vie correspond toujours à l'exécution du C.

`drop(-> value)` et `source.drop(-> value)` partagent les vérifications de
déplacement et le même chemin de destruction. La première forme utilise la
provenance enregistrée, tandis que la seconde vérifie en plus le receveur
explicitement fourni. La destruction via la provenance ne crée pas de source
implicite et ne contourne pas les restrictions d'emprunt. Ces deux formes sont
comparées par des tests de traces et de nettoyage exactement une fois.
Le [contrat de destruction explicite](DROP.md) détaille aussi les appels
imbriqués, les emprunts et l'identité des allocations lors de la réutilisation
d'un slot. Ces cas sont vérifiés dans `tests/test_drop_transitions.py`.
Le [contrat de reset](RESET.md) précise la destruction collective, le refus
des usages futurs et les paramètres C internes nécessaires à son exécution
dans une fonction. Les régressions sont dans `tests/test_reset_transitions.py`.
Le [contrat de réaffectation](REASSIGNMENT.md) distingue la fin de l'évaluation
de droite, la destruction de l'ancienne allocation et l'installation du nouvel
accès. Les tests incluent les emprunts utilisés dans cette expression, les
fonctions qui consomment ou retournent la même allocation et les pools bornés.
Le [contrat des arguments](ARGUMENTS.md) précise l'ordre des effets, la fin des
emprunts de sous-appels et la protection des arguments préparés. L'analyse de
dernière utilisation distingue désormais les sous-expressions d'une instruction.
Les régressions sont dans `tests/test_arguments.py`.
Le [contrat des conditions](CONDITIONALS.md) décrit les états séparés par branche,
la disponibilité sur tous les chemins qui continuent et les indicateurs de
nettoyage indépendants des slots. Les retours de branche sont aussi réunis au
retour de la fonction pour conserver leurs effets chez l'appelant. Les tests
correspondants sont dans `tests/test_conditionals.py`.
Les [retours conditionnels d'allocations](CONDITIONAL_RETURNS.md) réunissent les
candidats dans un descripteur sélectionné, de type commun et sources possibles, chez
l'appelant. Un retour uniforme de la même allocation entrante conserve son
identité et ses correspondances d'import ; les autres candidats suivent la
réunion qui retire les anciennes identités retournées sans
détruire les objets exécutés et conserve les autres effets des chemins.
La responsabilité du nettoyage est transférée avec le résultat : désarmement
de l'ancien indicateur, rétablissement au retour dans le même scope quand
nécessaire, et exclusion des indicateurs d'une fonction terminée. La jonction
ne contraint l'ordre que pour les allocations encore vivantes sur chaque chemin.
Les régressions sont dans `tests/test_conditional_returns.py`.
Les [expressions if avec receveur](IF_EXPRESSIONS.md) utilisent une variable C
commune pour le pointeur choisi et un descripteur sélectionné dans le parent.
Le nettoyage des autres valeurs de la branche précède la réception. Le bilan
distingue les branches qui fournissent une allocation des branches faisant
`return` ; les types doivent coïncider sur les chemins qui continuent.
Les régressions sont dans `tests/test_if_expressions.py`.
Le [contrat des boucles](LOOPS.md) décrit l'analyse des reprises, les emprunts
utilisés dans les itérations suivantes, les nettoyages avant `break` ou `continue` et les
chemins qui ne reviennent pas. Les indicateurs sont activés au point d'usage,
dans chaque itération concernée, et leur contexte C est suivi pour ne pas
référencer une variable de l'appelant depuis une autre fonction. Les régressions
sont dans `tests/test_loops.py` et `tests/test_continue.py`.
Le [contrat de while](WHILE.md) ajoute le test dans le scope d'itération, ses
allocations et effets, la reprise du test après `continue`, et la jonction avec
les sorties par condition fausse, dont celle précédant toute exécution du corps.
Les régressions sont dans `tests/test_while.py`.

Les contrôles du runtime imposent aussi une cible avec un `int` C de 32 bits,
un alignement de pages compatible et des calculs de capacité contrôlés. La
vérification du curseur précède la soustraction de la capacité restante.

## Contre-exemples trouvés et corrigés

### Accès dupliqué après réception explicite

Ce programme était accepté :

```rust
let mut memory = allocator();
let mut a = new(memory) Int(1);
let mut b = {
    -> a;
    <- a;
};
let mut c = <- b;
print(a); // Ancien accès encore accepté à tort.
print(c);
```

Le transfert descendant utilisait le même objet de suivi pour l'accès du parent
et celui de l'enfant. Recevoir le retour dans `b` laissait donc `a` utilisable.
Cet exemple démontrait un écart à notre règle de déplacement ; il ne démontrait
pas à lui seul un accès à une mémoire libérée.

Le parent perd désormais son accès à l'entrée de l'enfant, qui reçoit un accès
distinct. Un retour reçu dans une nouvelle variable ne réactive pas l'ancien.
Le programme ci-dessus est rejeté sur `print(a)`.

Le cas déjà défini de retour ordinaire reste valide :

```rust
let mut a = new(memory) Int(1);
{
    -> a;
    <- a;
}
print(a); // Le retour restaure explicitement l'accès initial du parent.
```

### Bloc imbriqué dans un initialiseur

Un bloc utilisé dans un initialiseur d'Int pouvait provoquer un `KeyError`
Python : ses instructions n'avaient pas été indexées pour l'analyse.
La traversée des sous-expressions est désormais commune à l'indexation et à
l'analyse de dernière utilisation. Les constructions non typables produisent
un diagnostic vérifié, sans émission de C, au lieu de cette erreur interne.

L'audit a également ajouté des diagnostics bornés pour les entiers trop longs,
les chiffres non ASCII, les fins de source tronquées et les imbrications qui
dépassent la capacité du prototype.

## Résumés d'effets des fonctions

Le [contrat des effets](EFFECTS.md) décrit l'analyse symbolique des sources de
paramètres, des allocations et resets externes, et la propagation des sous-appels.
Les sources pouvant être réinitialisées déterminent les captures de nettoyage
C. Les types allouables sont vérifiés après substitution des sources réelles.
Les effets externes observés par l'analyse spécialisée doivent être inclus dans
le résumé inféré ; un écart fait refuser la compilation avant exécution du C.

Les sources locales ne sont pas confondues avec des paramètres de même nom.
Un reset interdit par un paramètre en lecture est détecté même dans une fonction
non appelée. Le passage sur les corps et les contrats opaques complètent cette
analyse pour les types, identités et durées de vie du sous-ensemble. Les exigences
de pools sont conservées même lorsqu'un sous-appel n'alloue rien. Les tests sont
dans `tests/test_effects.py` et `tests/test_pool_requirements.py` ; le
[rapport du cycle](POOL_REQUIREMENTS_VALIDATION.md) détaille preuves et limites.

## Résumés des résultats

Le [contrat des résultats](RESULTS.md) décrit les alternatives d'allocations
neuves et d'identités entrantes inférées sans appels concrets. Les paramètres
symboliques sont substitués aux arguments ; les sources possibles du résultat
sont protégées et son identité restituée est conservée quand elle est garantie.
Les racines d'origine sont suivies statiquement à travers les sélections, sans
comparer les adresses, notamment pour distinguer un slot réutilisé d'un objet
rendu. Les résultats de la spécialisation doivent respecter le contrat avant
compilation du C. Cela ne remplace pas les contrôles de déplacements et emprunts
ni la vérification mémoire complète des corps aux appels. Les régressions sont
dans `tests/test_results.py`.

## Contraintes entre sources

Le [contrat des relations de sources](SOURCE_CONSTRAINTS.md) décrit l'égalité
pour une destruction avec receveur explicite et les distinctions nécessaires
lors d'accès après des resets. Les historiques sont séparés dans les branches,
réunis sur les continuations et stabilisés sur les reprises de boucle. Les
sous-appels substituent leurs obligations et les résultats reçus vivants ne
sont pas invalidés par une application aveugle des resets possibles.

Chaque provenance possible doit satisfaire les contraintes à l'appel. Les
arguments préparés et usages futurs chez l'appelant restent protégés. Cette
analyse n'ajoute pas de contrôle runtime et ne remplace pas les contrôles
complets des emprunts et déplacements. Les tests sont dans
`tests/test_constraints.py`.

## Corps vérifiés sans appel réel

Le [passage de vérification des corps](FUNCTION_BODIES.md) donne à chaque fonction
des entrées symboliques respectant les modes, types et égalités de sources.
Il réutilise le vérificateur des déplacements, emprunts, branches, boucles et
sorties de scopes ; son état et son C temporaire sont isolés puis jetés.
Les régressions sont dans `tests/test_function_bodies.py`.

Ce contrôle détecte aussi les erreurs mémoire dans des fonctions inutilisées,
sans les émettre dans le C final. Les [appels par contrats](MODULAR_CALLS.md)
contrôlent modes, types, sources et transitions de l'appelant sans ouvrir les
corps appelés. Les sources concrètes sont vérifiées dans les instructions du
programme ou de `main`. Le backend spécialisé conserve un parcours de génération
avec ses contrôles de cohérence ; `check` s'arrête avant ce backend.
Cela ne constitue pas une preuve indépendante du vérificateur existant.

## Provenances multiples

Le [contrat des provenances](PROVENANCES.md) décrit les unions de sources dans
les retours et expressions `if`, leur propagation dans les appels et la
protection conservative de chaque source possible. Les durées de vie et types
sont vérifiés pour toutes ces sources. Les objets restent à leur adresse.

Après la dernière utilisation, un reset d'une source possible détruit l'objet
sélectionné seulement s'il appartient réellement à cette source. Les indicateurs
protègent les cellules déjà mortes ; les survivants restent suivis pour les
autres resets ou le nettoyage final. Les pools d'enum sont reconnus par leur
racine publique malgré la provenance physique du bras. Les tests correspondants
sont dans `tests/test_provenances.py`. Cela ne constitue pas encore une
preuve générale de validité des provenances ; le contrôle symbolique des corps
et des appels par contrats est décrit plus haut.

## Audit des correspondances avec le C

L'[audit ciblé du 2 novembre](AUDIT_MEMORY.md) a corrigé une lecture trop tardive
des champs d'enum dans le C et une perte d'identité lors du retour conditionnel
uniforme d'une allocation entrante. Le premier changeait une valeur calculée ;
le second refusait un aller-retour valide. Aucun des deux contre-exemples ne
démontrait un accès après libération. Les tests ajoutent un modèle indépendant
de l'ordre de destruction, ainsi que des combinaisons de boucles, emprunts et
transferts. Ils sont dans `tests/test_audit_regressions.py`.

## Tests et instrumentation

L'extension des [champs &Int](REFERENCE_FIELDS.md) ajoute les dépendances de
lecture aux allocations, aux emprunts préparés et aux contraintes des appels.
La [matrice](VERIFICATION_MATRIX.md) référence sa couverture bornée. Les graphes
transitifs restent non implémentés ; les retours contenant ces emprunts sont
contrôlés selon [BORROWED_RETURNS.md](BORROWED_RETURNS.md). Le
comportement conservateur des resets sur chemins divergents est maintenu.

Le contrat de nettoyage des sorties normales et des retours anticipés, avec
un exemple de traduction en C, est détaillé dans [SCOPE_EXIT.md](SCOPE_EXIT.md).
Les régressions correspondantes sont dans `tests/test_scope_exit.py`.

Résultats de validation, après ajout des retours contenant des champs empruntés :
605 tests réussis dans la suite standard et 605 tests réussis avec
`CRUST_SANITIZE=undefined`. L'oracle du runtime est inclus dans les deux
exécutions. Le détail des binaires instrumentés est précisé ci-dessous.
La [matrice des 66 règles](VERIFICATION_MATRIX.md) distingue couverture partielle,
examen de spécification et règles non implémentées. Le
[rapport des exigences de pools](POOL_REQUIREMENTS_VALIDATION.md) conserve les
résultats du modèle indépendant, des mutations et des contrôles C à plusieurs
niveaux d'optimisation. Le [cycle des champs &Int](REFERENCE_FIELDS.md) conserve
son modèle de dépendances, ses quatre mutations et ses douze exécutions C.
Aucune de ces mesures n'établit une preuve générale de sûreté.
Le [cycle des retours d'objets empruntants](BORROWED_RETURNS.md) ajoute le modèle
des frontières de scopes, les régressions de réemprunts et les campagnes relancées
après découverte d'un contre-exemple supplémentaire d'exclusivité.

Le [cycle des retours directs &Int](DIRECT_BORROW_RETURNS.md) porte ensuite la
suite à **632 tests réussis en mode standard et 632 sous UBSan**. Il ajoute
27 méthodes, un modèle borné de 24 routes (12 admises/12 refusées), cinq mutations
sélectionnées détectées et neuf précédentes rejouées, plus douze exécutions C
à plusieurs optimisations. Les [résultats bruts](../validation/direct-borrow-suites.json)
distinguent ces mesures des cycles antérieurs. Le retour ne reçoit aucune
responsabilité de destruction et ne prolonge pas la durée de vie de sa cible.

La [clarification des références existantes](REFERENCE_VALUES.md) remplace
ensuite les réemprunts écrits `&reference` par le nom de la référence dans les
appels et retours. **647 tests standard et 647 sous UBSan réussissent**,
avec 15 nouvelles méthodes, cinq mutations spécifiques et quatorze précédentes
détectées, et 36 exécutions C optimisées conformes. Les contrats, dernières
utilisations, drop/reset et frontières enfant → parent restent contrôlés.
Les références imbriquées sont refusées, sans aplatissement. Les
[résultats bruts](../validation/reference-values-suites.json) distinguent ce cycle
des mesures antérieures ; les oracles mémoire des fixtures migrées sont conservés.

Le [cycle let / let mut](LET_MUTABILITY.md) ajoute ensuite la mutabilité des
bindings et les écritures de contenu Int sans allocation. **672 tests standard
et 672 sous UBSan réussissent**, avec 25 nouvelles méthodes, 33 programmes
nouveaux admis et 50 refusés dans leur corpus, cinq mutations nouvelles et 19
précédentes détectées, et 48 exécutions C optimisées conformes. Les modèles de
contenu/capacité et le suivi de reset dans les contrats sont décrits dans le
[rapport brut](../validation/let-suites.json). Les compteurs des cycles précédents
restent historiques ; la suppression de var/global set ne modifie pas les
oracles mémoire attendus des fixtures migrées.

Les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) étendent ensuite B5 aux prêts
exclusifs. **700 tests standard et 700 sous UBSan réussissent**,
avec 28 nouvelles méthodes, un corpus de 28 programmes admis / 58 refusés,
29 fautes sélectionnées détectées et 60 exécutions C optimisées conformes.
Les retours ne créent ni objet ni responsabilité de nettoyage ; chaque cible
possible garde l'exclusivité et la vérification enfant → parent. Le dernier
usage d'un Int alloué après écriture de contenu a aussi été corrigé pour V4/U1.
Le [rapport brut](../validation/mutable-return-suites.json) distingue les mesures,
l'incident d'injection réparé et les limites de cette validation bornée.

```sh
# Suite complète, y compris compilations et exécutions C.
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q

# Régressions adversariales et oracle du runtime.
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_safety.py -v

# UBSan, avec arrêt au premier comportement indéfini détecté.
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q

# AddressSanitizer et UBSan, quand l'environnement les exécute correctement.
CRUST_SANITIZE=address,undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
```

Les options de sanitizer sont appliquées aux compilations C du harnais de tests
et à l'oracle. Les tests d'intégration invoquant la CLI construisent leurs
binaires avec les options habituelles de celle-ci ; ces binaires ne deviennent
pas instrumentés par cette variable de test.

L'oracle de `tests/test_safety.py` appelle directement le runtime, sans passer
par le générateur de C. Sur 3 000 opérations déterministes, il compare les
valeurs vivantes à une table de références et vérifie, après chaque opération :
unicité des slots vivants, compteurs, ordre physique, liste libre, alignement
des positions, bornes du curseur et récupération des suffixes. Il emploie deux
variantes de tailles différentes puis réinitialise et ferme l'ensemble.

Cette exploration est bornée. Elle ne couvre pas toutes les tailles, séquences,
plateformes ou conditions d'épuisement possibles.

Sur l'environnement de cet audit, AddressSanitizer n'a pas pu être validé :
l'oracle instrumenté expire après 10 secondes, et un programme C vide instrumenté
avec ASan expire également après 5 secondes, y compris hors du sandbox. Aucun
résultat « ASan réussi » ne doit être déduit de cet essai.

## Base de confiance et suites nécessaires

La base de confiance comprend le parseur, les analyseurs d’effets, de résultats et de contraintes, le vérificateur
mémoire Python, la génération C, le runtime, le compilateur C et les mécanismes mémoire du système. Modifier
le C généré ou lier manuellement du C arbitraire sort des garanties visées.

L'absence de fuite immédiate ne signifie pas que tout stockage mort est rendu
au système : les slots peuvent rester réservés pour réutilisation. Un arrêt sur
épuisement ne déroule pas les destructeurs. Cela fait partie des limites
explicites du prototype.

Avant de présenter le sous-ensemble comme établi sûr, il reste notamment à :

1. Formaliser les transitions de scopes, d'accès et d'emprunts, puis les relier
   aux opérations C émises.
2. Vérifier la conservation des propriétés à chaque forme d'expression et à
   chaque sortie de scope ; les invariants internes seuls ne suffisent pas.
3. Étendre l'exploration indépendante et faire fonctionner ASan sur une cible
   adaptée, notamment pour les allocations de tas et les limites des mappings.
4. Réévaluer ces obligations à chaque extension du langage : ajouter une
   fonctionnalité ne signifie pas étendre automatiquement les garanties.

## Champs contenant &mut Int

Les champs &mut Int conservent la capacité exclusive sur leurs cibles à travers
les déplacements et retours d'objets. Les références partagées vers un même
porteur retiennent cette capacité. Les projections mutables suivent la règle
du bras décrite dans [le cycle suivant](MATCH_MUTABLE.md). Chaque
frontière enfant → parent vérifie la durabilité sans promotion implicite.

Le cycle comporte 29 tests dédiés, 24 sources distinctes admises exécutées et
43 refusées par les deux stages. Un modèle indépendant de dernier usage exerce
24 scénarios ; 35 injections sélectionnées sur des copies sont détectées et
48 exécutions C couvrent O0/O2/Os/O2-UBSan. L'audit a corrigé un descripteur qui
perdait son type réel et pouvait faire accepter un emprunt W dans un champ Int.
Les mesures globales, les premières campagnes remplacées, les incidents et les
limites sont décrits dans [MUTABLE_REFERENCE_FIELDS.md](MUTABLE_REFERENCE_FIELDS.md).
Cela ne constitue pas une preuve générale de sûreté.

Les suites globales de ce cycle passent 729 tests chacune, en standard et dans
la configuration UBSan du harness, sans test ignoré. Les [mesures brutes](../validation/mutable-field-suites.json)
sont conservées ; cette instrumentation ne s'applique pas automatiquement à
chaque binaire construit via la CLI.

## Cycle du noyau numérique

Le profil numérique du [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau)
raccorde les types scalaires au parseur, au typage contextuel, aux contrats et
au backend C. Il utilise les représentations internes historiques d'Int et de
Bool pour les chemins qui les partagent. La syntaxe du profil utilise `i32`
et `bool`. Une source sans marqueur de type ou de syntaxe numérique peut
sélectionner explicitement le profil avec `--numeric-core`. L'inférence du
profil préserve les programmes historiques.

L'évaluation constante arrondit les flottants à partir d'une fraction exacte.
Le backend matérialise les opérandes dans l'ordre d'évaluation et contrôle les
bornes avant les conversions susceptibles de tronquer. Les opérations entières
utilisent les intermédiaires `__int128` de Clang. Le backend est exercé avec
les formats binaires IEEE à arrondi au plus proche, sur la cible de validation.
`try_from` réutilise `IntegerConversionError::OutOfRange` pour les échecs de
représentabilité, y compris lorsqu'un type flottant est impliqué.

- La [suite ciblée](../tests/test_numeric_core.py) passe ses 10 méthodes en
  [O0/UBSan](../validation/numeric-core-targeted-o0.log) et en
  [O2/UBSan](../validation/numeric-core-targeted-o2.log). Chaque passe vérifie
  21 variantes invalides aux deux entrées et exécute 19 programmes natifs,
  dont neuf qui doivent s'arrêter sur un diagnostic à l'exécution.
- La [régression O2/UBSan](../validation/numeric-core-regression.log) passe
  131 méthodes en 63,325 s. Les suites couvrent le noyau mémoire, les
  déplacements, les conversions historiques, le stockage, les enums locaux,
  les copies et sorties de boucle async et les tableaux fixes. Le test
  historique du drop d'un résultat attend désormais l'acceptation de
  `drop(u8::try_from(42))` en syntaxe moderne.
- Les commandes `check`, `run` et `effects` acceptent le programme sans
  annotation qui imprime la borne haute de `i64`, avec le profil forcé.
  [Journal CLI](../validation/numeric-core-cli.log)

Le typage des champs d'agrégats avec les nouveaux formats, les conversions et
allocations numériques portées par les tâches et les affectations composées
sur champs ou déréférencements restent à raccorder. Les affectations composées
exercées concernent les variables et les tableaux fixes. Le réemploi des pools
synchrones est mesuré par l'adresse et la valeur relue. La trace de destruction
historique affiche le champ entier du slot, qui ne contient pas la charge
numérique élargie. Les preuves sont limitées à ces exécutions et à cette cible.
