[English](ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md)

# Cycle — expressions async sans continuation

## Règles et changement

Application de S4/S5/S5a, B1–B5, D1, AS8/AS10/AS11/AS12 et RT5/RT6, sans
changement normatif. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept
brouillons ont été relus. IF_EXPRESSIONS.md précise qu’un receveur et sa suite
ne sont pas produits lorsque tous les chemins quittent la fonction. Les mêmes
frontières de contrôle de S5 s’appliquent aux sorties de boucle. Le cycle
précédent avait produit des modifications et des preuves exécutées ; ce cycle
poursuit le manque qui y était conservé.

Le générateur représente maintenant explicitement une expression qui ne revient
pas à l’instruction qui l’évalue. Il propage cette absence de continuation
jusqu’à la frontière de l’instruction, sans créer un résultat, sans exécuter sa
suite inaccessible et sans répéter les nettoyages déjà associés aux sorties.
Cette représentation est interne au compilateur ; aucun nouveau type ou mot-clé
du langage n’est introduit. Les chemins qui continuent restent vérifiés pour
leur valeur, leur type, leur mode et leurs dépendances.

Les boucles dont aucun break ne fournit un résultat à leur receveur peuvent
ainsi retourner directement depuis leurs chemins, sans résultat intermédiaire
fictif. L’analyse des contrats s’arrête aussi après une instruction qui n’a
aucune continuation. Les opérateurs à court-circuit sont représentés par leurs
branches : une branche ignorée ne fait pas disparaître l’autre chemin.

`validation/open-async-diverging-initializer.crust` est accepté et exécuté :
42, 20, 77. Le refus historique reste conservé.

## Deux défauts trouvés et corrigés

### Dépendance fictive d’un retour inaccessible

`validation/async-diverging-dead-source.crust` retourne toujours a ou b depuis
l’initialisation. Un `return c` placé ensuite est inaccessible, mais son origine
était tout de même ajoutée au contrat. Modifier c chez l’appelant avant d’utiliser
le résultat était refusé à tort. Le journal initial conserve ce refus.

Le contrat conserve maintenant a et b, sans c. Le programme s’exécute avec
la sortie 42, 20, 50 ; les mutations prématurées de a ou b restent refusées.
Le test couvre aussi un bloc et une boucle dans l’initialisation, avec une suite
inaccessible. Trace corrigée : `async-diverging-dead-source-fixed.log`.

### Fuite d’une allocation préparée pour un appel interrompu

`validation/async-diverging-prepared-owner.crust` déplace junk dans le premier
argument de la future tâche. L’argument suivant retourne depuis la fonction.
La tâche n’est donc jamais créée, mais le transfert avait déjà vidé l’accès
original. La capture temporaire n’avait aucun nettoyage : le réemploi d’un pool
de capacité un échouait avec `pool capacity exceeded`.

Ce défaut a été observé à l’exécution, puis corrigé. Le compilateur suit les
captures propriétaires préparées, avec leur profondeur lexicale. Les sorties
qui interrompent l’appel détruisent ces captures ; une boucle interne à un
argument peut se terminer sans interrompre l’appel englobant et conserve donc
ses captures. Le cas d’un Result propriétaire utilise son champ d’allocation,
qui peut être nul sur un échec de lancement. Le nettoyage est gardé contre ce
cas. Les réservations temporaires et la pile des arguments sont aussi retirées
quand l’évaluation de l’appel est interrompue.

La trace corrigée contient la sortie 88 puis 42 et les destructions junk=77,
reused=88, a=42, chacune une fois. Les deux traces et le programme sont conservés.
Le runtime n’a pas changé : ce correctif porte sur le suivi statique et le C émis.

Le C de ce contre-exemple est conservé dans
`validation/async-diverging-prepared-owner.c`. Son callback de nettoyage
détruit et vide la capture temporaire préparée. Le chemin qui a quitté la
fonction n’émet aucun appel de construction de la tâche abandonnée.

## Scénarios et modèle

Le module final `tests/test_async_diverging_expressions.py` compte douze
méthodes : 42 exécutions natives et 33 refus attendus par passage complet.
Ces nombres ne sont pas une mesure de garanties indépendantes.

- Tous les bras sortent par break dans une initialisation, une affectation,
  un print ou un bloc imbriqué ; les marqueurs de la suite ne s’exécutent pas.
- Retour depuis une initialisation ou depuis un loop, avec suspension et
  conservation des deux provenances du résultat emprunté.
- Continue et break dans la même expression ; modèle arithmétique indépendant
  pour 1, 2 ou 4 incréments avant sortie. La sortie native est comparée au nombre
  attendu, sans utiliser les décisions du compilateur ni le C émis.
- && et || avec un opérande droit qui retourne : les quatre chemins conservent
  le bon résultat et les deux sources possibles restent protégées.
- Match après await dont tous les bras quittent la boucle ; succès et EAGAIN
  injecté, suspension dans les bras, puis utilisation du résultat.
