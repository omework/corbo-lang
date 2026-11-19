[English](RESIDUAL_ERROR_PATTERNS_CYCLE.md)

# Cycle — bras Err(_) après une variante précise

## Défaut et correction

F2 autorise un motif résiduel pour les variantes non encore couvertes.
Le programme `validation/open-read-error-residual-pattern.crust` était
pourtant refusé : après `Err(ReadError::CapacityExceeded)`, le parseur
attribuait Utf8Error au motif `Err(_)` et diagnostiquait deux types différents.
Le contre-exemple est découvert pendant le cycle des opérations Vector async.
Son log initial est conservé. Aucune décision normative nouvelle.

Le parseur conserve maintenant la famille d’erreurs déjà connue et développe
le corps résiduel sur ses seules variantes restantes. Il ne couvre pas Ok.
Les corps dupliqués sont des copies distinctes de l’AST, notamment pour les
temporaires et points de reprise async. Une erreur déjà couverte ne peut pas
être répétée ; un Err(_) sans variante restante est inaccessible. L’absence
de branche Ok ne devient pas exhaustive par l’ajout d’un Err(_).

La modification est limitée à la préparation des bras. Le sujet reste évalué
une fois dans son scope ; l’analyse des emprunts et la génération C des bras
utilisent les mécanismes existants. Les tests voisins contestent les transferts,
retours anticipés, provenance des vues et extraction de handles possédés.

## Scénarios et preuves

`tests/test_residual_error_patterns.py` comporte six méthodes : 19 programmes
natifs et cinq refus attendus par passage. La table d’observation est fixée
indépendamment du parseur : lecture réussie → nombre d’octets ; capacité → 92 ;
autres erreurs → 90. La table est exécutée en sync et async avec contenu lu,
EOF, mauvais descripteur et région réellement pleine. Le motif Err(_) précède
Ok dans ces programmes, ce qui détecte une confusion avec un wildcard global.

Un match utilisé comme valeur suspend dans le bras résiduel ; son compteur
avance une fois. La conversion char exerce Empty, MultipleChars et succès.
La découpe &str exerce OutOfBounds, NotCharBoundary et succès emprunté. Les
refus portent sur Ok absent, variante dupliquée après le résiduel, résiduel
après couverture complète, second résiduel et famille d’erreur incompatible.

| Exécution terminée | Résultat | Trace |
| --- | --- | --- |
| Nouveau lot O0 | 6 méthodes, 6,728 s, réussi | validation/residual-error-patterns-O0.log |
| Lot O2, opérations/résultats Vector et découpes UTF-8 | 52 méthodes, 60,561 s, réussi | validation/residual-error-patterns-O2-regression.log |
| Fondamentaux et voisin async char_at | 22 méthodes, 11,825 s, réussi | validation/residual-error-patterns-foundations.log |
| Mutations | Trois détectées | validation/residual-error-patterns-mutations.log |

Clang 20.1.3 arm64 macOS, C11, pthread et UBSan fatal pour les nouveaux
programmes. Les anciens helpers ont leurs propres options : CRUST_TEST_OPT
ne prouve pas à lui seul leur niveau d’optimisation. Le compteur des nouveaux
scénarios n’inclut pas les exécutions des anciens tests.

Trois fautes sont introduites dans des copies temporaires : n’émettre que la
première erreur résiduelle, effacer le corps résiduel et désactiver le contrôle
d’exhaustivité. Les trois produisent des échecs d’assertion sémantique attendus.
Aucun résultat n’est extrapolé à l’ensemble du parseur. Les tables de résultats
attendus sont indépendantes ; pas d’exploration exhaustive ni de preuve formelle.
La compilation Python des fichiers modifiés a réussi.

## Limites et prochain contre-exemple

Le traitement autonome des types d’erreurs reste incomplet. Le programme
`validation/open-async-read-error-binding.crust` lie `Err(error)`, puis le
consomme explicitement avec drop et renvoie -1. Il reste refusé à tort par
le contrôle du motif async. Le log est conservé ; ce refus n’est pas une règle
du langage. Cette correction du wildcard ne prétend pas implémenter les enums
généraux ni fermer les autres obligations des sept brouillons.

Mise à jour : [BUILTIN_ERROR_VALUES_CYCLE.md](BUILTIN_ERROR_VALUES_CYCLE.md)
corrige ce refus et vérifie les liaisons, captures et retours des sept types
d’erreurs builtin nommés. Le log antérieur reste historique.

Pas d’ASan/TSan ou de second compilateur C dans ce cycle. Les politiques de
stockage et de destruction sont inchangées, et reset demeure hors prototype.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_residual_error_patterns -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_residual_error_patterns test_async_vector_operations.AsyncVectorOperationTests test_utf8_try_slice test_utf8_try_slice_async test_async_vector_results -v
CRUST_TEST_OPT=-O2 python3 tests/run_residual_error_pattern_mutations.py
```
