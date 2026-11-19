[English](ASYNC_LOCAL_STRUCT_HELPERS_CYCLE.md)

# Réception locale de structures depuis un helper synchrone en async

## Règles et périmètre

Ce lot applique les règles déjà retenues des brouillons 03 et 05 : une
structure locale T utilise la data stack implicite du receveur ; elle conserve
son adresse pendant le transfert. Les règles de copie ST17/ST18 du brouillon 07,
les transferts T1/T6, les emprunts B1/B2/B4a et le nettoyage L1/L2/L6/L7 restent
applicables à travers AS8/AS9/AS12. Aucune règle normative n'est modifiée.

Le cas `validation/open-async-local-owned-struct-helper.crust`, refusé au cycle
précédent, est maintenant exécutable. Le helper reçoit A<Int>, construit un
Holder local contenant cette allocation, puis rend ce Holder au scope courant
de la tâche. La tâche peut le conserver à travers yield, lire son champ et
le détruire. Le stockage du Holder appartient au receveur ; celui du champ
appartient toujours à son pool. Il ne s'agit pas d'un A<Holder> nouvellement
alloué dans un pool implicite.

Les structures admises sont les familles fixes déjà représentées par le
backend async, sans champs empruntés. La copie concerne celles qui sont Copy,
notamment les structures de champs Int ; un champ propriétaire reste non Copy.
Ce lot ne termine pas les transferts de ces valeurs entre scopes ou tâches.

## Implémentation

- Un appel à résultat local reçoit un argument interne `Source *` qui désigne
  la data stack du scope receveur dans l'état async. Le bridge réserve la cellule
  de résultat avant d'invoquer le helper et réutilise le mécanisme existant de
  réservation du backend synchrone. Le helper ne détruit pas ce stockage.
- La stack est créée lors du premier appel concerné dans le scope. Elle utilise
  le défaut existant de 16 Mio de plage virtuelle. Les destructions des valeurs
  précèdent sa fermeture, au retour normal comme au nettoyage suspendu. Les
  reprises de boucle créent/nettoient le stockage de l'itération effective.
- Les sources de résultat et de champs sont conservées dans l'analyse locale.
  Les emprunts et drops suivent la dernière utilisation ; un paramètre A<T>
  explicite et une annotation A<T> refusent une valeur locale T.
- Un même helper dispose de bridges spécialisés selon les paramètres locaux
  ou issus de pools. Le contrôle de l'appel reste fondé sur le contrat ; la
  spécialisation transmet les faits de stockage au backend du helper. Cela
  permet aussi la copie depuis un paramètre partagé &Point.
- Les méthodes partagées/mutables peuvent recevoir directement un Point local.
  Leur emprunt implicite de receveur respecte `let mut`.
- Une réaffectation ne convertit plus une valeur locale T en A<T>, ni l'inverse.
  La provenance du receveur est conservée avant l'évaluation du membre droit.

## Défauts et contre-exemples

La première réception passe dans `validation/async-local-struct-helper-initial.log`.
La sonde de copie suivante produisait la valeur 7 attendue, mais détruisait la
copie comme un scalaire (`destroy q=0`) : la description de Point était perdue.
La spécialisation de provenance corrige ce défaut. Les observations avant/après
sont conservées dans `async-local-struct-helper-copy-probe.log` et `copy-second.log`.
Cette sonde a été exécutée pendant le développement du lot, après ouverture du
chemin jusque-là refusé ; elle ne décrit pas un programme exécutable avant le lot.

La première suite de huit méthodes avait deux échecs : l'emprunt d'un receveur
local utilisait encore l'accès scalaire, et un test essayait de créer un
Pool<Point> dans async, fonctionnalité encore ouverte. Le premier chemin est
corrigé. Le test de double spécialisation construit désormais le pool dans main
et transmet son allocation à la tâche, sans prétendre couvrir la construction
async de ce pool. La seconde suite de huit méthodes passe en 5,660 s.

La première version du contre-exemple de réaffectation était refusée pour
absence d'usage explicite de l'ancienne valeur ; ce refus est conservé dans
`validation/async-local-struct-helper-replacement-counterexample.log`.
Le programme affiné `validation/rejected-async-local-pool-replacement.crust`
lit les deux valeurs avant le remplacement. Dans une copie temporaire du code
sans la garde de distinction T/A<T>, les deux stages l'acceptent. Le code final
le refuse pour le bon motif, ainsi que la substitution inverse. Aucun binaire
de ce programme mal typé n'a été exécuté. Journal :
`validation/async-local-struct-helper-replacement-counterexample-refined.log`.

## Vérifications exécutées

Les commandes natives utilisent Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan bloquant. Les fichiers de tests sont
`tests/test_async_local_struct_helpers.py` et
`tests/run_async_local_struct_mutations.py`.

