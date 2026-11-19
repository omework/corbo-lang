[English](SELECT_SOURCE_CYCLE.md)

# SL1 — Select depuis le langage source

## Portée

Ce lot raccorde la syntaxe et les contrats du lot
[précédent](SELECT_CONTRACTS_CYCLE.md) au vérificateur de captures, aux états
générés et au runtime. Les règles SL1, AS2–AS15, B1/B2/B4/B5, T1/T2/T11 et
L1/L2 restent inchangées. AGENTS.md et VALIDATION_GUIDELINES.md sont suivis.

`runtime::select(-> ...)` est désormais exécutable dans les corps async pour
les familles décrites ci-dessous. Ce statut remplace la restriction de
compilation source indiquée dans les rapports historiques, sans changer leurs
résultats d'exécution passés. Ce lot ne termine pas l'ensemble du chantier async.

## Implémentation

- Les arguments sont évalués de gauche à droite. Les tâches déjà construites
  ont un responsable temporaire de nettoyage pendant l'évaluation des arguments
  suivants, y compris si celle-ci suspend ou quitte le bloc.
- Le constructeur vérifie les captures dès leur création et exige un type
  de résultat identique. Les branches peuvent être des tâches nommées,
  des appels directs ou des tâches produites par des blocs, if et boucles.
- L'attente exige une liaison mutable et produit un seul résultat. L'état
  « déjà attendu » suit les renommages et transferts. Les captures des
  perdantes restent réservées jusqu'au nettoyage de Select.
- L'état de Select et ses entrées de branches restent dans des membres stables
  de l'état async. Un transfert choisi par if ou break transmet un pointeur
  vers cet état, sans déplacer les états des branches ni leurs allocations.
- Les transferts vérifient la durée de vie des cibles et des pools. Les
  alternatives de captures sont réunies ; les provenances du résultat sont
  conservées après drop de Select.
- Le nettoyage fonctionne à la fin des blocs, aux sorties anticipées et aux
  suspensions d'une sélection imbriquée. La prévalidation des nettoyages
  suspendus inclut ses branches, sans ajouter d'attente cachée d'un handle.
- Le code C du mécanisme Select est inclus lorsque le programme en construit
  un. Le dimensionnement existant compte les emplacements des tâches conservées.

## Contre-exemple et renforcement des tests

Le transfert source d'une sélection depuis un bloc était refusé avant le lot.
La reproduction avec la copie précédente d'async_lowering.py et l'acceptation
après correction sont conservées dans
`validation/select-source-before-transfer-counterexample.log` ; le programme
est `validation/select-source-block-transfer.crust` et sa famille est exécutée
par les tests des transferts. L'exemple complet `examples/select.crust` passe
également par la CLI : `validation/select-source-cli-final.log`, sorties 20
puis 9, destruction unique de nombre.

Le programme
[select-immutable-shadow-counterexample.crust](../../validation/select-immutable-shadow-counterexample.crb)
était accepté à tort : une sélection mutable détruite dans un bloc laissait
son nom dans l'ensemble des liaisons mutables. Une nouvelle liaison immutable
du même nom pouvait alors être attendue. La sortie du scope retire maintenant
cette information. Le programme est refusé dans les deux stages ; le voisin
avec `let mut` est exécuté. La mutation qui réintroduit la fuite de mutabilité
est exercée séparément.

Une mutation réinitialisant l'état d'attente à la jonction des branches a
survécu à la première campagne. Le test ne traversait qu'un bloc simple. Il
couvre désormais aussi deux branches ayant chacune attendu leur Select, puis
le refus d'une deuxième attente du résultat transféré. L'oracle reste la règle
d'attente unique ; aucun comportement normatif n'est modifié.

## Scénarios et preuves

`tests/test_select_source.py` contient maintenant vingt-quatre méthodes. Elles couvrent les
captures partagées et mutables, les transferts conditionnels et par boucle,
les emprunts retournés, les propriétaires retournés depuis deux pools,
l'attente unique, la construction inactive, les sorties break/continue,
le réemploi, les nettoyages suspendus et les modifications de champs laissées
par une perdante. Les résultats Int, Bool, u8, char, &str et tableaux fixes
sont exécutés ; cela ne vaut pas couverture de tous les types du langage.

Un modèle indépendant choisit le premier résultat parmi deux branches avec
zéro, une ou deux pauses. Il utilise seulement deux compteurs de pauses ;
aucun contrat ni objet interne du compilateur. Les neuf combinaisons comparent
la valeur rendue, les destructions uniques des deux captures et le réemploi
du pool. Les modèles de réveils et d'effets de champs des lots précédents
restent distincts de ce modèle volontairement limité aux `yield`.

