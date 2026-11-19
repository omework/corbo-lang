[English](RECURSIVE_BORROW_RESULTS_CYCLE.md)

# Retours partagés depuis des descendants récursifs

## Règles appliquées

ST13, les règles de provenance B1–B5, de match et AS8–AS12 sont inchangées.
Une référence partagée stockée dans un descendant désigne une cible extérieure.
La référence retournée conserve cette cible, sans dépendance artificielle envers
le porteur. La destruction du porteur est permise après l'appel ; l'écriture ou
la destruction de la cible restent refusées avant le dernier usage du résultat.
Les références mutables ne deviennent pas copiables.

## Implémentation et défauts corrigés

- results.py conserve le chemin des projections A<T> dans un match emprunté,
  puis publie la provenance détachée du champ partagé terminal. Auparavant,
  deux liens de même type aboutissaient à une provenance locale non durable.
- crust.py résout ces chemins sur les descendants symboliques, prépare les
  champs empruntés nécessaires et ignore les variantes prouvées absentes.
  Le filtre des résultats de match admet maintenant un match imbriqué, soumis
  ensuite aux contrôles ordinaires. La liaison d'un champ partagé ne conserve
  plus le prêt temporaire du sujet du match après sortie ; le sujet reste
  réservé pendant le bras. Les champs mutables gardent leur capacité.
- async_lowering.py admet les enums, comme les structures, pour la projection
  d'un résultat d'appel synchrone à partir de son contrat.

Les journaux first à fourth conservent les étapes des refus précédents : cible
locale non durable, filtre de lecture de match, porteur absent du contrat, puis
limitation de la projection async aux structures. fifth termine les deux cas.

## Cas et résultats exécutés

Deux méthodes dans tests/test_recursive_borrow_results.py : deux programmes
valides natifs et quatre invalides testés par verify_program et compile_source.
Le graphe contient deux liens A<Node> suivis d'un champ &Int. Un helper retourne
ce champ, avec une autre cible en secours dans les branches restantes.

- Appel depuis main : destruction du graphe, lecture 7, puis écriture 8 admise.
- Appel depuis un état async : destruction du graphe, yield, lecture 7, puis
  écriture après dernier usage admise.
- Dans chaque cas, écriture avant lecture et drop avant lecture sont refusés.
  Les variantes drop retirent l'usage ultérieur de number : le diagnostic ne
  peut pas être justifié seulement par une seconde utilisation après destruction.

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-borrow-results-fifth-o0.log | 2 méthodes, 1,041 s, succès |
| recursive-borrow-results-final-o0.log | 2 méthodes, 1,077 s, code 0 ; refus de drop ajoutés |
| recursive-borrow-results-regression-o2.log | 81 méthodes, 48,141 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_borrow_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_borrow_results test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_async_owned_borrow_writes test_async_owned_nominal_writes test_mutable_match_function_return test_direct_borrow_returns -v
```

Les harnais async/ciblés compilent C11/pthread, warnings en erreurs, UBSan fatal,
avec le niveau indiqué. Les harnais synchrones historiques de retours directs
et de match mutable compilent en C sans optimisation/sanitizer explicitement
activé dans cette commande ; ils utilisent le profil legacy-reset pour leurs
anciens scénarios. La régression réexécute leurs modèles finis et contrôles de
contrats existants, sans nouvelle campagne adversariale ou de mutations.

## Limites

Couverture du retour partagé &Int depuis ce graphe fini et de son usage dans
un état suspendu. Pas de preuve générale, pas de validation indépendante ajoutée.
Le retour mutable profond et le remplacement de liens récursifs demeurent à
compléter. L'interface publique du scheduler et les autres arbitrages signalés
restent ouverts ; ce lot ne termine pas l'objectif global.

Snapshot : /tmp/crust-before-recursive-borrow-results/.
Diffs : validation/recursive-borrow-results-{crust.py,results.py,async_lowering.py}.patch.
