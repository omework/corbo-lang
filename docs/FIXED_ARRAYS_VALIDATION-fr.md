[English](FIXED_ARRAYS_VALIDATION.md)

# Validation des tableaux de taille fixe

## Cycle du 4 novembre 2026 — lignes contenant des références

Ce cycle implémente les lignes de références qui sont elles-mêmes accessibles
par des références stockées : par exemple `[&[&Int;2];1]` et
`[&mut [&mut Int;2];1]`, avec composition récursive. Il applique les règles
existantes E2–E7, B1–B5, D1, V4, S4–S5 et A2/A5. Aucune règle normative n'a été
modifiée. `mut()` reste explicitement exclu du prototype.

### Implémentation et traduction en C

Le vérificateur conserve un arbre de prêts : l'emprunt de la ligne, ses
références intérieures, puis les descendants éventuels. Les derniers usages
sont suivis par chemin d'accès. Une référence intérieure encore utilisée
protège sa cible et ses réservations, même si sa variable d'origine n'est
plus utilisée. Les tableaux de références mutables restent non copiables.

Le C conserve les structures de tableaux et les pointeurs de leur type exact.
Les allocations ne sont pas déplacées. Une traversée de pointeur de ligne
matérialise son adresse avant les indices et les effets suivants ; aucun
indice n'est réévalué. Les contrôles de bornes précèdent chaque accès.
Les pools et leur stratégie de slots ne changent pas.

Les contrats décrivent les références intérieures par chemins, tels que `0/1`.
Ils conservent les cibles retournées, les alias des lignes, les modifications
par case et les contraintes de sources. Le vérificateur applique ces contrats
sans reparcourir les corps appelés. Le backend C conserve sa spécialisation
existante des fonctions. Les tests comprennent un appel vérifié avec seulement
son contrat et un contrat forgé tentant de modifier une ligne partagée, refusé.

Les contrats séparent aussi les effets sur les lignes injectées à l'entrée de
la fonction de ceux du conteneur extérieur. Ces effets restent connus si ce
conteneur est consommé par transfert ou remplace son pointeur avant de finir.
Ce suivi est statique : il n'ajoute ni rétention ni allocation au runtime.

Les alias, les lignes projetées et les variables masquées par une déclaration
locale conservent leur lien avec le stockage d'origine. Les sorties de branches,
les résultats de loop, les reprises par continue et les retours réunissent les
provenances des références intérieures. Les transferts appliquent D1 à tous les
niveaux, sans promotion implicite d'un conteneur local.

### Contre-exemples et corrections

- Une référence extérieure pouvait conserver sa ligne sans conserver les prêts
  intérieurs. Les prêts actifs et les allocations retenues sont parcourus
  récursivement, avec les réservations des porteurs enum.
- Un résumé de branche pouvait conserver le pointeur de ligne et perdre son
  contenu référencé. Les jonctions et instantanés conservent les contenus et
  les derniers usages intérieurs ; la clé de convergence de boucle les inclut.
- Une mise à jour de référence intérieure pouvait ne modifier que la vue
  empruntée. Les postconditions sont propagées jusqu'à la ligne d'origine.
- Le remplacement d'une référence de ligne doit rendre l'ancienne ligne avec
  son contenu et installer la nouvelle avec ses propres cibles. Remplacer un
  pointeur vers une ligne partagée ne signifie pas modifier cette ligne.
- Le parcours d'une ligne ne doit pas compter comme lecture de toutes ses
  références intérieures. Les tests permettent le reset d'une cible après son
  dernier accès, tout en conservant l'accès à une autre case vivante.
- Un réemprunt retourné doit conserver la réservation de la case intérieure
  effectivement utilisée chez l'appelant. Les projections de paramètres ne
  doivent pas effacer cette capacité nommée.
- **Écart confirmé entre les stages :** une fonction retournant `&mut g[1]`
  perdait le décalage de la ligne dans l'analyse des contrats. Un relais qui
  écrivait dans cette ligne attribuait l'écriture à g[0]. `verify_program`
  acceptait alors un reset invalide avant la lecture de g[0], tandis que
  `compile_source` le refusait pendant la spécialisation. Le remappage des
  positions à travers le retour corrige cet écart. Le cas invalide est maintenant
  refusé aux deux stages et le cas valide produit les valeurs attendues.

- Un autre contre-exemple concernait un tableau extérieur consommé après
  écriture dans une ligne empruntée, puis remplacement de son pointeur. Le
  résumé confondait l'écriture du référent et le changement du pointeur. Avec
  deux allocations distinctes dans le même pool, verify_program acceptait un
  drop de la cible encore utilisée, alors que compile_source le refusait.
  Les effets conservent maintenant les lignes injectées initiales ; remplacer
  leur pointeur ne réécrit pas leurs références. Le contre-exemple est conservé
  dans test_transferred_outer_container_preserves_writes_to_parent_rows.
- Une passe globale a échoué sur dix sous-cas de diagnostic relatifs aux
  porteurs réservés. Les programmes étaient refusés, mais l'itération d'un
  ensemble choisissait parfois une contrainte générique avant celle du porteur.
  L'ordre de vérification est désormais déterministe, avec priorité aux
  réservations. Les tests existants ont été conservés.

Le contre-exemple de projection est reproduit dans
`test_returned_inline_row_projection_updates_only_its_actual_slots` de
`tests/test_nested_reference_rows.py`. Les régressions des cycles précédents
restent exécutées : ordre des arguments, branches, retours, transferts,
remplacements des receveurs, prêts temporaires, stabilité des adresses,
nettoyage et réutilisation des slots.

