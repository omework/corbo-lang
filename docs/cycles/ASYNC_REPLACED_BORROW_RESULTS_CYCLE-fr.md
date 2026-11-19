[English](ASYNC_REPLACED_BORROW_RESULTS_CYCLE.md)

# Résultats empruntés après remplacement d'un descendant

## Règles et défaut corrigé

Ce lot applique les règles existantes de retour d'emprunt, de remplacement et
de durée de vie, ainsi qu'AS16 et SL1. Aucune nouvelle sémantique n'est introduite.
Une référence partagée sauvegardée avant le remplacement garde son ancienne
cible. Une lecture du descendant après remplacement désigne la nouvelle cible.
Le résultat emprunté peut survivre au porteur lorsque sa cible est extérieure
et demeure valide.

Le cas enregistré est
`validation/open-async-replaced-descendant-borrow.crust`. Le snapshot antérieur
le refuse aux deux entrées avec « projection du retour async : champ Int ou
référence Int requis ». L'état corrigé le vérifie, produit du C et affiche 9.

Le contrat propriétaire suivait le nouveau descendant, mais la vue aplatie
des champs empruntés du parent conservait l'ancienne projection. Le résolveur
symbolique actualise maintenant cette vue lors du remplacement, sans modifier
les snapshots des références déjà détachées. La projection des captures de
résultat traverse aussi les descendants possédés avant de projeter le champ
terminal : elle peut ainsi conserver la cible ancienne d'un résultat sauvegardé.

## Cas exécutés

Le module `test_async_replaced_borrow_results` comporte six méthodes :

- Contrats distinguant exactement la cible ancienne et le paramètre nouveau.
- Exemple enregistré, avec refus du drop de la cible retournée.
- Join depuis main, pour un résultat ancien ou nouveau ; destruction du porteur
  et de la cible devenue inutile avant lecture ; échec de lancement injecté.
- Relais par deux fonctions async, yield et attentes successives.
- Remplacement conditionnel : deux branches exécutées et deux cibles conservées
  statiquement dans le contrat.
- Résultat du gagnant de Select utilisé après destruction de Select et du porteur.

Par passage complet : dix exécutions natives, dix programmes invalides testés
aux deux entrées (vingt contrôles de refus), plus les deux contrôles de contrat.
Les programmes valides distinguent 7 pour l'ancien emprunt, 9 pour le nouveau
et 11 pour le résultat de repli lors d'un échec de lancement.

## Résultats

- Six méthodes à O0 : 4,968 s, code 0 ;
  `validation/async-replaced-borrow-results-expanded-o0.log`.
- Six méthodes à O2 : 4,891 s, code 0 ;
  `validation/async-replaced-borrow-results-final-o2.log`.
- Régression liée : 125 méthodes, 64,791 s, code 0 ;
  `validation/async-replaced-borrow-results-regression-o2.log`.
  Elle a chargé les quatre premiers tests ciblés, avant l'ajout des deux derniers.
  Aucun changement d'implémentation n'a suivi son lancement ; les six tests
  ciblés finaux couvrent les deux ajouts à O0 et O2.

Les exécutions natives utilisent Clang C11, pthread et UBSan sans récupération.
La régression comprend les effets de champs, résultats propriétaires, champs
mutables, descendants, alternatives et relais synchrones. Certains modules
historiques importent d'autres classes de tests, incluses dans le total annoncé.

Le premier brouillon du cas enregistré détruisait depuis un bras de match des
variables possédées dans son parent sans transfert d'entrée. Il a été corrigé
pour recevoir le résultat puis effectuer les drops dans le scope parent. Le
refus de projection a ensuite été reproduit sur ce cas corrigé avec le snapshot
antérieur. Aucune règle n'a été assouplie pour admettre le programme.

## Limites

Les résultats exercés sont des références partagées Int vers des cibles
extérieures aux descendants remplacés. Ce lot ne déclare pas raccordés tous les
résultats mutables, les autres types de cibles, les graphes récursifs ou toutes
les formes de fabriques. Les alternatives de lancement et de branche restent
conservatrices. Aucun nouvel audit adversarial ni campagne de mutations ; les
modèles déjà inclus dans les régressions ont été exécutés, sans nouveau modèle
indépendant. Ces résultats ne constituent pas une preuve générale de sûreté.

Les retours &mut Int depuis les descendants sont désormais raccordés dans le
[lot suivant consacré aux capacités mutables](ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE.md),
avec ses propres cas et limites.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_replaced_borrow_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_replaced_borrow_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_replaced_borrow_results test_async_owned_borrow_writes test_async_owned_field_writes test_borrowed_field_completion test_mutable_field_completion test_async_enum_suspension_fields test_async_structure_effects test_suspension_effects test_owned_results test_nested_field_choices test_nested_field_wrappers -v
```

La dernière commande comprend maintenant deux méthodes de plus que le passage
de régression enregistré. Snapshot :
`/tmp/crust-before-async-replaced-borrow-results/`. Différences :
`validation/async-replaced-borrow-results-results.py.patch` et
`validation/async-replaced-borrow-results-crust.py.patch`.
