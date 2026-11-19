[English](ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md)

# Cycle — sorties de boucle depuis les expressions async

## Règles et changement

Ce cycle applique S4/S5/S5a, B1/B2/B3/B5, D1, AS8/AS10/AS11/AS12 et RT5/RT6.
Les règles normatives ne changent pas. AGENTS.md, VALIDATION_GUIDELINES.md,
l’index des sept brouillons et les clauses de contrôle de flux ont été relus.
IF_EXPRESSIONS.md précise que seules les branches qui rejoignent un receveur
doivent lui fournir une valeur. Le cycle précédent constituait un progrès
effectif ; les autres obligations des brouillons restent ouvertes.

Un bras d’expression qui exécute break ou continue n’a pas à produire une
valeur pour l’expression interrompue. Le contrôle de la valeur manquante se
fait désormais après analyse du bras. Une branche qui continue sans valeur
reste refusée. Les if/blocs terminaux dont tous les chemins sortent sont
traités comme du contrôle de flux, sans fabriquer un résultat intermédiaire.
Les métadonnées de région du bloc sont conservées lors de cette transformation.

L’analyse des résultats empruntés de boucle visite aussi les expressions des
initialisations, affectations, arguments et opérandes de sortie. Elle garde
leurs liaisons lexicales pour retrouver les provenances. Les boucles imbriquées
introduisent leur propre cible de break : leurs sorties ne sont pas confondues
avec celles de la boucle externe.

Les expressions continuantes gardent leur type et mode habituels. Les sorties
utilisent les mêmes vérifications de durée de vie, réservations et nettoyages
que les autres break/continue. Le runtime n’a pas été modifié.

## Contre-exemples et défauts de développement

`validation/open-async-loop-break-in-initializer.crust`, valide mais auparavant
refusé, est maintenant accepté et exécuté : sortie 42, 20, 77. Sa variante
`validation/async-loop-nested-expression-provenance.crust` tente d’écrire dans
a avant d’utiliser le résultat mutable. Elle est refusée par le contrôle
d’emprunt, et non plus par une limitation de la forme de l’expression.
Les traces initiales et corrigées sont conservées.

La première extension du parcours confondait les listes d’instructions et
les listes d’arguments d’appel : AttributeError sur des tuples. Elle distinguait
aussi insuffisamment un if terminal sans chemin continuant. Ces erreurs ont
été corrigées ; le journal initial reste disponible. Le premier lancement
découvrait en outre les tests de la classe importée sous un alias : l’import
utilise maintenant le module, ce qui évite cette exécution involontaire en double.

## Scénarios et observations

`tests/test_async_expression_loop_exits.py` contient huit méthodes :
23 exécutions natives et 21 refus attendus par passage complet.

- Break dans un if d’initialisation, un bloc, des if imbriqués ou un match
  de conversion ; les deux cibles possibles restent réservées après retour.
- Continue dans une initialisation ou une affectation : reprise de la bonne
  itération, suspension, compteur final et absence d’exécution du reste du bras.
- Boucle interne qui emprunte b puis retourne son accès avant que la boucle
  externe fournisse a ; chez l’appelant, b reste modifiable avant usage de a.
  Ce voisin accepté vérifie que les contrats ne retiennent pas arbitrairement
  toutes les références rencontrées dans le corps.
- Break dans l’expression d’un break ou d’un return, avec les deux chemins
  exécutés et protection de chacune des provenances.
- Break depuis le bras Ok d’un match après await : propagation de la cible du
  résultat, suspension dans le bras, branche de secours après EAGAIN injecté.
- Enfant inactif possédant une allocation dans le scope quitté par le break :
  destruction une seule fois, aucun démarrage de cet enfant, puis réemploi
  du pool de capacité un après join.
- Refus des types/modes divergents, break sans valeur, cible locale détruite,
  branche continuante sans valeur et reprise qui réutiliserait une tâche consommée.

