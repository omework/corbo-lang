[English](ASYNC_VECTOR_RESULTS_CYCLE.md)

# Cycle AS2/RT5/RT6 — Transport async des résultats de vecteurs

## Portée normative et implémentation

Ce cycle applique les règles retenues de capture immédiate AS2, d’attente AS4,
de résultats et provenances AS12, de join RT5/RT6 et d’usage U1. Les opérations
scalaires des vecteurs étaient déjà définies et exécutables en synchrone.
Aucune nouvelle sémantique ni décision normative n’est introduite. AGENTS.md,
VALIDATION_GUIDELINES.md, l’index des décisions et les clauses pertinentes sont
relus, en continuité avec la lecture complète des cycles précédents.

Le contre-exemple `validation/open-async-vector-value-result.crust` s’exécute
maintenant : un `Result<(),u8>` peut être capturé et retourné par une tâche.
Son ancien log de refus est conservé. Le support couvre huit familles déjà
existantes : Option<Int>, Option<u8>, Result<Int,Int>, Result<u8,u8>,
Result<(),Int>, Result<(),u8>, Result<(),CapacityError> et Result<Int,ReadError>.

Trois représentations C existantes (statut seul, statut/Int, statut/u8) sont
déplacées dans l’en-tête partagé. Le résultat de join possède des champs dédiés
pour les transporter. Les signatures inférées et explicites utilisent les
mêmes modes de type ; les enveloppes `runtime::Error` peuvent s’imbriquer comme
pour les précédentes charges simples. Les analyses d’effets et de provenances
extraient le bon type à chaque niveau.

Le code async peut copier, capturer, recevoir, retourner, réaffecter, détruire
et traiter ces valeurs par match. Les branches if, les résultats de boucle et
les attentes directes sont raccordés. Les motifs Option/Result, unit/valeur
et les charges Int/u8 restent distincts. Dans Err d’un replace/try_push,
l’extraction rend bien la valeur rejetée ; elle ne rend pas un runtime::Error.
Les vues empruntées et les propriétaires ne sont pas convertis en ces modes.

Les méthodes qui produisent ces résultats directement dans le corps async
restent un chantier distinct à compléter. Ce cycle valide leur production
synchrone suivie du transport et du traitement async, sans prétendre couvrir
l’exécution de ces méthodes dans une tâche.

## Modèle et scénarios

La table des tests est indépendante des modes internes et du C généré. Elle
fixe les issues de huit opérations, dont les valeurs rejetées -23 et 255.
Les scénarios de capacité remplissent réellement une région annotée 1M :
262144 Int ou 1048576 u8. Aucun statut de saturation n’est fabriqué dans le
programme de référence. La source Vector est détruite après le calcul du
résultat, avant sa capture par une tâche.

Les 32 configurations principales combinent huit familles, deux variantes et
une observation synchrone ou après recapture/suspension async, avec deux
niveaux de join. Seize configurations supplémentaires exercent le join direct
pour contrôler chaque champ de copie C. Quatre scénarios refusent le lancement
de la tâche interne ; l’erreur doit rester dans l’enveloppe runtime, pas devenir
une valeur rejetée par le vecteur.

La lecture utilise stdin contrôlé : trois octets reçus, fin de flux, erreur
sur descripteur -1 et capacité dépassée avant accès au descripteur. Ces issues
restent distinctes à travers les contrats et les joins. Les autres scénarios
exercent retours directs, if/loop, copie, réaffectation et drop.

Le module final a **11 méthodes, 56 exécutions natives et 13 refus attendus**.
Les refus portent sur mauvais type de capture/retour/annotation, confusion
Option/Result, confusion unit/valeur, utilisation de u8 comme Int sans
conversion, résultat inutilisé et lecture après drop. Les programmes voisins
valides sont exécutés ; une simple erreur de syntaxe n’est pas utilisée comme
preuve de refus sémantique.

## Vérification du C et limites

Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, avertissements stricts dans le
nouveau helper. UBSan est fatal à O0/O2. Le déplacement des types C communs
est vérifié également par les anciens scénarios de tâches, de tableaux, de
références, d’attentes calculées et de réemploi de pools.

