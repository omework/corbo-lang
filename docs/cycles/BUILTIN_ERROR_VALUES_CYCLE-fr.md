[English](BUILTIN_ERROR_VALUES_CYCLE.md)

# Cycle — valeurs d’erreurs builtin dans les contrats et les tâches

## Portée normative et changement

Ce cycle applique F2/B5, F5, VE4, TX4 et AS2/AS8/AS10/AS12 avec RT5/RT6.
Les règles demeurent celles de LANGUAGE_RULES.md et de ses extensions.
AGENTS.md, VALIDATION_GUIDELINES.md, l’index des brouillons et les points
reportés ont été relus. Pas de nouvelle sémantique ni de réintroduction de reset.

Le contre-exemple `validation/open-async-read-error-binding.crust` lie
Err(error), consomme cette erreur explicitement et retourne -1. Il était
refusé par la vérification du motif ; il s’exécute maintenant avec -1.
La limitation n’était pas seulement syntaxique : les analyses de résultats,
de contraintes et d’effets assimilaient plusieurs erreurs à leur valeur de
succès. Elles produisent désormais le type d’erreur sans dépendance de stockage.

Types intégrés : ReadError, CapacityError, ByteReplaceError, CharAtError,
CharFromStrError, IntegerConversionError et SliceError. Les variantes déjà
définies par les APIs sont reconnues comme valeurs. Les liaisons, copies,
réaffectations, résultats if/loop/match, drop, signatures sync, captures et
retours async conservent leur type nominal. Un même entier C ne constitue
pas une conversion entre types Crust. Les champs de join sont dédiés et la
charge métier reste séparée du statut runtime::Error de lancement.

Err(error) extrait le statut exact, y compris après un bras d’erreur précis.
Le parseur développe alors les seules variantes restantes comme pour Err(_),
avec des corps AST distincts. Les contrôles d’exhaustivité et de type restent
effectifs. Un sujet de match calculé est matérialisé une fois avant le bras,
même lorsqu’il suspend. Les tests de compteur vérifient cette propriété.

Un détail de C généré a également été corrigé : le handle nommé d’une
allocation immédiatement détruite était parfois inutilisé, la destruction
employant le nom interne de l’allocation. L’émission le marque utilisé avant
drop, sans ajouter de destruction ni désactiver l’avertissement du compilateur C.

## Scénarios, oracles et contre-exemples

Le module final `tests/test_builtin_error_values.py` contient 14 méthodes,
60 exécutions natives et 61 refus attendus par passage complet. Une table
indépendante de sept types et treize variantes détermine les sorties attendues ;
elle n’importe pas les codes internes du compilateur. Chaque variante passe
par une capture et un retour, avec observation sync ou async. Sept résultats
sont aussi extraits par await d’un handle dans un parent async.

Treize issues d’opérations couvrent EOF, capacité et Io, remplacement d’octet,
décodage, conversion et découpe. Les premières variantes sont incluses afin
qu’un statut erroné ne soit pas masqué par la dernière branche d’un match.
La saturation utilise réellement une région 1M. Une erreur est lue après
drop du Result, après suspension et après drop/réemploi du stockage source.
Le résultat d’erreur ne doit pas porter l’emprunt de la valeur de succès.

La matrice nominale contient 42 paires de types incompatibles. S’ajoutent les
refus de conversion en Int, de lecture après drop, de mauvais retours,
captures ou contrats, et de motifs incomplets, dupliqués ou incompatibles.
Les enveloppes de join sont testées avec réussite et EAGAIN injecté. Les
13 variantes et les paires de types constituent une exploration finie ;
pas une preuve générale du système de types.

Les logs initiaux sont conservés. Sept exécutions avaient échoué sur
l’avertissement C du handle immédiatement détruit ; l’émission a été corrigée.
Un test initial tentait aussi de drop un Result du scope parent directement
dans le bras enfant : ce scénario était invalide selon la règle de scope.
Il est remplacé par une extraction de l’erreur suivie du drop dans le scope
du Result, puis d’une suspension et de la lecture indépendante.

