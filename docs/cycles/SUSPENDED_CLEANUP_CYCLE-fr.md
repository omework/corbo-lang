[English](SUSPENDED_CLEANUP_CYCLE.md)

# SL1 / AS8–AS10 — Nettoyage généré aux points de suspension

## Portée

Ce lot poursuit le [mécanisme interne de Select](SELECT_RUNTIME_CYCLE.md).
SL1 exige de conserver puis détruire les états perdants ; AS8, L1/L2 et V4
imposent de distinguer les ressources encore vivantes à chaque suspension.
Aucune règle normative n'est modifiée. Select reste non raccordé au parseur,
aux contrats et au vérificateur source.

## Implémentation

Le backend enregistre un chemin de destruction distinct pour chaque point
yield/await. Il le construit sans consommer les liaisons de l'analyse normale.
Les chemins décrivent, dans cet ordre :

1. L'enfant direct dont le résultat est encore attendu, lorsqu'il existe.
2. Les captures propriétaires déjà préparées pendant l'évaluation des arguments.
3. Les scopes encore ouverts, du plus interne au plus externe, avec leurs
   entrées de destruction en ordre inverse.

Les déplacements et drops déjà effectués sont pris en compte. Une même liaison
importée d'un scope parent n'est nettoyée qu'une fois. Un résultat propriétaire
enveloppé ne détruit sa charge que sur son chemin de succès. Un pool local est
fermé après ses allocations et les enfants qui peuvent encore l'utiliser.
Les références n'ont pas de destructeur runtime qui détruirait leurs cibles.

Chaque état généré fournit `can_discard_suspended` et `discard_suspended`.
La capacité est vérifiée récursivement sur les enfants directs avant de
consommer le premier état. Le nettoyage restitue ensuite les slots d'états
après leurs ressources. Les états inactifs et terminés continuent d'utiliser
leurs chemins de libération antérieurs.

`task_drop_owned` est une primitive C interne, réservée au propriétaire exclusif
d'un arbre d'attentes directes après révocation des routes de réveil. Elle
n'autorise pas à détruire un handle lancé et n'ajoute pas d'annulation publique.
Le runtime de sélection peut utiliser les callbacks générés sans adaptateur
manuscrit pour les cas exercés ici.

