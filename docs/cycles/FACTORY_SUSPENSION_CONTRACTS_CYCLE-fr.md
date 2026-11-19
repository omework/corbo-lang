[English](FACTORY_SUSPENSION_CONTRACTS_CYCLE.md)

# Préfixes de suspension des fabriques synchrones de tâches

Suivi : les remplacements propriétaires évoqués comme incomplets ci-dessous
sont raccordés pour les formes testées dans
[FACTORY_OWNED_EFFECTS_CYCLE.md](FACTORY_OWNED_EFFECTS_CYCLE.md).

## Périmètre

AS3–AS5, AS14, AS16 et SL1 s'appliquent à une tâche renvoyée par une fonction
synchrone. Son contrat conserve séparément les effets visibles aux suspensions
et ceux de sa terminaison normale. Créer ou détruire une instance inactive
n'exécute pas son corps. Aucune règle normative n'est modifiée.

Le programme enregistré dans
`validation/open-factory-suspended-field.crust` était refusé avec le diagnostic
« effets suspendus de la branche Select non raccordés ». La tâche enfant écrit
une nouvelle référence, suspend, puis restaure l'ancienne à sa terminaison.
Lorsqu'elle perd dans Select pendant sa suspension, la restauration n'a pas lieu.
Le programme doit donc afficher `99`, `9`, puis `1`.

## Implémentation

Les contrats des fabriques et les valeurs symboliques des tâches conservent
les cibles des écritures suspendues et la possibilité d'une suspension.
Un résumé inconnu reste distinct d'un résumé connu vide. Les appels remappent
ces cibles sur les paramètres réels, y compris après permutation, relais et
transfert d'une tâche déjà construite.

Les choix entre tâches réunissent les cibles possibles d'un même champ :
ils ne sont pas traités comme des écritures successives dont seule la dernière
survivrait. L'analyse des appels async applique ces préfixes à l'attente,
séparément des effets de terminaison. Select accepte également une instance
provenant directement d'une fabrique lorsque ses effets sont représentés.

L'analyse symbolique utilise les contrats synchrones publiés avec des corps
vides. Le test contrôle explicitement cette frontière et le contenu des
résumés de suspension et de terminaison. La génération C et l'exécution
utilisent les mécanismes existants de reprise et de nettoyage.

## Cas ciblés

`tests/test_factory_suspension_contracts.py` contient cinq méthodes :

- Cas enregistré : écriture suspendue conservée après nettoyage de Select ;
  drop de la cible avant lecture refusé aux deux entrées du compilateur.
- Terminaison normale : restauration de l'ancienne cible ; destruction de la
  nouvelle cible permise, destruction de l'ancienne refusée avant la lecture.
  Création suivie de yield et drop inactif : aucune écriture du corps.
- Fabrique relayée, paramètres permutés et transfert par un auxiliaire.
- Fabrique directement dans Select, propagation de son effet à l'appelant.
- Choix des captures dans la fabrique et dans l'appelant async ; les deux
  branches s'exécutent et les deux cibles possibles restent protégées.

Chaque passage ciblé comprend neuf exécutions natives et six programmes refusés
via `verify_program` et `compile_source`, soit douze contrôles de refus.

## Résultats exécutés

Le passage ciblé O0 termine avec code 0 : cinq méthodes en 5,375 s,
journal `validation/factory-suspension-contracts-o0.log`.
La régression O2 termine avec code 0 : 97 méthodes en 66,366 s, incluant
les cinq méthodes ciblées sur la même implémentation finale ; journal
`validation/factory-suspension-contracts-regression-o2.log`.
Les exécutions natives utilisent Clang C11, pthread et UBSan avec
`-fno-sanitize-recover=all` ; les erreurs de compilation et d'exécution font
échouer le test. Aucun test n'est sauté dans ces deux passages.

## Limites

Ce lot couvre les champs empruntés Int représentés dans les contrats. Les
fabriques dont les préfixes remplacent des allocations possédées restent
incomplètes dans cette représentation ; elles ne publient pas un faux résumé
vide. Les préfixes concurrents de tâches déjà lancées ne sont pas raccordés
par ce lot. Les captures de handles restent soumises à l'arbitrage ouvert.

Le contrat `may_suspend` ne décrit pas l'ordre exact du premier yield par
rapport à toute terminaison. L'analyse de Select peut donc conserver aussi
l'alternative restaurée, même lorsque l'exécution testée sélectionne la branche
immédiatement prête. Cette approximation conserve les protections nécessaires.

Les premiers passages des nouveaux tests contenaient une extraction de texte
incorrecte et une incompatibilité entre les notations Bool/bool dans les
paramètres synchrones et async. Le test conditionnel utilise le sélecteur Int
déjà pris en charge ; l'harmonisation Bool/bool n'est pas corrigée par ce lot.
Un contrôle de contrat supposait aussi une précision supérieure à `may_suspend` ;
il a été corrigé pour vérifier les deux origines conservées, sans modifier les
valeurs natives attendues ni retirer les contrôles de refus.

Pas de nouvelle campagne adversariale ni de mutations. Les modèles déjà
présents dans les suites liées sont rejoués ; aucun nouveau modèle indépendant
n'est revendiqué. Ces exécutions ne constituent pas une preuve générale de sûreté.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_factory_suspension_contracts
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_factory_suspension_contracts test_suspension_effects test_async_result_factories test_select_source test_async_structure_effects test_async_owned_field_writes test_async_mutable_descendant_results
```

Snapshot avant modification : `/tmp/crust-before-factory-suspension-contracts/`.
Différences conservées dans
`validation/factory-suspension-contracts-{results,async_structure_effects}.py.patch`.
Les journaux intermédiaires sont conservés séparément des passages finaux.
