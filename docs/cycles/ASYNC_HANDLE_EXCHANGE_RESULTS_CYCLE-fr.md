[English](ASYNC_HANDLE_EXCHANGE_RESULTS_CYCLE.md)

# Captures et retours async des résultats de replace et try_push

## Règles et implémentation

Application de H1–H2, VE3–VE4, U1, F4, B1–B5, AS2–AS5, AS8–AS14 et
SL1–SL2, sans modification normative. Une instance async peut recevoir par
transfert `Result<A<Int>,A<Int>>` ou `Result<(),A<Int>>` et retourner cette
enveloppe par await d'une instance inactive. Le déplacement transporte le
handle et sa provenance ; il ne déplace pas l'allocation ciblée.

Le générateur conserve le type de contenu Int séparément du type de
l'enveloppe, distingue les charges Ok/Err, et raccorde les captures, retours
directs ou nommés, fabriques synchrones, relais async et helpers synchrones.
Les résumés de terminaison transportent les provenances par bras. Leur
projection dans les contrats de fabriques et dans le stockage des tâches
conserve ces informations après await.

Pour replace, les deux variantes possèdent une allocation. Pour try_push,
Ok(()) ne possède rien ; Err possède l'entrant rejeté. Les captures préparées
et les états inactifs respectent cette distinction. Le pointeur d'une capture
try_push réussie est normalisé à NULL et son nettoyage inactif vérifie aussi
le statut. Les chemins suspendus utilisent les obligations correspondantes.

## Défauts rencontrés

Le premier passage a révélé les captures non raccordées depuis main et la
perte des provenances de bras dans les fabriques. Leurs contrats et les ponts
de capture ont été complétés. Une erreur d'indentation introduite pendant
cette modification a interrompu le deuxième passage avant exécution native ;
elle a été corrigée au passage suivant.

Le cinquième passage a détecté un double nettoyage après capture d'un
try_push réussi, puis destruction de la tâche inactive. Le C synchrone
conservait un pointeur dans la variante Ok ; le nettoyage inactif traitait
ce pointeur comme une allocation encore possédée. Le vecteur nettoyait ensuite
la même allocation. UBSan a signalé un accès via un pointeur nul après le
double passage. Le test et son oracle sont conservés ; le nettoyage a été
corrigé, sans changer la sémantique de try_push.

Reproduction : `validation/regression-async-try-push-inactive-capture.crust`.
Le résultat attendu est 8 puis 9, avec une seule destruction de l'entrant.
Ce cas est exécuté dans la suite ciblée, avec les variantes de capacité pleine,
d'échec de lancement et de préparation suspendue.

## Cas ciblés

Dix méthodes dans `tests/test_async_handle_exchange_results.py` : 28
exécutions natives et sept programmes invalides aux deux entrées.

- Retours directs et nommés, succès/erreur de replace ; absence de flèche refusée.
- Fabrique synchrone, relais async d'une capture et helper synchrone après await.
- Capture depuis main, transfert explicite et réutilisation de la source refusée.
- Destruction inactive et échec de soumission, avec nettoyage unique et réemploi.
- Ancienne allocation provenant d'un pool extérieur, tandis que le vecteur et
  le pool de l'entrante disparaissent ; source trop courte refusée.
- Réservation du vecteur jusqu'à await et double consommation refusée.
- Résultat try_push retourné puis capturé, sur succès et capacité atteinte.
- Enfant suspendu d'un perdant Select et nettoyage de son résultat.
- Capture préparée à partir d'un helper synchrone avant l'await de l'argument
  suivant ; continuation ou destruction par Select, sur succès et erreur.

Les cas pleins atteignent effectivement une région de 1 MiB. Aucune limite du
runtime n'est réduite dans le C généré. Les échecs de soumission sont injectés
par le dispositif existant, distinct des oracles de valeurs et de destruction.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| open-async-handle-exchange-result.log | Refus initial de la signature async aux deux entrées |
| async-handle-exchange-results-first-o0.log | Quatre méthodes, 1,881 s, trois échecs |
| async-handle-exchange-results-second-o0.log | Quatre méthodes, 0,026 s, erreur de syntaxe Python |
| async-handle-exchange-results-third-o0.log | Quatre méthodes, 5,418 s, code 0 |
| async-handle-exchange-results-fourth-o0.log | Huit méthodes, 8,607 s, code 0 |
| async-handle-exchange-results-fifth-o0.log | Neuf méthodes, 9,296 s, un échec : double nettoyage détecté par UBSan |
| async-handle-exchange-results-sixth-o0.log | Neuf méthodes, 11,589 s, code 0 |
| async-handle-exchange-results-seventh-o0.log | Dix méthodes, 13,515 s, code 0 |
| async-handle-exchange-results-regression-o2.log | 109 méthodes, 105,405 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_exchange_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_exchange_results test_async_handle_exchange_calls test_async_handle_vector_replace test_async_handle_vector_try_push test_async_handle_option_results test_async_handle_option_calls test_async_option_join test_async_structure_effects test_factory_owned_effects test_select_source -v
```

Tests natifs via le harnais C11/pthread, avertissements en erreurs et UBSan
fatal, à O0 pour le ciblé et O2 pour la régression. La régression porte sur les fonctions et contrats modifiés, les
opérations de handles, les options et Select. Pas de nouvelle campagne
adversariale ou de mutations ; le modèle existant de poll/nettoyage de Select
est rejoué dans la régression. Ces preuves concernent les chemins exécutés ;
elles ne constituent pas une preuve générale de sûreté.

## Limites et suite

Le résultat externe de spawn/join ajoute un niveau Result distinct. Il n'est
pas encore raccordé pour ces deux enveloppes et reste refusé explicitement,
depuis main comme depuis async. Le refus n'est pas une règle normative.
`validation/open-async-handle-exchange-join.crust` et son journal reproduisent
ce prochain travail aux deux entrées. Les handles publics correspondants et
les types d'éléments autres que A<Int> ne sont pas clôturés ici.

Snapshot : `/tmp/crust-before-async-handle-exchange-results/`.
Les cinq diffs sont archivés sous `validation/async-handle-exchange-results-`
pour async_lowering.py, crust.py, async_structure_effects.py, results.py et
async_result_storage.py.