- Enfant inactif propriétaire : nettoyage une fois avant réemploi après join.
- Appel abandonné après un argument déplacé, branche alternative qui termine
  normalement l’appel, break qui interrompt l’appel et boucle d’argument qui
  ne l’interrompt pas ; utilisation de l’ancien accès après transfert refusée.
- Capture préparée d’un Result propriétaire : succès, lancement refusé et
  appel qui termine normalement ; nettoyage sans double destruction.
- Modes divergents, cibles locales détruites, break sans valeur et bras
  continuant sans valeur restent refusés.

Le modèle est fini. Il n’établit pas la correction générale du contrôle de
flux, des provenances ni des nettoyages de tous les agrégats.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-diverging-expressions-initial.log | 7 méthodes, 12,860 s, OK ; avant découverte de la capture préparée perdue |
| async-diverging-expressions-expanded.log | 26 méthodes, 34,047 s, OK ; n’éprouvait pas encore la fuite des arguments |
| async-diverging-expressions-prepared.log | 11 méthodes, une erreur sur un bloc utilisé comme argument Int ; corrigée en traitant cette forme via l’évaluation typée des blocs |
| async-diverging-expressions-prepared-result.log | Test du Result préparé : 1 méthode, 1,818 s, OK |
| async-diverging-expressions-O0.log | 11 méthodes, 25,569 s, OK |
| async-diverging-expressions-short-circuit-O0.log | Douzième méthode ajoutée : 2,461 s, OK |
| async-diverging-expressions-short-circuit-O2.log | Même complément à O2 : 2,250 s, OK |
| async-diverging-expressions-O2-regression.log | 176 méthodes, 247,789 s, OK, sans saut ; avant ajout du complément court-circuit, exécuté séparément |

La régression O2 élargie est terminée. Le module final est ainsi couvert à O0
et O2 par les onze méthodes initiales plus le complément exécuté séparément.
`py_compile` et les liens locaux des documents modifiés ont réussi. Le diff
du compilateur est conservé dans `validation/async-diverging-expressions.patch`.
Les helpers natifs utilisent Clang C11, pthread, -Wall/-Wextra/-Werror et UBSan
fatal. Aucun saut de méthode n’est caché dans les résultats ci-dessus.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_diverging_expressions -v
python3 tests/run_async_diverging_expression_mutations.py
```

La régression O2 + UBSan charge les modules de ce cycle, des sorties
d’expressions, des boucles empruntées, des matchs empruntés, des liaisons locales
async, des retours async et des expressions empruntées synchrones. Elle ajoute
les méthodes d’AsyncRuntimeTests contenant loop, continue, break, conditional,
argument, capture ou cleanup. Son journal fournit les noms exacts exécutés.
Elle a été lancée avant l’ajout du test de court-circuit, exécuté séparément.

## Mutations

| Faute | Observation |
| --- | --- |
| Réintroduire les retours inaccessibles dans le contrat | Programme valide refusé à cause de c |
| Omettre le nettoyage des captures préparées | Pool de capacité un épuisé |
| Nettoyer les captures de l’appel extérieur au break d’une boucle d’argument | Défaut natif détecté après raffinement de la faute |
| Effacer une provenance de retour | Accès incompatible à une cible possible accepté |

La première mutation de profondeur supprimait aussi une réservation et faisait
échouer le compilateur avec KeyError. Le script l’a classée inconclusive ; cette
trace reste dans `async-diverging-expressions-mutations.log`. La faute a été
raffinée pour préserver les réservations et supprimer seulement la frontière de
nettoyage mémoire. Elle est détectée à l’exécution dans
`async-diverging-expressions-depth-mutation.log`. Les trois autres fautes étaient
détectées dans la campagne initiale. Aucun taux général n’est extrapolé.

## Limites et suite

Une initialisation entièrement non continuante annotée `[Int;1]` reste refusée :
`validation/open-async-diverging-typed-initializer.crust` et son journal.
L’annotation ne doit pas imposer de matérialiser une valeur qu’aucun chemin ne
fournit. Cette frontière des liaisons typées reste à intégrer.

Suivi : [ASYNC_TYPED_DIVERGENCE_CYCLE.md](ASYNC_TYPED_DIVERGENCE_CYCLE.md)
traite cette fixture et les annotations reconnues par le backend async.
La limite ci-dessus décrit l’état à la fin du présent cycle.

Tous les types d’agrégats et toutes les positions syntaxiques ne sont pas
couverts. Les autres obligations des sept brouillons restent ouvertes, dont
scheduler, threads natifs, Select, mutex et stockage implicite. Reset reste retiré.
ASan n’a pas été relancé après le blocage du programme C vide documenté
précédemment. Aucune preuve ASan/TSan, second compilateur, preuve formelle ou
sûreté générale du langage n’est revendiquée. L’objectif global reste actif.