## Validation exécutée

Clang Homebrew 20.1.3, arm64 macOS, C11/pthread, avertissements stricts,
UBSan fatal à O0/O2 pour les nouveaux tests. Les anciens helpers ont leurs
propres options ; CRUST_TEST_OPT ne garantit pas leur niveau d’optimisation.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| Lot O0 avant ajout du résiduel nommé | 13 méthodes, 31,875 s, réussi | validation/builtin-error-values-O0-final.log |
| Complément extraction sync O0 | 1 méthode, 1,541 s, réussi | validation/builtin-error-values-sync-O0.log |
| Complément extraction sync O2 | 1 méthode, 2,069 s, réussi | validation/builtin-error-values-sync-O2.log |
| Complément résiduel nommé O0 | 1 méthode, 1,550 s, réussi | validation/builtin-error-values-residual-O0.log |
| Lot final O2 et motifs résiduels | 20 méthodes, 31,230 s, réussi | validation/builtin-error-values-O2-final.log |
| Résultats, vecteurs, motifs, runtime::Error, contrats, contraintes et effets | 113 méthodes, 105,447 s, réussi | validation/builtin-error-values-O2-regression.log |
| Résultats imbriqués/métier et vues UTF-8 | 38 méthodes, 55,465 s, réussi | validation/builtin-error-values-envelopes.log |
| ABI, tableaux, emprunts, pools et attentes calculées | 15 méthodes, 24,034 s, réussi | validation/builtin-error-values-abi.log |
| Nouvelles mutations | Cinq détectées | validation/builtin-error-values-mutations.log |
| Mutations des enveloppes métier rejouées | Quatre détectées | validation/builtin-error-values-old-mutations.log |

O0 est couvert par le lot initial et ses compléments. Le complément sync
ajoute un cas Empty qui manquait à l’oracle initial. Les comptes du module
final ne doivent pas être attribués rétroactivement aux premières passes.

Les mutations effacent le statut extrait dans Vector async, UTF-8 async et
sync, désactivent le contrôle nominal des captures et celui du match d’erreur.
Les cinq sont détectées par des assertions sémantiques. Aucun taux global
n’est inféré. L’ancre de l’ancien test de mutation du contrôle des captures
a été adaptée à la garde enrichie ; son oracle n’a pas changé. La compilation
Python des modules et scripts modifiés a réussi.

## Limites et travail restant

Ce cycle ne généralise pas tous les enums utilisateur, leurs emprunts,
leur stockage dans les agrégats ou tous les Result paramétriques. Le type
historique Utf8Error, dont les variantes nommées ne sont pas définies dans
ce catalogue, n’est pas ajouté artificiellement à ces sept types. Aucune
nouvelle variante publique n’a été inventée.

Le prochain écart est reproduit dans
`validation/open-async-vector-remove.crust` et son log : remove d’un élément
Copy dans un corps suspendable reste refusé. Le programme devrait rendre 17,
puis une longueur de 1 et l’élément restant 29. Les travaux plus larges sur
les handles publics, scheduler, threads, Select, mutex et les autres lignes
N/P de la matrice restent ouverts. Les points explicitement reportés restent
reportés. Ni ASan/TSan, ni deuxième compilateur C, ni preuve formelle dans ce cycle.

Mise à jour : [ASYNC_VECTOR_REMOVE_CYCLE.md](ASYNC_VECTOR_REMOVE_CYCLE.md)
corrige et exécute le contre-exemple remove ci-dessus. Le log du refus initial
reste historique.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_builtin_error_values -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_builtin_error_values test_residual_error_patterns -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_builtin_error_values test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_residual_error_patterns test_runtime_error_values test_plain_join_contracts test_constraints test_effects -v
CRUST_TEST_OPT=-O2 python3 tests/run_builtin_error_value_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_mutations.py
```