### Preuves d'exécution

La suite globale a exécuté 909 tests distincts sans échec en quatre groupes
de 229, 320, 178, 182 tests, en 247,446, 217,203, 190,072, 200,523
secondes respectivement. Le total correspond à la découverte courante, avec
909 identifiants uniques.

Les 68 tests existants ciblant les tableaux passent sans instrumentation en
12,305 secondes ; les 22 nouveaux passent en 5,893 secondes. Les 90 tests passent
aussi sous UBSan à -O2 en 88,567 secondes, avec
101 invocations acceptées et 194 invocations refusées du vérificateur.

Les tests de diagnostic des porteurs réservés ont aussi été rejoués avec
PYTHONHASHSEED=0 et PYTHONHASHSEED=1 : 9 tests passent dans chaque configuration,
en 12,397 et 12,488 secondes. Ces répétitions ne sont pas ajoutées au nombre de
tests distincts de la suite globale.

Les programmes acceptés des suites ciblées compilent le C avec Homebrew Clang 20.1.3, C11 et les
avertissements traités en erreurs. Ils comparent les valeurs et les traces de
destruction. Les refus sont vérifiés avec verify_program et compile_source
pour les nouveaux contre-exemples, ainsi que directement depuis un contrat
opaque pour le cas readonly forgé. Les compteurs sont des invocations du
vérificateur, pas des programmes uniques ; ils excluent les échecs du parseur
et les vérifications directes des blocs d'appelants opaques.

UBSan utilise -O2 et -fno-sanitize-recover=all. Les diagnostics de sanitizer
font échouer le test. Aucune réussite ASan nouvelle n'est revendiquée : les
sondes d'un cycle précédent dépassaient les délais avec Homebrew Clang et
Apple Clang, même pour un programme indépendant limité à puts.

### Modèles indépendants et mutations

Le modèle de destinations imbriquées utilise des indices de listes Python :
24 opérations déterministes avec la graine 20261107, comprenant copy, replace,
swap et lectures. Il calcule les valeurs attendues sans consulter le compilateur.
Le modèle de fenêtres de drop énumère 12 configurations : profondeurs 1, 2 et 3,
deux cibles libérables et deux cibles lues. Il exige le refus si la cible lue
est libérée : 6 programmes admis exécutés et 6 refusés aux deux stages.

Les modèles précédents restent exécutés : 90 opérations sur les valeurs
(graine 20261104), permutations/remplacements de références scalaires
(graine 20261105), et 40 opérations sur les références de lignes de valeurs
(graine 20261106). Les modèles de slots et de destructions historiques sont
également présents dans la suite globale.

Les 15 mutations contrôlées sont détectées :

- 8 par acceptation indue d'un programme ou contrat interdit ;
- 6 par refus d'un programme valide ;
- 1 par comportement observable incorrect après un accès hors limites.

Elles visent les bornes, les prêts actifs et intérieurs, les séparations entre
cases, les provenances, les alias, les anciens réemprunts, les postconditions,
le contenu des contrats, les derniers usages, les lignes partagées, le
remappage des projections et les effets après transfert.

Une mutation de propagation avait d'abord survécu au scénario choisi : l'effet
sur la ligne était aussi propagé par le résumé des référents injectés. La même
mutation a été rejouée sur le test existant qui remplace le pointeur extérieur,
où cette propagation est nécessaire. Elle est alors détectée par un faux refus
du programme valide. Aucun oracle n'a été modifié pour faire réussir la suite.

Les substitutions, noms de tests et diagnostics sont conservés dans
`validation/fixed-array-current-mutations.json`. Le lanceur reproductible
`validation/run_fixed_array_mutations.py` travaille sur des copies temporaires
et garde les oracles inchangés. Cet échantillon de mutations choisi ne mesure
pas un taux général de détection.

Les groupes de régression, les compteurs et les empreintes SHA-256 des sources
sont conservés dans `validation/fixed-array-current-global.json` et
`validation/fixed-array-current-suite.json`.

### Reproduction

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_fixed_arrays.py -q
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_nested_reference_rows.py -q
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined CRUST_ARRAY_OPT=-O2 PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_fixed_arrays.py -q
CRUST_SANITIZE=undefined CRUST_ARRAY_OPT=-O2 PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_nested_reference_rows.py -q
python3 validation/run_fixed_array_mutations.py
```

### Limites et réexamen des interactions

Les règles d'intention et de type (I/V), de scope et de contrôle (S/T/U), de
prêt et de durabilité (B/D), de destruction et de source (L/A/P) ont été
réexaminées pour ces références récursives. Leurs régressions sont exécutées
ensemble. Le runtime des pools conserve ses invariants et modèles existants ;
ce cycle modifie le suivi statique et le C des tableaux, pas son allocator.

Les modèles indépendants ne constituent pas un oracle complet des durées de
vie : le modèle de drop ne couvre que ses 12 configurations. Les alias et les
mutations de contrats sont exercés par des programmes choisis. Les profondeurs
arbitraires, toutes les combinaisons de jonctions, la convergence générale et
la complétude des refus/admissions ne sont pas prouvées. L'analyse reste
conservative pour les projections ambiguës. Les tailles extrêmes du backend
C ne sont pas exercées. Les types et fonctionnalités hors prototype — traits,
FFI, concurrence et tailles dynamiques notamment — restent hors du cycle.

Ces résultats sont des preuves limitées aux scénarios exécutés. Ils ne
constituent ni une preuve formelle ni une garantie générale de sûreté du langage.
