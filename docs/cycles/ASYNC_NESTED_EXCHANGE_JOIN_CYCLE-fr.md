[English](ASYNC_NESTED_EXCHANGE_JOIN_CYCLE.md)

# Enveloppes runtime imbriquées autour de replace et try_push

## Règles appliquées

RT6 impose une enveloppe `Result<T, runtime::Error>` à chaque attente d'un
handle. AS10–AS13, H1–H2 et VE3–VE4 imposent de conserver les allocations,
leurs sources et la responsabilité de leur nettoyage. U1, F3–F4, AS14 et
SL1–SL2 restent applicables aux transferts, captures et arguments suspendus.
Aucune règle normative n'est modifiée.

Ce lot retire la limite fixe de profondeur pour les enveloppes runtime autour
de `Result<A<Int>,A<Int>>` et `Result<(),A<Int>>`. Chaque type est décrit par
sa profondeur, son type intérieur, sa représentation C, le chemin du handle
et les conditions de présence de sa charge. L'extraction de `Ok` enlève une
seule enveloppe. Les deux provenances de l'opération restent distinctes.
Pour try_push, seul le bras d'échec de l'opération possède l'entrant ; une
erreur de lancement, à n'importe quel niveau, ne possède pas ce résultat.

Les signatures, contrats, handles publics synchrones, captures de résultats,
retours async, jonctions et nettoyages utilisent ces descriptions. Les tables
consultées pendant l'analyse suivent les nouveaux types enregistrés lors du
parsing. Les dispositions C sont émises selon les signatures du programme.
Les objets des pools gardent leur adresse : les enveloppes transportent leurs
handles, sans recopier les allocations ciblées.

## Cas ciblés

`tests/test_async_nested_exchange_join.py` comprend huit méthodes, avec
21 exécutions natives et six programmes invalides vérifiés par verify_program
et compile_source :

- Deux, trois et cinq enveloppes autour de replace, sur les deux variantes.
- Échec de lancement injecté à chacun des trois niveaux d'une chaîne.
- Handle public, helper synchrone d'attente et relais du résultat.
- Extraction des enveloppes dans async après attente d'un handle.
- Capture du résultat : exécution, destruction inactive et argument préparé
  avant suspension, nettoyé dans une branche perdante de Select.
- Try_push réussi ou refusé après remplissage réel d'une région de 1 MiB,
  avec extraction ou destruction inactive ; destruction unique de l'entrant.
- Pools distincts par bras ; extraction de l'ancienne allocation hors du
  bloc du pool entrant, et refus lorsque sa propre source ne survit pas.
- Résultat provenant d'un if ou d'une loop, nettoyage et réemploi des slots.
- Refus du transfert absent, de la réutilisation d'un résultat transféré,
  du résultat sans usage, de la double consommation et du motif ignorant
  une charge propriétaire.

Le nombre de profondeurs exécutées ne constitue pas une preuve pour toute
profondeur. La description est récursive, sans nouvelle borne spécifique à
ces enveloppes ; les limites générales de récursion du prototype restent.

## Défauts rencontrés

La reproduction initiale `validation/open-async-nested-exchange-join.crust`
était refusée par le garde de profondeur du compilateur. Après raccordement,
elle produit `8`, puis `9`, avec nettoyage et réemploi.

Le premier passage de la nouvelle suite utilisait la notation de match
consommant de replace/try_push sur les enveloppes runtime intermédiaires.
Le générateur de snippets a été corrigé pour utiliser leur syntaxe déjà prise
en charge ; les résultats attendus et les oracles mémoire n'ont pas changé.
Un passage ultérieur a aussi relevé une accolade finale absente dans le nouveau
snippet à pools distincts, corrigée avant son exécution native.

Le défaut d'implémentation découvert par les profondeurs supplémentaires était
une liste de modes de résultats figée lors de l'import du module des effets
async. Elle dépendait donc des types déjà rencontrés dans le processus. Une
vue dynamique du registre remplace cette copie, y compris pour les effets
différés des champs. Les charges vides de try_push sont également reconnues
à chaque profondeur dans les paramètres symboliques.

## Exécutions et preuves

Les commandes ciblées utilisent `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0
python3 -m unittest test_async_nested_exchange_join -v`. Le harnais compile
le C11 avec pthread, Wall/Wextra/Werror, UBSan et
`-fno-sanitize-recover=all`. Les diagnostics sanitizer font échouer le test.

Journaux dans `validation/` :

| Journal | Résultat |
| --- | --- |
| async-nested-exchange-join-first-o0.log | Reproduction initiale exécutée, code 0 |
| async-nested-exchange-join-second-o0.log | 7 méthodes, 1,983 s, code 1 ; notation des matchs du générateur |
| async-nested-exchange-join-third-o0.log | 7 méthodes, 5,394 s, code 1 ; modes figés dans les effets async |
| async-nested-exchange-join-fourth-o0.log | 7 méthodes, 8,156 s, code 0 |
| async-nested-exchange-join-fifth-o0.log | 8 méthodes, 8,134 s, code 1 ; accolade absente du snippet ajouté |
| async-nested-exchange-join-sixth-o0.log | 8 méthodes, 8,848 s, code 0 ; 21 exécutions et six refus |
| async-nested-exchange-join-regression-o2.log | 135 méthodes, 121,391 s, code 0 ; O2/UBSan |

Commande de régression :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
  test_async_nested_exchange_join test_async_exchange_join \
  test_async_handle_exchange_results test_async_handle_exchange_calls \
  test_async_option_join test_async_handle_option_results \
  test_async_handle_option_calls test_async_structure_effects \
  test_factory_owned_effects test_public_handle_contracts \
  test_select_source test_task_wakes -v
```

## Portée et suite

Les résultats ciblés sont comparés à leurs valeurs attendues, leurs traces de
destruction et le réemploi de pools bornés. Le harnais existant de Select et
les tests de réveil ont réussi dans la régression (dont leurs modèles indépendants existants). Aucun nouveau modèle général,
aucune campagne de mutation ni audit adversarial indépendant ne sont revendiqués.
ASan et d'autres compilateurs C ne sont pas exercés dans ce lot.

La généralisation des enveloppes autour d'Option<A<Int>>, des allocations
simples et d'autres charges reste distincte et ouverte. Les captures de handles
d'exécution dans une instance inactive ne sont pas ajoutées : le diagnostic
existant est reproduit dans `async-nested-exchange-public-layout-first.log`.
Ce refus se produit avant l'émission C et ne prouve rien sur ses dispositions.
Les arbitrages publics scheduler/mutex recensés dans design-buffer restent
ouverts. Ce lot ne clôt pas l'objectif global d'implémentation.

Les sept fichiers Python modifiés sont comparés à la sauvegarde
`/tmp/crust-before-nested-exchange-joins`. Les diffs sont conservés sous
`validation/async-nested-exchange-join-*.py.patch`.

Le programme de profondeur trois et son C généré sont conservés dans
`validation/async-nested-exchange-depth3.crust` et `.c`. L'inspection des
conditions de nettoyage confirme le test de chaque statut runtime avant
l'accès à la charge ; l'exécution de ce programme est couverte par la suite.
La prochaine restriction est reproduite aux deux entrées dans
`validation/open-async-nested-option-join.crust` et `.log` : une tâche retournant
`Result<Option<A<Int>>,runtime::Error>` ne peut pas encore être lancée.
