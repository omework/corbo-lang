[English](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md)

# Résultats locaux async contenant des champs propriétaires

## Règles et portée

Ce lot applique les brouillons 03/04/05, L7, T1/T6, V5, D1, ST7/ST15 et
AS8–AS14. Aucune règle normative n'est modifiée. Le programme conservé dans
`validation/open-async-result-storage-owned.crust` est désormais compilé et
exécuté : une racine Holder locale est construite dans le stockage du receveur,
avec un champ A<Int> dont le pool reste distinct et doit survivre au résultat.

Le raccordement couvre les racines locales fraîches avec des champs provenant
de paramètres transférés ou de pools injectés, dont les graphes finis imbriqués
représentés par les contrats existants. La racine garde son type T ; elle ne
se transforme pas en A<T>. Aucun pool ni descendant local inconnu n'est promu.

## Implémentation

- Le contrat du résultat distingue la destination de la racine et les sources
  de chaque chemin propriétaire. Un paramètre transféré portant un arbre est
  développé en chemins de descendants lorsqu'on applique ce contrat.
- L'inférence de terminaison accepte les captures de graphes propriétaires
  finis sans références. Elle conserve séparément les effets de suspension ;
  les agrégats empruntants ne deviennent pas implicitement pris en charge.
- Les producteurs de résultats locaux sont suivis à travers tâches nommées,
  relais, fabriques, spawn, join et extraction de la branche Ok. Seule la racine
  nouvellement construite reçoit la destination de l'ancêtre.
- Les fabriques conservent cette destination dans les sources de la tâche et
  dans celles de son résultat. Les sources des descendants restent indépendantes.
- Les contrats backend retiennent les pools des descendants après attente.
  Un résultat ne peut sortir d'un bloc qui ferme l'un de ces pools.

## Contre-exemples et étapes intermédiaires

Le premier raccordement acceptait le cas direct, mais les tests ont retrouvé
le refus des transferts vers le parent et des fabriques : le plan de placement
exigeait un résultat sans dépendance de source. Il reconnaît maintenant la
racine fraîche d'un graphe complet, sans déplacer les descendants.

Le graphe Root -> A<Leaf> -> A<Int> a exposé deux lacunes supplémentaires :
l'inférence excluait tous les paramètres agrégés propriétaires et le contrat
appliqué ne développait pas les petits-enfants d'un paramètre entier. Ces deux
raccordements sont ajoutés. Une autre sonde valide, retournant le résultat d'un
join hors d'un bloc enfant, révélait l'absence de suivi spawn/join/Ok dans le
plan de placement ; ce chemin est maintenant suivi.

Les journaux `initial-o0`, `expanded-o0`, `contracts-o0`, `source-model-o0` et
les sondes `nested-probe`/`nested-contract` conservent les refus initiaux.
Deux fixtures ont été corrigées selon les règles inchangées : un diagnostic
« non durable » admis pour le pool trop court, et `a ->;` à l'entrée du bras
qui consomme un paramètre de son parent. Aucun attendu mémoire n'a été affaibli.
Aucune acceptation dangereuse du compilateur non muté n'a été identifiée par
ce lot ; les premiers échecs sont des refus de cas admis ou des fixtures.

## Preuves exécutées

- Suite finale O0 : **12 méthodes réussies**, 15,103 s ; **19 exécutions natives**,
  **19 programmes invalides refusés aux deux étapes**, soit 38 contrôles.
  Journal : `validation/async-local-owned-result-graphs-counted-o0.log`.
- Baseline finale O2 : 12 méthodes réussies, 15,279 s ; **huit mutations
  détectées**, aucune survivante/inconclusive.
  Journal : `validation/async-local-owned-result-graphs-mutations-o2.log`.
- Mutations historiques des pools : baseline de 15 méthodes réussie, 18,092 s,
  puis huit mutations détectées. Les ancres des deux appels de projection de
  contrat ont été mises à jour ; les tests et oracles restent inchangés.
  Journal : `validation/async-local-owned-result-graphs-pool-mutations-o2.log`.
- Régression élargie : **180 méthodes réussies**, O2, 136,500 s. Ce passage a
  chargé le code avant le complément spawn/join du plan de placement et l'ajout
  de la destination aux sources de tâche des fabriques.
  Journal : `validation/async-local-owned-result-graphs-regression-o2.log`.
- Passage final après ces deux compléments : **63 méthodes réussies**, O2,
  49,275 s, couvrant stockage, relais, fabriques, retours propriétaires et le
  présent lot. Journal : `validation/async-local-owned-result-graphs-final-placement-o2.log`.

Tous les processus finaux cités sont terminés avec code 0. Les campagnes
ciblées et de mutations comprennent également les deux derniers compléments.
Les exécutions natives utilisent Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal, O0/O2 selon le journal. Les mutations restent
confinées à des copies temporaires, sans changer les oracles.

Le modèle de durée de vie énumère les quatre dispositions des deux pools
(ancêtre/enfant), à travers un appel direct, une fabrique et un relais async.
Seule la disposition où les deux pools survivent au receveur est admise.
Les séquences de remplacement contrôlent le nombre exact de destructions
pour une et trois itérations. Deux sondes C observent l'adresse de la racine,
son pool distinct de celui du descendant, le pointeur du champ, la libération
du slot d'état enfant et le nettoyage normal ou suspendu. Les tests couvrent
aussi les branches, les prêts du résultat, le réemploi des slots, les tâches
inactives et un échec de lancement injecté.

Les fautes injectées retirent les dépendances des descendants, les champs du
contrat direct, les chemins des petits-enfants, la destination dans une fabrique,
le placement au parent et l'inférence du graphe ; une autre ferme indûment le
stockage externe. Les détections comprennent refus indus et fautes de sûreté.
Ces huit cas ne mesurent pas la couverture générale du compilateur.

## Limites conservées

Complément ultérieur : les racines locales contenant des emprunts sont
maintenant raccordées dans le périmètre décrit par
[ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md](ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md).
Les constats ci-dessous décrivent l'état à la clôture de ce lot historique.

Les deux étapes refusent encore les exemples ouverts de racine locale contenant
un emprunt, de projection à travers plusieurs A<T>, et de restitution après
remplacement d'un champ propriétaire. Constats reproduits dans
`validation/async-local-owned-result-graphs-remaining.log`. Ce sont des écarts
d'implémentation, pas de nouvelles interdictions normatives.

Les graphes mixtes, les sources locales de descendants non résolues, les
signatures générales et les deux décisions relatives aux handles restent
ouverts. `reset()` reste absent du prototype. Pas de nouvelle mesure ASan/TSan,
ni preuve générale de sûreté, d'absence de course ou d'optimalité de placement.

Snapshot : `/tmp/crust-before-async-local-owned-result-graphs`.
Diffs : `validation/async-local-owned-result-graphs-*.py.patch`.
L'objectif complet reste actif et incomplet.
