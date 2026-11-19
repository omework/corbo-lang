[English](ASYNC_FAILURE_ONLY_RESULTS_CYCLE.md)

# Résultats sans charge propriétaire et relais async/synchrones

## Portée

Ce lot poursuit [les résultats Select](SELECT_RESULTS_CYCLE.md). Il applique
les règles existantes AS4/AS12/AS16, RT6/RT7, B1/B2/B4/B5, T1/T2/T11,
L1/L2, D1/D3 et U1, sans nouvelle syntaxe ni changement normatif.
AGENTS.md et VALIDATION_GUIDELINES.md sont suivis.

## Contre-exemples et corrections

`validation/open-owned-noncompleting-child.crust` contient un enfant à résultat
propriétaire dont le corps ne termine pas. L'attente de son handle peut pourtant
continuer si le lancement échoue. Le parent modifie ensuite un champ. Le refus
initial des deux entrées est conservé dans
`validation/owned-noncompleting-write-before.log` : contrat de terminaison absent.
La sonde antérieure sans cette modification passait ; son résumé était incomplet
et ses deux échecs de lancement injectés rendaient les valeurs attendues
(`owned-noncompleting-before.log`, `owned-noncompleting-probe.log`).

L'analyse distingue maintenant une absence de terminaison prouvée par un résumé
complet d'un résumé inconnu. LaunchFailed fournit un chemin continuant sans
source de charge réussie. Une attente directe de l'instance, elle, ne crée
toujours aucune continuation si l'enfant ne termine pas. Les résumés récursifs
inconnus ne sont pas transformés en chemins d'échec.

Le retour de cette enveloppe a révélé une seconde limite : une liste de sources
vide ne permettait pas de distinguer une charge absente d'une origine inconnue.
`Value` et `FunctionResult` portent maintenant `absent_owned_payload`, qui est
une information de preuve, pas une conséquence déduite d'une liste vide. Elle
se propage par transfert, contrat, jonction et boucle. Une jonction ne la garde
que si toutes ses alternatives la prouvent. Un résultat propriétaire nu ne
bénéficie pas de cette exception. Les champs et dépendances du résultat sont
collectés séparément de cette information.

Le vérificateur concret conserve cette absence sur le descripteur conditionnel
de Result. Il ne crée pas de source de pool fictive. L'invariant de provenance
ne permet l'absence de source que pour cette charge optionnelle prouvée absente.
L'extraction imbriquée conserve la preuve ; l'extraction finale impossible
termine ce chemin avec un diagnostic interne dans le C généré.

Les tests de composition ont également révélé et corrigé :

- La jonction, dans un if async, de handles issus de fonctions différentes
  mais au même type de résultat public. Les captures, sources et effets des
  branches restent réunis ; les tâches inactives gardent leur type nominal.
- Le transfert descendant explicite d'un Result préexistant, puis son retour
  par break. L'import du bloc est distingué d'un accès implicite au parent.
- Le rattachement au scope d'un Result transféré reçu par le backend async.
- Les paramètres et résultats propriétaires faillibles des auxiliaires
  synchrones appelés depuis un état async, pour Int, String et Vector<Int/u8>,
  y compris deux niveaux de Result. Le pont utilise le contrat publié.
- La responsabilité temporaire de la charge pendant l'évaluation des arguments
  suivants. Une suspension la conserve ; un return anticipé la détruit.
- L'export du Result depuis le pont synchrone, pour éviter sa destruction avant
  le retour. Les gardes symboliques exportées sont explicitement lues par void
  pour conserver la compilation sous Werror sans désactiver les diagnostics.
- L'emploi direct du retour du pont dans match et dans `return <- appel(...)`.
  `drop(-> appel(...))` était déjà raccordé ; la sonde avant correction est
  `validation/failure-only-direct-expressions-probe.log`. La liaison intermédiaire
  n'est pas imposée, et un retour sans flèche reste refusé.
- Le transfert imbriqué `relay(-> relay(-> resultat))`. La sonde
  `validation/open-nested-owned-result-argument.crust` et son journal conservent
  le refus antérieur malgré les flèches. Les résultats temporaires de ces
  appels reçoivent désormais la même responsabilité de nettoyage que les noms.

## Tests, modèle et mutations

`tests/test_async_failure_only_results.py` contient maintenant douze méthodes. Les familles
sans terminaison incluent Int/String/Vector alloués, &str, &u8, tranches partagées
et mutables, et Result<&str,SliceError>. Les essais qui lanceraient réellement
un enfant infini ne sont pas exécutés : le harnais impose un refus du lancement
parent ou enfant et vérifie le résultat et les destructions.

Le modèle fini croise enfant terminant/non terminant et échec de lancement
absent/parent/enfant. Il exclut la seule exécution infinie et calcule les traces
des cinq autres couples sans consulter le compilateur. Le cas terminant produit
une allocation, les autres aucune. La source du résultat possible doit rester
dans le contrat même si l'autre alternative ne termine pas.

Les relais propriétaires sont aussi testés avec une charge réellement présente,
une attente dans l'argument suivant, un return anticipé, le réemploi du pool,
les erreurs aux différents niveaux de Result, les transferts manquants et les
réutilisations après transfert. Le cas de charge absente sans aucun pool de
résultat est exercé ; il ne dépend pas d'un pool artificiel ajouté au programme.
Une méthode supplémentaire exerce deux handles de frames différentes retournant
&Int : chaque choix rend la bonne cible et les deux destructions prématurées
possibles sont refusées avant l'usage du résultat.

