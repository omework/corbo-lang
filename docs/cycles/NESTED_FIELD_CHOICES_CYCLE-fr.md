[English](NESTED_FIELD_CHOICES_CYCLE.md)

# Choix entre plusieurs descendants empruntés

## Règles et portée

Ce lot applique les règles de branchement, B1–B5, D1, ST6–ST15 et les contrats
d'effets existants. Une référence mutable peut désigner un descendant choisi
par if ou par un résultat de boucle. Modifier son champ ne modifie qu'un
emplacement à l'exécution ; le contrat doit réunir les effets possibles et
conserver l'ancienne cible de chaque emplacement qui peut ne pas être choisi.
Deux branches désignant le même emplacement permettent un remplacement certain.
Aucune nouvelle sémantique normative n'est ajoutée.

`validation/open-nested-field-choice.crust`, auparavant refusé, est accepté et
exécuté. La suite vérifie les deux choix à l'exécution, les effets publiés par
champ, les références mutables et un choix entre un objet entier et un descendant.

## Implémentation

Les valeurs symboliques gardent des alternatives de porteur et de projection.
Les fusions de if, de boucle, de match et d'environnements les conservent.
Une mise à jour analyse séparément chaque alternative depuis l'état d'entrée,
puis réunit les états obtenus. Elle n'applique pas les écritures successivement
à tous les candidats. Les projections supplémentaires après le choix suivent
le même mécanisme. Les alternatives identiques sont dédupliquées.

L'analyse des résultats et celle des contraintes conservent chacune ce suivi.
L'utilitaire de fusion des valeurs de référence est partagé avec les tableaux,
d'où la régression spécifique de ce sous-système. Les structures possédées
restent stables en mémoire ; aucun déplacement d'allocation n'est introduit.

Le backend reconnaît aussi l'alternative inchangée d'un champ mutable : la
capacité de ce même champ ne constitue pas une nouvelle cible locale échappante.
Cette exception exige l'identité exacte du porteur et du chemin de destination.

## Contre-exemple trouvé

Pendant le raccordement, `verify_program` acceptait la destruction de first
avant l'attente d'une tâche, alors que `compile_source` refusait le programme.
Le contrat conservait bien `.inner/.view`, mais sa résolution chez l'appelant
opaque cherchait la dépendance sur le parent au lieu du descendant. La cible
ancienne disparaissait ainsi des obligations appliquées.

Le programme est conservé dans
`validation/counterexample-choice-sync-first.crust`. Les deux étapes le refusent
maintenant. La résolution parcourt la provenance du porteur intermédiaire,
puis résout le champ terminal avec le type et les capacités appropriés.
Le C invalide n'a pas été exécuté. Une première tentative réutilisant le
résolveur des retours avec un type intermédiaire incorrect refusait les cas
valides ; le journal de la deuxième suite garde cet échec.

## Preuves exécutées

La suite ciblée passe 11 méthodes à O0 en 17,777 s : 17 exécutions natives,
15 programmes invalides et 30 contrôles de refus. Journal
`validation/nested-field-choice-count-o0.log`.

Le modèle indépendant calcule les cibles encore accessibles selon que les
branches désignent le même enfant ou des enfants différents, puis selon que
la destruction intervient avant ou après attente. Ses 12 combinaisons donnent
7 programmes exécutés et 5 refusés aux deux étapes, inclus dans les nombres
ci-dessus. Les autres tests couvrent les relais synchrones, les boucles,
les écritures répétées, la projection d'un niveau supplémentaire et les deux
choix observables dans le C généré.

La régression des tableaux fixes et des lignes contenant des références passe
90 méthodes à O2 en 85,967 s. Journal
`validation/nested-field-choice-array-regression-o2.log`. Elle inclut leurs
modèles de liste et leurs scénarios générés existants.

La régression finale des contrats, structures et interactions async passe
178 méthodes à O2 en 204,690 s. Journal
`validation/nested-field-choice-final-regression-o2.log`. Une première campagne,
lancée avant la correction de la capacité mutable inchangée, avait terminé
176 méthodes en 200,480 s avec ce seul échec connu ; son journal est conservé
dans `nested-field-choice-regression-o2.log`.

La première campagne de mutations détecte quatre fautes sur cinq. Supprimer
les alternatives de l'analyse des contraintes survit au test initial choisi,
mais échoue sur la suite ciblée complète, exécutée en 14,411 s : le cas mêlant
objet entier et descendant devient refusé à tort. Ce test existant est désormais
la cible de cette mutation. Aucun oracle n'a été affaibli. Les journaux
`nested-field-choice-mutations-o2.log` et `nested-field-choice-survivor-o2.log`
conservent l'investigation dans validation.

La campagne finale passe son baseline de 11 méthodes à O2 en 10,033 s et
détecte les cinq fautes par assertions. Journal
`validation/nested-field-choice-final-mutations-o2.log`. Tous les processus
cités sont terminés. Les campagnes finales sortent avec code 0 ; les essais
intermédiaires gardent leurs codes d'échec, sans masquer la chronologie.

Les programmes natifs utilisent clang C11/pthread, O0/O2, les avertissements
comme erreurs et UBSan fatal. Les suites historiques demandent
`CRUST_SANITIZE=undefined`. Aucun nouveau résultat ASan ou TSan n'est revendiqué.
Une campagne réussie ne fournit ni preuve générale de sûreté ni taux global
de détection des mutations.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_choices.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_choice_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_field_choices test_nested_field_wrappers test_nested_field_replacement test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_fixed_arrays test_nested_reference_rows -v
```

## Limites et suite

Les unions de cibles restent conservatrices et ne décrivent pas toutes les
corrélations entre plusieurs choix successifs. Les graphes récursifs, les
signatures générales et les compositions non représentées restent à auditer.
Ce lot ne revendique pas l'implémentation complète des sept brouillons.

L'interface publique du scheduler reste ouverte : RT3 fixe le point
d'installation et les responsabilités, sans préciser le type ni les signatures
du scheduler fourni. Une clarification a été demandée sur l'existence d'un
arbitrage plus récent, sans bloquer le travail indépendant ni inventer cette API.

Les cinq différences sont archivées dans
`validation/nested-field-choice-*.py.patch` depuis le snapshot
`/tmp/crust-before-nested-field-choice`. L'objectif global reste actif.