Les résultats sans emprunt ne prolongent pas le stockage source. Le cycle ne
prouve pas ce fait pour tous les conteneurs : il couvre les modes explicitement
listés. Les résultats avec propriétaires ou références conservent leurs
chemins de vérification séparés. PR1 n’est pas modifiée ; les régressions
historiques avec reset conservent leur option explicite.

La matérialisation autonome de CapacityError et ReadError dans une liaison
`Err(error)` n’est pas encore prise en charge dans le code async. Les motifs
de variantes explicites sont exécutables et testés. Cette limite du prototype
n’est pas une nouvelle règle du langage ni une décision de rejeter ces usages
dans la conception finale.

Mise à jour : les valeurs CapacityError et ReadError autonomes sont intégrées
dans [BUILTIN_ERROR_VALUES_CYCLE.md](BUILTIN_ERROR_VALUES_CYCLE.md), avec les
autres erreurs builtin nommées et leurs contrats/captures/retours.

Un autre manque est reproduit dans
`validation/open-async-vector-result-producer.crust` et son log : un
`return v.try_push(n)` directement dans une tâche reste refusé pour expression
non prise en charge. Le type de résultat est maintenant accepté, ce qui
permet de poursuivre sur l’implémentation de l’opération elle-même.

Mise à jour du cycle suivant : ce manque est corrigé et son programme est
exécuté dans [ASYNC_VECTOR_OPERATIONS_CYCLE.md](ASYNC_VECTOR_OPERATIONS_CYCLE.md).
Le log du refus initial reste historique.

Les autres obligations des sept brouillons restent ouvertes : types et
conteneurs généraux, runtime::Handle<T>, scheduler public, runtime::thread,
Select, gardes et écarts de stockage déjà consignés. Les points expressément
reportés restent reportés. Aucun résultat de ce cycle n’est présenté comme
preuve générale de sûreté ; ni ASan, ni TSan, ni preuve formelle n’ont été
exécutés ici.

## Preuves d’exécution et mutations

| Exécution terminée | Résultat | Trace |
| --- | --- | --- |
| Nouveau lot O0 avant ajout du join direct | 10 méthodes réussies, 23,852 s ; 40 programmes natifs et 13 refus | validation/async-vector-results-O0-final.log |
| Complément O0 du join direct | 1 méthode réussie, 5,948 s ; 16 programmes natifs | validation/async-vector-results-O0-direct.log |
| Nouveau lot complet O2 | 11 méthodes réussies, 38,523 s | validation/async-vector-results-O2-final.log |
| Résultats métier/imbriqués/simples, runtime::Error, contraintes et effets | 86 méthodes réussies, 95,422 s | validation/async-vector-results-regression.log |
| ABI, attentes calculées, Bool/tableaux, emprunts et pools | 15 méthodes réussies, 29,247 s | validation/async-vector-results-abi.log |
| Mutations finales | 5 détectées | validation/async-vector-results-mutations-final.log |

Les anciens helpers contraintes/effets ont leur niveau d’optimisation propre ;
CRUST_SANITIZE active UBSan mais CRUST_TEST_OPT ne prouve pas leur exécution à
O2. Les nouveaux helpers utilisent explicitement cette variable. Les premiers
logs, antérieurs aux deux compléments de couverture, sont conservés. La
compilation Python des modules et des nouveaux tests/scripts a réussi.

Les mutations sont appliquées dans des copies temporaires. Elles effacent la
valeur du join direct, le contrôle du type de capture, le statut avant match,
la valeur restituée dans Err et le contrôle de forme des motifs. Les cinq sont
détectées par des assertions attendues. Les quatre premières mutations de la
campagne initiale étaient déjà détectées ; la cinquième vérifie le chemin
supplémentaire de copie directe. Aucune mutation survivante n’est masquée et
aucun taux de couverture global n’est déduit de cette sélection.

Commandes reproductibles :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_vector_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_async_vector_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_result_mutations.py
```