La compilation native utilise Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal à O0/O2. Les programmes refusés passent par
verify_program et compile_source. ASan/TSan et la sûreté générale ne sont pas
établis par ces essais.

Le runner `tests/run_failure_only_result_mutations.py` injecte huit fautes dans
des copies temporaires : refuser le cas prouvé vide, traiter un inconnu comme
non terminant, inventer une continuation directe, effacer une source réussie,
perdre la preuve d'absence, la perdre au passage d'un contrat, oublier une charge
préparée, détruire le Result exporté avant son retour.

## Chronologie et journaux

Les journaux ci-dessous sont dans `validation/`.

- `failure-only-results-initial-o0.log` : quatre méthodes, 5,040 s, OK.
- `failure-only-results-expanded-o0.log` : six méthodes, deux échecs. Le choix
  de tâches de types nominaux différents était une fixture incorrecte et a été
  remplacé par un choix de handles. Le retour d'un Result vide révélait le
  manque d'information de preuve, corrigé ensuite.
- `failure-only-results-marked-o0.log` : marqueur ajouté ; le choix de handles
  était encore refusé par le backend async, corrigé ensuite.
- `failure-only-results-handles-o0.log` : six méthodes, 8,412 s, OK.
- `failure-only-results-relays-o0.log` : sept méthodes, quatre erreurs ; invariant
  de source sans charge, import/break et pont Result non raccordés.
- `failure-only-results-absence-o0.log` : absence concrète raccordée ; boucle et
  pont restaient en erreur.
- `failure-only-results-bridge-o0.log` et `failure-only-results-bridge-expanded-o0.log` :
  implémentation raccordée, diagnostics Werror de gardes exportées inutilisées ;
  corrigés sans relâcher les options du compilateur C.
- `failure-only-results-bridge-final-o0.log` : neuf méthodes, 17,918 s, OK.
- `failure-only-results-regression-o2.log` : 127 méthodes, 76,017 s, OK sur
  l'état antérieur aux derniers raccordements de pont, boucle et absence concrète.
- `failure-only-results-mutations-o2.log` : baseline neuf méthodes, 22,845 s,
  sept fautes détectées ; une non concluante parce qu'un Error attendu du mutant
  précédait l'assertion de contrat. L'ordre des deux vérifications a été corrigé,
  sans changer leur résultat attendu. La campagne finale est lancée séparément.

Passages finaux terminés :

- `failure-only-results-final-o0.log` : neuf méthodes, 30,595 s, OK ; compteur
  exécuté de 38 programmes natifs et 12 programmes refusés dans les deux stages
  (24 contrôles de refus).
- `failure-only-results-final-regression-o2.log` : 149 méthodes, 133,909 s,
  OK sur le code avant les deux derniers raccordements d'expressions directes.
  Le complément est exercé séparément ci-dessous.
- `failure-only-results-mutations-final-o2.log` : baseline neuf méthodes,
  32,489 s, OK ; huit mutations détectées. Aucune non concluante ni survivante
  dans cette campagne finale.
- `failure-only-select-mutations-o2.log` : baseline douze méthodes, OK ; les
  cinq mutations précédentes des résultats Select restent détectées.
- `failure-only-results-borrowed-handles-o2.log` : une méthode supplémentaire,
  1,436 s, OK.
- `failure-only-results-final-targeted-o2.log` : dix méthodes, 17,905 s, OK ;
  inclut le choix emprunté et quatre voisins de réutilisation après transfert
  par renommage, if, break et contrat synchrone.
- `failure-only-results-direct-expressions-o2.log` : une méthode, 7,199 s, OK ;
  douze programmes natifs et quatre programmes refusés par les deux stages,
  pour les quatre types alloués et les formes drop/match/return.
- `failure-only-results-direct-regression-o2.log` : 42 méthodes, 66,298 s, OK,
  après les formes directes et avant le dernier raccordement d'argument imbriqué.
- `failure-only-results-nested-final-o2.log` : douze méthodes, 34,714 s, OK sur
  le code final. Le complément imbriqué exerce sept programmes natifs (deux,
  trois ou cinq appels avec/sans échec injecté, puis return dans un argument
  suivant) et trois programmes refusés dans les deux stages.

`failure-only-results-runtime-o2.log` : 275 méthodes, 514,093 s, OK, processus
terminé avec code 0. Cette suite a chargé le code précédant les raccordements
d'expressions directes et imbriquées. Les trois compléments sont exercés dans
les sélections suivantes terminées, sans relancer la même suite runtime pour
des chemins qu'elle ne couvre pas directement. Aucun processus de ce lot ne
reste en cours. Les modules Python modifiés et les nouveaux tests/runners
passent py_compile ; les liens des deux rapports de cycle pointent vers des
fichiers existants.

## Limites

Les résumés ne distinguent pas généralement les variantes de Result dans chaque
branche. L'absence prouvée d'allocation est une propriété plus limitée. Les
unions de champs restent conservatrices. Les conteneurs et signatures généraux,
la récursion générale, le scheduler public et les arbitrages de handles dans
des tâches inactives ou perdantes Select restent ouverts. Les tests de ce lot
n'exécutent pas de nettoyage implicite d'un handle lancé.

Les patches de ce lot sont conservés sous
`validation/*-failure-only-results.patch`. L'objectif global reste en cours.
