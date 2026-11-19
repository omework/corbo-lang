[English](NESTED_FIELD_WRAPPERS_CYCLE.md)

# Contrats modifiant un descendant via un emprunt du parent

## Périmètre normatif

Ce lot poursuit ST6–ST15, B1–B5, D1, T1/T6 et les contrats d'effets existants.
Une fonction peut recevoir le parent par &mut et modifier une référence dans
un descendant A<T>. L'appelant doit appliquer cette modification au descendant
concerné, conserver les cibles des autres champs et vérifier les durées de vie.
Aucune nouvelle règle de langage n'est introduite.

Le programme `validation/open-nested-field-wrapper.crust`, refusé aux deux étapes
au lot précédent, est maintenant exécuté. Les relais successifs, un emprunt
nommé du parent, les cibles partagées/mutables et une source provenant d'un autre
porteur sont couverts. Les appels restent vérifiés depuis les contrats.

## Implémentation et défauts trouvés

L'analyse des contraintes conserve le propriétaire et le chemin d'une projection
mutable d'un descendant. Le contrat peut actualiser cette projection et publier
les dépendances sur les chemins complets du parent. Le backend utilise les
chemins de champs possédés, tels que `.inner/.view`, pour retrouver leur type
et appliquer les prêts correspondants.

Pendant ce raccordement, un remplacement conditionnel perdait la cible initiale :
les enfants symboliques d'un paramètre emprunté étaient construits sans leurs
champs empruntés. L'ancienne cible pouvait alors être détruite avant le transfert
ou l'attente. Le journal initial conserve le refus attendu manquant aux deux
étapes ; `validation/counterexample-nested-field-wrapper-conditional.crust`
est la variante minimale où la branche ne modifie pas le champ. Les enfants
symboliques héritent désormais des cibles initiales. Les deux issues du contrat
restent possibles et le programme est refusé. Le C invalide n'a pas été exécuté.
Le compilateur du lot précédent refusait le wrapper entier ; ce défaut a été
détecté dans l'extension en cours avant de la déclarer validée.

Chez l'appelant synchrone, la mise à jour était ensuite appliquée au mauvais
niveau : les chemins imbriqués étaient ignorés par le résolveur destiné aux
champs d'un slot unique. Le compilateur parcourt maintenant les arêtes possédées,
résout les cibles pour le type du descendant et prépare la modification de ce
dernier. La cible précédente n'est plus conservée à tort après une affectation
certaine. Les chemins indirects non possédés non raccordés sont refusés
explicitement, sans leur substituer un effet vide.

## Vérification

La suite ciblée finale passe 10 méthodes à O0 en 14,634 s : 17 exécutions
natives, 16 programmes invalides et 32 contrôles de refus. Journal
`validation/nested-field-wrapper-final-count-o0.log`. Le baseline O2 des
mutations passe ces mêmes 10 méthodes en 14,638 s ; les cinq mutations
sont détectées par assertions, sans survivante dans cette campagne choisie.
Journal `validation/nested-field-wrapper-final-mutations-o2.log`.

La régression élargie passe 153 méthodes à O2 en 149,359 s, avec UBSan.
Journal `validation/nested-field-wrapper-regression-o2.log`. Elle avait été
lancée avec les sept premières méthodes du lot ; les trois suivantes passent
dans les baselines finaux O0/O2. La commande ci-dessous lancée maintenant
inclut donc 156 méthodes. Tous les processus cités sont terminés avec code 0.
Ce petit échantillon de mutations ne fournit pas un taux global de détection.

La suite ciblée couvre :

- le contrat publié `.inner/.view` et sa source de paramètre ;
- deux relais, un parent emprunté nommé, un autre porteur source ;
- le maintien de la cible mutable et le refus des destructions prématurées ;
- la variante conditionnelle et le contre-exemple enregistré ;
- les appelants sync/async, un échec de lancement et le réemploi du slot ;
- un modèle indépendant de deux arêtes et trois cibles : 12 combinaisons,
  7 admises exécutées et 5 refusées aux deux étapes ;
- la lecture du descendant modifié suivie de l'affectation à son frère.

Ce dernier scénario détecte la mutation `forget_child_targets`, survivante au
lot précédent. La perte des champs de l'enfant provoque désormais un refus
incorrect du programme valide. Le constat précédent reste historique, sans
prétendre qu'il démontrait l'équivalence de cette mutation. L'expérience est
conservée dans `validation/nested-field-wrapper-former-survivor-o2.log` et
intégrée à la campagne permanente.

Les programmes natifs utilisent clang C11/pthread, les avertissements comme
erreurs, UBSan fatal et O0/O2. Aucun résultat ASan/TSan nouveau. Les essais
intermédiaires sont conservés ; l'oracle des cas valides/refusés n'a pas été
affaibli pour contourner les défauts.

Commandes finales :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_wrappers.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_wrapper_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_field_wrappers test_nested_field_replacement test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
```

## Limites et suite

Le choix conditionnel entre deux descendants avant la modification reste valide
mais refusé : `validation/open-nested-field-choice.crust`. Le journal
`validation/nested-field-wrapper-choice-probe.log` conserve les deux diagnostics.
Le suivi doit représenter plusieurs projections possibles, sans attribuer
la modification de façon certaine à tous les descendants ni oublier leurs
anciennes cibles. Ce point reste ouvert, ainsi que les signatures générales
et l'API publique de remplacement du scheduler.

Mise à jour : le choix entre descendants est désormais traité dans
[NESTED_FIELD_CHOICES_CYCLE.md](NESTED_FIELD_CHOICES_CYCLE.md). Les résultats
de ce rapport restent ceux de la campagne originale.

Les tests ne constituent ni une preuve générale de sûreté ni une couverture
de tous les graphes. Les quatre différences du compilateur sont archivées
dans `validation/nested-field-wrapper-*.py.patch` depuis le snapshot
`/tmp/crust-before-nested-field-wrapper`. L'objectif global reste actif.