Les attentes de sortie et de destruction sont définies explicitement à partir
des chemins. Il n’y a pas de nouveau modèle indépendant général dans ce lot.
La régression inclut le modèle des trois indices de tableau du cycle précédent,
ainsi que les modèles de sélection des résultats empruntés. Cela reste une
couverture finie, sans preuve générale d’analyse de contrôle de flux.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-expression-loop-exits-initial.log | Erreurs de développement décrites ci-dessus ; conservées |
| async-expression-loop-exits-expanded.log | 16 méthodes, 14,295 s, OK : les six premières nouvelles méthodes et les dix du cycle précédent |
| async-expression-loop-exits-operands.log | Deux méthodes supplémentaires, 2,848 s, OK |
| async-expression-loop-exits-O0.log | Module final : 8 méthodes, 9,458 s, OK |
| async-expression-loop-exits-O2-regression.log | 89 méthodes, 88,707 s, OK, sans saut |

La régression O2 est terminée. `py_compile` et les liens locaux des documents
modifiés ont été vérifiés. Le diff du compilateur est conservé dans
`validation/async-expression-loop-exits.patch`.
Les helpers natifs utilisent Clang C11, pthread, -Wall/-Wextra/-Werror et UBSan
fatal. Les niveaux d’optimisation sont choisis par CRUST_TEST_OPT.

Commandes du module et des fautes ciblées :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_expression_loop_exits -v
python3 tests/run_async_expression_loop_exit_mutations.py
```

La régression O2 + UBSan charge test_async_expression_loop_exits,
test_async_loop_references, test_async_match_references,
test_async_local_references, test_async_reference_returns et
test_reference_expressions, puis les méthodes d’AsyncRuntimeTests dont le
nom contient loop, continue, break ou conditional. Le journal liste les noms.

## Mutations

La campagne initiale détectait l’oubli des sorties d’initialisation et la
traduction incorrecte de continue en break. La seconde faute déclenche UBSan
sur le résultat qui n’a pas été fourni avant la sortie prématurée.

La suppression complète du nettoyage était initialement classée inconclusive
par le script, car le compilateur refusait le programme valide avant génération
C. Le journal montre précisément le contrôle des obligations de nettoyage
divergentes entre sorties. Le script reconnaît désormais ce diagnostic exact
pour cette faute comme une détection par invariant du compilateur, distincte
d’une détection native. Une quatrième faute supprime uniquement l’appel C de
nettoyage de l’enfant, pour éprouver aussi l’observation du réemploi du slot.
La campagne finale est terminée : quatre fautes détectées, dont une par
l’invariant du compilateur. La suppression de l’appel C provoque bien
l’épuisement du pool de capacité un. Traces :
`validation/async-expression-loop-exits-final-mutations.log` ; script :
`tests/run_async_expression_loop_exit_mutations.py`. Aucun taux global de
détection n’est déduit de ces quatre fautes sélectionnées.

## Limites et suite

`validation/open-async-diverging-initializer.crust` reste refusé. Les deux bras
de son if d’initialisation quittent la boucle : aucun receveur intermédiaire
ne doit être produit, et la boucle externe reçoit bien la référence du break.
Le diagnostic `utiliser if comme instruction quand toutes les branches retournent`
constitue encore un manque d’implémentation. La prise en charge de ces expressions
sans continuation doit être propagée au-delà des seuls bras terminaux.

Suivi : [ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md](ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md)
traite ce programme et les nettoyages des arguments préparés avant une sortie.
La limite ci-dessus décrit l’état à la fin du présent cycle.

Les tests ne couvrent pas tous les types d’agrégats ni toutes les positions
d’expression. Les autres écarts de la matrice, notamment scheduler, threads
natifs, Select, mutex et stockage implicite, restent ouverts. Reset reste retiré.
ASan n’a pas été relancé après le blocage du programme C vide documenté dans
les cycles précédents. Aucune preuve ASan/TSan, second compilateur ou preuve
formelle n’est revendiquée. L’objectif global n’est pas atteint.