Le harnais natif utilise Clang C11, pthread, Wall/Wextra/Werror et UBSan fatal,
à O0 ou O2 selon le journal. Les tests refusés passent par `verify_program`
et `compile_source`. Les tests de mutations travaillent sur des copies
temporaires du compilateur avec les mêmes oracles.

Journaux déjà terminés :

- `validation/select-source-initial-o0.log` : neuf méthodes, 5,098 s, OK.
- `validation/select-source-transfers-initial-o0.log` : douze méthodes,
  6,762 s, OK.
- `validation/select-source-expanded-initial-o0.log` : dix-sept méthodes,
  trois erreurs de fixtures conservées. Elles utilisaient print(Bool), une
  conversion Int vers u8 non exacte et un littéral char non pris en charge.
  Les fixtures utilisent maintenant une condition booléenne, un littéral
  contextuel u8 et la conversion explicite par char_at.
- `validation/select-source-expanded-o0.log` : dix-sept méthodes,
  10,626 s, OK après correction des fixtures.
- `validation/select-source-computed-initial-o0.log` : vingt méthodes,
  15,810 s, OK.
- `validation/select-source-regression-contracts-o2.log` : 76 méthodes,
  24,119 s, OK. Ce passage précède le renforcement final du test d'attente
  après jonction ; il comprend les vingt tests source, seize contrats Select,
  quinze contrats de suspension et vingt-cinq contrats de champs async.
- `validation/select-source-mutations-initial-o2.log` : baseline réussie ;
  six mutations classées détectées, une survivante décrite plus haut et une
  classée inconclusive. Cette dernière provoquait effectivement l'arrêt natif
  `internal error: source still has live allocations` ; le classificateur
  confondait ce diagnostic du runtime avec une erreur de compilation C.
  La classification distingue maintenant ce diagnostic.

- `validation/select-source-final-o0.log` : vingt méthodes, 31,867 s, OK ;
  46 exécutions natives admises et 34 programmes refusés dans les deux stages
  (68 contrôles). Les cas se recouvrent avec les passages antérieurs.
- `validation/select-source-mutations-final-o2.log` : baseline de vingt
  méthodes réussie et huit fautes détectées : perte des prêts des perdantes,
  oubli de l'attente unique, fuite de mutabilité, omission du nettoyage normal
  ou suspendu, perte de durée de vie au transfert, perte des cibles retournées,
  oubli de l'état déjà attendu à la jonction.
- `validation/select-source-cleanup-mutations-o2.log` : baseline de dix
  méthodes réussie et huit fautes antérieures de nettoyage détectées.
- `validation/select-source-contract-mutations-o2.log` : baseline de seize
  méthodes réussie et huit mutations des contrats Select détectées.
- `validation/select-source-runtime-mutations-o2.log` : baseline de sept
  méthodes réussie et sept mutations du mécanisme Select détectées.
- Compilation Python des fichiers modifiés réussie. Les différences avec la
  copie antérieure au lot sont conservées dans
  `validation/async_lowering-select-source.patch`,
  `validation/async_runtime-select-source.patch` et
  `validation/crust-select-source.patch`.

La régression runtime élargie est terminée :
`validation/select-source-regression-runtime-o2.log`, 292 méthodes,
542,077 s, OK. Elle a chargé le code avant les deux compléments ci-dessous.

## Complément : branches impossibles à poller

Le programme [open-select-source-unpolled-contract.crust](../../validation/open-select-source-unpolled-contract.crb)
rend 1 dans sa première branche. La branche récursive suivante ne peut donc
jamais être pollée. Le contrat symbolique le savait déjà, mais le backend
demandait son résumé de suspension et refusait le programme. Les deux refus
initiaux sont conservés dans `validation/select-source-next-gap.log`.

Le backend exploite maintenant cette frontière : une branche dont tous les
contrats possibles excluent la suspension empêche de poller les suivantes.
Leurs captures restent néanmoins retenues pour le nettoyage. Les cibles du
résultat viennent uniquement des branches atteignables pouvant terminer.

Les alternatives de sélections issues de if et break conservent chacune leur
propre ordre de branches. Les concaténer en une seule liste ferait masquer
une alternative par la première branche prête d'une autre. Le test vérifie
la valeur du champ modifié sur les deux chemins, ainsi que le refus d'une
mutation prématurée de sa cible dans l'état async.

- `validation/select-source-poll-paths-initial-o0.log` : vingt-deux méthodes,
  34,084 s, OK ; avant le renforcement du contrôle local de champ.
- `validation/select-source-poll-paths-field-o0.log` : le contrôle renforcé
  passe séparément, 3,397 s.
- `validation/select-source-poll-paths-mutations-o2.log` : neuf mutations
  classées détectées et une inconclusive. Cette dernière réintroduit le refus
  connu du programme valide avec branche non pollée. Le harnais rapporte
  maintenant ce refus explicite comme un échec d'assertion du cas admis,
  distinct des exceptions internes du compilateur ; l'attente reste inchangée.
