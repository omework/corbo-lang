[English](NESTED_FIELD_REPLACEMENT_CYCLE.md)

# Remplacement des références dans les descendants possédés

## Règles appliquées

Ce lot applique les règles existantes ST6–ST15, B1–B5, D1, T1/T6,
AS2/AS8–AS15 et RT6 : une modification de champ change les dépendances
de ce champ, sans modifier celles de ses frères ; le transfert du graphe
conserve toutes les cibles encore accessibles. Les références mutables
restent exclusives. Aucun changement normatif n'est introduit.

Le programme `validation/open-nested-field-replacement.crust` peut maintenant
remplacer `outer.inner.view`, transférer outer dans une tâche et détruire
l'ancienne cible avant l'attente. La nouvelle cible reste réservée jusqu'à
la destruction du porteur. Les tests couvrent aussi un retour du graphe entier,
une modification dans la tâche productrice et deux niveaux de descendants.

## Implémentation et recherche de contre-exemples

L'analyse des résultats conserve le propriétaire et le chemin d'un emprunt
mutable de descendant. Les mises à jour de contrats peuvent viser cette
projection. Elles actualisent les champs du descendant et les chemins complets
sur son parent, sans remplacer les champs du parent par ceux de l'enfant.
Les descendants symboliques des paramètres possédés sont développés à la demande
en conservant leurs sources et les cibles empruntées.

Le backend résout chaque arête A<T> du chemin avant d'appliquer un effet de
champ. Il conserve le préfixe du descendant dans la clé du prêt. Les changements
conditionnels réunissent les anciennes et nouvelles cibles ; les frères restent
distincts, même avec des noms de champs identiques.

Une composition supplémentaire était refusée : le lancement d'une tâche issue
d'une fabrique, sans effets différés de champs. L'analyse de terminaison sait
maintenant utiliser son contrat complet même si la liste des écritures est vide.
Un contrat inconnu ne devient pas un effet vide ; les effets de suspension
de cette forme restent explicitement non raccordés.

Le fichier initial contenait aussi `value.view = target`, notation implicite
refusée par les règles retenues. Il utilise maintenant `&*target`. Le refus
du compilateur précédent sur cette version corrigée est conservé dans
`validation/nested-field-replacement-corrected-baseline.log` : les deux étapes
refusaient les dépendances du descendant. La fixture du producteur async a
également été corrigée pour déclarer son paramètre possédé `mut`.

## Preuves exécutées

- Suite ciblée à O0 : 11 méthodes, 18 exécutions natives, 18 programmes
  invalides, 36 contrôles de refus, en 8,251 s. Journal
  `validation/nested-field-replacement-count-o0.log`.
- Baseline de mutations à O2 : les mêmes 11 méthodes passent en 8,639 s.
- Régression async à O2 : 144 méthodes passent en 129,322 s ; régression
  synchrone : 46 méthodes passent en 38,188 s. Les journaux sont
  `nested-field-replacement-regression-o2.log` et
  `nested-field-replacement-sync-regression-o2.log` dans validation.
- Modèle indépendant inclus : deux arêtes possédées et trois cibles, remplacement
  certain ou conditionnel, destruction avant/après attente. Les 12 combinaisons
  donnent 7 cas exécutés et 5 programmes refusés aux deux étapes. L'oracle
  calcule les ensembles de cibles accessibles sans interroger le compilateur.
- Sorties et ordre de destruction vérifiés ; retour du graphe, maintien du
  nouvel emprunt mutable, cible de bloc trop court, homonymes et lancement
  refusé par le scheduler sont couverts.
- Quatre mutations ciblées : trois détectées, une survivante. Supprimer le
  préfixe de descendant, omettre toute mise à jour projetée ou perdre les
  cibles stockées sur le parent fait échouer les assertions. Supprimer seulement
  la mise à jour des champs du nœud enfant survit au test ciblé et aux 11 méthodes
  complètes, exécutées en 11,274 s dans une copie temporaire. Les chemins du
  parent restent suffisants dans ces scénarios. Aucune équivalence générale
  n'est revendiquée. La campagne garde son code 1 ; investigation dans
  `validation/nested-field-replacement-survivor-o2.log`.

Les programmes natifs utilisent clang C11/pthread, O0 ou O2, avertissements
traités comme erreurs et UBSan fatal. Aucun nouveau résultat ASan/TSan.
Les journaux initiaux et intermédiaires sont conservés ; les tests attendus
valides n'ont pas été changés en tests de refus pour contourner les restrictions.
Tous les processus du lot sont terminés. Les suites finales sortent avec le
code 0 ; la campagne de mutations sort avec le code 1 pour la survivante.

Commandes reproductibles :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_nested_field_replacement.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_nested_field_replacement_mutations.py
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_nested_owned_borrows test_nested_detached_references test_public_structure_handles test_async_execution_arguments test_async_field_application test_async_child_field_effects test_async_owned_borrowed_captures test_async_capture_field_contracts test_sync_handle_field_effects test_select_source -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_reference_fields test_stored_field_reborrows test_stored_field_reborrow_model test_mutable_field_completion -v
```

## Limites et travail restant

Le relais `change_outer(value: &mut Outer, target: &Int)` qui emprunte le parent
entier puis appelle change sur son descendant reste refusé. Le contre-exemple
valide est `validation/open-nested-field-wrapper.crust` ; le refus aux deux
étapes est conservé dans `validation/nested-field-wrapper-probe.log`.
Le suivi des projections doit aussi traverser l'analyse des contraintes et les
signatures d'emprunts d'agrégats contenant A<T>. Ce chantier reste ouvert.

Mise à jour : ce relais est traité dans [NESTED_FIELD_WRAPPERS_CYCLE.md](NESTED_FIELD_WRAPPERS_CYCLE.md).
Ce cycle ultérieur détecte aussi la mutation survivante avec une lecture du
descendant modifié suivie d'une affectation à son frère. Les résultats ci-dessus
restent ceux de la campagne originale.

Les graphes de types récursifs, les signatures générales et l'API publique de
remplacement du scheduler ne sont pas généralisés par ce lot. Les tests et le
modèle fini ne prouvent pas la sûreté de toutes les compositions. La mutation
survivante reste une limite explicite de la validation.

Les trois différences sont archivées dans
`validation/nested-field-replacement-*.py.patch` depuis le snapshot préalable
`/tmp/crust-before-nested-field-replacement`. L'objectif global reste actif.