- **11 méthodes ciblées** passent à O0 en 15,507 s, journal
  `validation/async-local-struct-helper-corrected-o0.log` ; la baseline finale
  O2 passe les mêmes onze méthodes en 15,780 s dans la campagne de mutations.
  Elles exécutent 18 programmes/sondes natifs et vérifient sept programmes
  invalides dans chacun des deux stages (14 contrôles de refus).
- Le modèle de nettoyage compare trois préfixes indépendants d'une boucle :
  k itérations terminées impliquent k fermetures ; le nettoyage de l'itération
  suspendue en ajoute exactement une. Les compteurs C et destructions concordent.
  D'autres essais couvrent 0/1/3 itérations, continue, break et return.
- Deux sondes supplémentaires vérifient la terminaison et le nettoyage suspendu
  d'un Point local. Elles contrôlent le stockage non pool, la cellule vivante,
  la valeur, les métadonnées Point, la destruction unique et une fermeture.
  Le harnais détient exclusivement une tâche non lancée : aucune opération
  d'annulation publique n'est ajoutée.
- Les programmes source couvrent deux résultats simultanés, le remplacement,
  la copie propriétaire et partagée, les bridges local/pool d'un même helper,
  les méthodes, les annotations et les prêts à travers yield.
- Une régression élargie de **120 méthodes** passe en 97,758 s avant la dernière
  garde T/A<T> de réaffectation :
  `validation/async-local-struct-helper-regression-o2.log`.
- Sur le code final, **50 méthodes** passent à O2 en 50,733 s : appels
  propriétaires synchrones, structures propriétaires dans les bridges async,
  réception locale et retours async de structures. Journal :
  `validation/async-local-struct-helper-final-regression-o2.log`.
  Le programme minimal de réaffectation a été affiné pendant cette exécution ;
  la baseline finale séparée des onze méthodes vérifie ensuite les deux sens
  de substitution avec la version finale du test.

Les premiers journaux `suite-initial-o0`, `suite-second-o0`, `suite-third-o0`,
`model-o0` et `final-o0` sont conservés. `final-o0` et la première campagne
`mutations-complete-o2` contiennent les échecs d'attendus causés par le premier
snippet de réaffectation, avant son affinage ; ils ne sont pas présentés comme
des passes réussies.

## Mutations

La première campagne de quatre fautes détecte trois mutations et en laisse une
inconclusive : effacer la provenance locale produit d'abord un avertissement C
de réservation inutilisée, rendu bloquant par Werror. Journal :
`validation/async-local-struct-helper-mutations-o2.log`.
Dans le mutant seulement, une expression `(void)` neutralise cet avertissement
pour atteindre son comportement runtime erroné. Les assertions détectent alors
la copie incorrecte/réservation inutilisée. La campagne intermédiaire de quatre
fautes réussit dans `mutations-final-o2.log`.

La campagne finale détecte **cinq fautes** après baseline réussie : absence de
réservation chez l'appelant, perte de provenance locale, oubli de fermeture
suspendue, passage d'un T local à un paramètre A<T>, et disparition de la
distinction T/A<T> au remplacement. Les copies sont isolées, les oracles ne sont
pas modifiés. Journal :
`validation/async-local-struct-helper-mutations-corrected-o2.log`.
La faute de réservation est détectée par refus d'un programme valide ; cette
détection n'est pas présentée comme une corruption mémoire exécutée.

## Écarts et limites

Les résultats actuels des deux stages sont enregistrés dans
`validation/async-local-struct-helper-open-limits.log` :

- `open-async-local-helper-parent-transfer.crust` : un résultat construit dans
  un bloc enfant doit pouvoir rejoindre son parent. Il est encore refusé parce
  que le stockage du receveur parent n'est pas réservé par ce chemin async.
  Le diagnostic parle actuellement de pool local alors que la source est une
  data stack ; le programme est valide selon les règles, pas normativement interdit.
- `open-async-local-helper-child-capture.crust` : transmettre le Point local à
  une tâche enfant et l'attendre est valide. Ce chemin reste explicitement
  refusé, car la distinction local/pool ne traverse pas encore les signatures
  d'états enfants. Elle est nécessaire notamment pour une copie dans l'enfant.

Le retour d'un objet local hors de la tâche exige également l'injection du
stockage du receveur extérieur. Les structures contenant des emprunts, les
constructions directes et les pools de structures dans les états restent
ouverts. La restitution après remplacement d'un champ propriétaire dans un
helper reste l'écart consigné au cycle précédent.

Le placement actuel couvre la réception dans le scope courant, sans prétendre
réaliser le placement général parent/enfant du brouillon 03. Les sondes sont
finies, sans preuve générale de sûreté ni nouveau résultat ASan/TSan.
Tous les processus cités sont terminés. Les modules modifiés et les tests
passent `py_compile`; les diffs sont archivés dans
`validation/async-local-struct-helper-*.py.patch` par rapport à
`/tmp/crust-before-async-local-struct-helper/`. L'objectif global reste ouvert.