- `validation/select-source-poll-paths-final-mutations-o2.log` : baseline de
  vingt-deux méthodes, 39,275 s, OK ; les dix mutations sont détectées.
- `validation/select-source-poll-paths-final-o0.log` : vingt-deux méthodes,
  42,715 s, OK ; 51 exécutions natives et 43 programmes refusés dans les deux
  stages, soit 86 contrôles de refus.
- `validation/select-source-poll-paths-regression-o2.log` : 95 méthodes,
  73,991 s, OK. Ce passage précède uniquement l'explicitation de l'assertion
  d'acceptation du harnais ; le compilateur et les attentes sont identiques.

La régression runtime de 292 méthodes a chargé le code avant ce complément.
La nouvelle sélection de régression inclut les contrats, le backend Select et
les nettoyages suspendus sur le code après complément. Il ne faut pas attribuer
les anciens résultats à une version qu'ils n'ont pas exécutée.

## Complément : captures d'une gagnante certaine

Le programme
[open-select-single-winner-loan.crust](../../validation/open-select-single-winner-loan.crb)
était refusé après l'attente d'une sélection à une seule branche : son résultat
Int ne contient aucun emprunt et aucune perdante ne garde sa capture, mais
l'accès à la cible restait réservé jusqu'au drop de Select. Les deux refus
avant correction sont conservés dans `validation/select-source-single-winner-gap.log`.

Pour chaque alternative de sélection, le backend identifie maintenant les
branches atteignables pouvant terminer. Si une seule peut gagner, il retire
ses captures terminées des prêts de Select. Il garde ceux de toutes les
perdantes possibles, y compris celles jamais pollées. Les références portées
par le résultat et les champs modifiés ont leurs dépendances propres : cette
libération ne les efface pas.

Deux attentes équivalentes d'une sélection extérieure, une dans chaque bras,
produisent les mêmes réservations statiques. Elles se rejoignent sans inventer
une différence d'obligations due aux identités des listes Python. Une attente
supplémentaire après la jonction reste refusée.

Le passage `validation/select-source-winner-initial-o0.log` exécute 23 méthodes,
25,159 s, OK. Le test de jonction extérieure passe séparément dans
`validation/select-source-outer-paths-o0.log`. Les passages finaux du code
après ces compléments sont suivis dans `select-source-winner-final-o0.log`,
`select-source-winner-final-mutations-o2.log` et `select-source-winner-regression-o2.log`.
Leurs résultats terminaux sont :

- O0 : 24 méthodes, 49,026 s, OK ; 56 exécutions natives et 49 programmes
  refusés dans les deux stages, soit 98 contrôles de refus.
- Mutations O2 : baseline de 24 méthodes, 48,408 s, OK ; douze mutations
  détectées, dont la rétention excessive d'une gagnante certaine et la
  divergence artificielle des réservations après deux attentes équivalentes.
- Régression O2 : 97 méthodes, 71,348 s, OK ; code final des trois parties
  de ce lot, incluant les suites de nettoyages suspendus et du runtime Select.

Tous les processus de validation du cycle sont terminés avec leurs codes
de sortie observés. Les résultats en échec des passages intermédiaires restent
conservés. Ce cycle ne démontre pas une sûreté générale et ne clôt pas l'objectif
global : les limites suivantes sont toujours ouvertes.

## Limites explicites

- Les unions de captures et d'effets du backend sont conservatrices. Elles
  ne distinguent pas exactement la branche gagnante, et peuvent retenir des
  cibles supplémentaires lorsque les contrats ne décrivent qu'une suspension possible.
  Cela peut refuser des programmes valides ; ce n'est pas une nouvelle règle.
  La gagnante certaine bénéficie du complément ci-dessus ; la corrélation
  générale entre la valeur du résultat et l'identité de la gagnante reste ouverte.
- Les résultats agrégés généraux, les autres conteneurs de références et les
  corrélations de chemins restent à raccorder. Un succès scalaire ou une
  allocation Int retournée ne prouve pas le support de tous les résultats.
- Les chemins qui attendent conditionnellement le même Select extérieur
  restent soumis à la jonction conservatrice des états de contrôle lorsqu'un
  seul chemin l'a attendu. Deux chemins qui l'ont chacun attendu sont couverts.
- La destruction d'une perdante détenant un handle lancé et la capture d'un
  handle lancé par une tâche inactive restent des arbitrages ouverts. Les
  gardes de mutex et l'interface publique du scheduler ne sont pas ajoutées.
- Aucun résultat ASan/TSan nouveau, aucune preuve formelle, aucune garantie
  sur tous les ordonnancements ou toutes les combinaisons de types.

L'objectif global demeure incomplet.