Si un point de suspension conserve un handle lancé, ou attend un enfant qui
en conserve un, la prévalidation répond non sans modifier ni libérer l'état.
La tâche peut reprendre normalement et satisfaire son attente. Ce comportement
interne ne tranche pas [l'arbitrage en attente](../SELECT_LAUNCHED_HANDLE_DECISION.md)
et ne constitue pas encore un diagnostic source pour Select.

## Écart découvert et corrigé

Le remplacement explicite `a = <- p.new(40)` dans un corps async était dirigé
vers l'analyse scalaire et refusé comme `new_transfer` non pris en charge.
Le backend reconnaît maintenant le marqueur autour d'une construction ou
d'un appel synchrone retournant une allocation et utilise le chemin de
remplacement existant : nouvelle valeur évaluée, puis ancienne détruite.

Le test utilise notamment `a = <- p.new(read(&a).await)` : au premier arrêt,
seule l'ancienne allocation existe ; au suivant, elle a été détruite et la
nouvelle est possédée. L'appel synchrone créateur avec marqueur explicite est
également exécuté. Receveur immutable et emprunt utilisé après remplacement
restent refusés par check et compile.

## Scénarios et oracles

`tests/test_suspended_cleanup.py` contient dix méthodes :

- Six couples branche/point de suspension : capture déjà détruite, allocations
  locales et conditionnelles, remplacement et réemploi du pool d'entrée.
- Douze exécutions d'une attente directe sur trois niveaux, avec deux pools
  locaux : destruction de l'enfant avant la cible du parent qu'il emprunte.
- Arguments déjà transférés pendant un await ultérieur, pour un appel synchrone
  et un appel async, puis suspension après création effective de l'enfant.
- Cinq points d'arrêt avec transfert descendant, retour au parent, renommage,
  enfants inactifs et trois itérations de boucle.
- Résultat `Result<A<Int>, runtime::Error>` encore possédé à la suspension,
  avec succès et refus de soumission injecté ; une seule destruction.
- Arbre contenant un handle lancé : prévalidation négative sans fermeture de
  pool, puis reprise, attente explicite et résultat normal.
- Vraie sélection en C avec callbacks générés : le gagnant fournit 9 et la
  perdante garde son allocation locale jusqu'au drop de Select.
- Remplacement dont le calcul emprunte l'ancienne allocation et se suspend ;
  appel créateur synchrone ; voisins refusés pour mutabilité et emprunt actif.
- Modèle indépendant de scopes : listes de valeurs vivantes et historique de
  destructions, 22 scénarios (0/1/3 tours, deux branches, chaque point d'arrêt).
  Il prédit l'ordre des valeurs détruites et le nombre de fermetures de pools,
  sans utiliser les états du vérificateur ni les points de reprise C.
- String, Vector<Int> et Vector<u8>, avec région 1M et vue encore présente dans
  la perdante, six réemplois par type. La continuation qui utiliserait la vue
  n'est pas exécutée ; les données sont détruites et leurs sources fermées.

Les harnais qui détruisent une instance en cours possèdent exclusivement son
arbre ; ils n'exécutent pas cette opération sur une tâche schedulée. Les
préconditions de la primitive interne ne sont pas une nouvelle syntaxe source.

## Chronologie et preuves exécutées

Clang C11/pthread, Wall/Wextra/Werror, UBSan fatal ; optimisation contrôlée par
`CRUST_TEST_OPT`. Journaux sous `validation/`.

- `suspended-cleanup-select-initial.log` : sept tests du mécanisme Select
  précédent réussis à O0, 3,035 s.
- `suspended-cleanup-initial-o0.log` : sept méthodes, neuf sous-cas en erreur
  avant exécution. Fixtures corrigées : déréférencement explicite dans les
  lectures async et noms de payload distincts des liaisons déjà déclarées.
- `suspended-cleanup-second-o0.log` : sept méthodes, six sous-cas refusés sur
  `new_transfer`. C'est l'écart de remplacement corrigé dans le compilateur.
- `suspended-cleanup-third-o0.log` : sept méthodes, deux assertions sur le label
  diagnostique de la construction anonyme. Ce label est `async allocation`,
  pas le nom du receveur. Les identités des valeurs et l'ordre attendu n'ont
  pas changé ; la fixture a été corrigée.
- `suspended-cleanup-model-o0.log` : neuf méthodes, mêmes deux assertions et
  un scénario du modèle refusé faute d'usage explicite de `current`. Les lectures
  explicites ont été ajoutées ; l'oracle de destruction est inchangé.
- `suspended-cleanup-final-o0.log` : neuf méthodes réussies, 7,930 s.
- `suspended-cleanup-complete-o0.log` : dix méthodes finales, 14,782 s, OK.
- `suspended-cleanup-mutations-o2.log` : baseline de dix méthodes, 11,386 s, OK.
  Huit mutations détectées : enfant omis, captures préparées omises, ordre de
  nettoyage inversé, obligation de handle ignorée, prévalidation d'enfant omise,
  statut du résultat inversé, points de suspension confondus, slot d'état perdu.
  Les copies temporaires du compilateur sont modifiées sans toucher aux oracles.
- `suspended-cleanup-regression-o2.log` : 47 méthodes, 30,966 s, OK, avec les
  nouveaux nettoyages, Select, pools locaux, régions et notifications d'attente.
- `suspended-cleanup-fields-o2.log` : 42 méthodes, 42,472 s, OK, couvrant les
  reprises de champs, résultats empruntés et mutables, et fabriques synchrones.
- `suspended-cleanup-async-regression-o2.log` : 275 méthodes, 451,134 s ;
  274 réussites et un échec d'instrumentation décrit ci-dessous. La suite avait
  chargé l'ancienne ancre avant sa correction ; la méthode corrigée a été
  réexécutée séparément. Aucun passage unique de 275 méthodes sans échec
  n'est revendiqué.
- `suspended-cleanup-slice-counterexample.log` puis
  `suspended-cleanup-slice-final.log` : une instrumentation de test cherchait
  la déclaration de frame suivie du switch pc, désormais présente aussi dans
  les deux nouveaux callbacks. Son ancre vise maintenant explicitement la
  fonction resume. La méthode passe à O2 (1,197 s), avec les mêmes attentes de
  valeurs et de refus ; le contrôle d'unicité de l'ancre est conservé.
- Compilation Python des fichiers du lot réussie.

Ces comptages se recouvrent et ne sont pas des nombres de programmes distincts.
Les premiers passages en échec restent consignés séparément des versions finales.

## Limites et suite

Les nettoyages sont désormais générés pour les points reconnus par le backend,
mais les essais ne couvrent pas toutes les compositions de types et de contrôle
de flux. Pas de preuve formelle, de nouveau résultat ASan/TSan ni de deuxième
compilateur C. La destruction d'une branche perdante avec obligation d'attente
reste à arbitrer ; aucune attente cachée n'a été introduite.

Restent le raccordement source de Select, ses contrats de capture/résultat et
de durée des perdantes, la vérification de l'unique attente, le dimensionnement
des pools avec rétention des états et les interactions avec les mutex. Les autres
familles ouvertes du projet ne sont pas déclarées terminées par ce lot.

La revue du raccordement identifie aussi une exigence pour les contrats :
une perdante a pu modifier un champ extérieur avant de suspendre. Le contrat
de terminaison seul ne suffit pas, car une restauration écrite après yield
ne sera pas exécutée. Le scénario
[open-select-partial-field-effect.crust](../../validation/open-select-partial-field-effect.crb)
doit faire refuser le drop de `second` : la branche perdante l'a stocké dans
`view.data`. Il s'agit d'un contre-exemple à un raccordement qui ignorerait les
effets des préfixes suspendus, pas d'un programme actuellement accepté ; Select
n'est pas encore analysé par le compilateur. Cette exigence découle des règles
existantes et ne demande pas de changer leur sémantique.
