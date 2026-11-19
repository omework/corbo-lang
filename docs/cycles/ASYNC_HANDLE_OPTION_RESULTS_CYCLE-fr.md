[English](ASYNC_HANDLE_OPTION_RESULTS_CYCLE.md)

# Captures et retours async d'options propriétaires

## Règles appliquées

Application de H1–H2, VE3, U1, B1–B5, AS2–AS5, AS8–AS15 et SL1–SL2,
sans modification normative. Une Option<A<Int>> possède son éventuel contenu.
Sa capture exige un transfert explicite ; son retour transmet le contenu et
sa provenance au receveur. None ne transporte aucune allocation. Le pool de
l'élément doit survivre à la tâche puis au résultat qui le conserve.

## Implémentation

La représentation VectorHandleResult est raccordée aux captures et aux résultats
des états async. Les contrats de résultats et de champs conservent les sources
optionnelles. Les fabriques synchrones et relais async propagent ces contrats.
L'attente d'une instance inactive reçoit l'option avant de détruire son état.
Les chemins de nettoyage existants traitent le contenu seulement s'il est présent.
Une capture statiquement vide ne crée pas de dépendance d'allocation fictive.

Le résultat direct de la tâche et l'enveloppe faillible de son handle sont
distincts. Ce lot raccorde le premier. Un join ou un await de handle dont le
résultat est Option<A<Int>> produit encore un diagnostic explicite de fonctionnalité
non raccordée, au lieu d'utiliser la représentation d'un résultat Int.

## Cas exécutés

Huit méthodes dans tests/test_async_handle_option_results.py : treize exécutions
natives et sept programmes invalides contrôlés par verify_program et compile_source.

- Retours Some/None par await ; retour sans flèche refusé.
- Option nommée avant yield, fabrique synchrone et relais async.
- Captures Some/None ; absence de transfert et réutilisation après transfert refusées.
- Destruction d'une tâche inactive et échec du premier lancement injecté :
  nettoyage du contenu transféré, destruction unique et réemploi du slot.
- Capture retournée par une tâche enfant, puis transmise à un helper synchrone.
- Enfant suspendu après extraction, dans un perdant de Select : nettoyage unique.
- Lecture du vecteur après await admise ; lecture pendant la capture mutable
  et option reçue sans usage explicite refusées.
- Retour de l'allocation hors du bloc du vecteur admis si son pool survit ;
  pool local trop court refusé. Le cas de capture trop courte est refusé dès
  l'insertion dans le vecteur extérieur : il ne constitue pas une preuve isolée
  du contrôle à la frontière de sortie de la tâche.

Le cas initial conservé est validation/open-async-handle-option-result.crust.
Son journal .log documente le refus antérieur ; le même programme est désormais
exécuté par le test ciblé et produit 7 puis 8.

## Preuves d'exécution

| Journal dans validation/ | Résultat |
| --- | --- |
| async-handle-option-results-first-o0.log | Six méthodes, 4,437 s, code 0 |
| async-handle-option-results-second-o0.log | Huit méthodes, 4,734 s, code 0 |
| async-handle-option-results-regression-o2.log | 74 méthodes, 113,097 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_option_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_results test_async_handle_option_calls test_async_handle_vector_pop test_async_awaited_owned_results test_async_owned_struct_returns test_select_source test_factory_owned_effects -v
```

C11/pthread, avertissements traités en erreurs, UBSan fatal. Les résultats
attendus, le comptage des destructions et le réemploi des pools sont contrôlés
par les tests. La régression inclut le modèle existant d'ordre de poll/nettoyage
de Select. Aucun nouveau modèle indépendant, aucune campagne de mutations ni
recherche adversariale élargie : cette phase reste distincte, conformément à
la priorité donnée par l'utilisateur. Ces exécutions ne prouvent pas la sûreté
générale du langage.

## Limites et suite

Le périmètre porte sur Option<A<Int>>, pas sur toutes les formes génériques
d'Option. L'enveloppe Result<Option<A<Int>>,runtime::Error> de spawn/join et les
handles publics correspondants restent à raccorder. Les autres opérations de
vecteurs et les arbitrages publics ouverts ne sont pas clôturés par ce lot.
reset reste retiré du prototype ; aucune nouvelle validation ne le réintroduit.

Snapshot : /tmp/crust-before-async-handle-option-results/.
Diffs : validation/async-handle-option-results-{async_lowering.py,async_result_storage.py,async_structure_effects.py,results.py,crust.py}.patch.
