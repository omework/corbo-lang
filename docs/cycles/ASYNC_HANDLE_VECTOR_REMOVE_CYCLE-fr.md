[English](ASYNC_HANDLE_VECTOR_REMOVE_CYCLE.md)

# Extraction de handles de vecteurs dans les états async

## Périmètre

Application des règles H1–H2, VE1–VE3, B1–B5, AS8–AS12 et U1, sans changement
normatif. `remove` transfère un A<Int>, conserve l'adresse et la source de sa
cible, décale les cases restantes et transmet le nettoyage au receveur.
L'extraction exige `<-`, ou le transfert déjà explicite de `drop(-> ...)`.

Le lowering matérialise le résultat en Cell*, réserve le vecteur pendant
l'évaluation de l'indice, puis rattache le résultat aux sources conservées.
Les retours et contrats de fabriques distinguent les sources des éléments de
celle du vecteur. Les relais async reconstituent un candidat d'élément à partir
de cette provenance. Le résultat peut survivre au pool du vecteur, jamais à
celui de sa cible. Le runtime de remove reste inchangé.

Le pont synchrone conserve les sources symboliques des éléments au lieu de les
remplacer par le graphe de champs, vide pour ce type. Le retour direct sync
conserve aussi le marqueur explicite d'extraction. La résolution du résultat
consommé par drop reconnaît désormais remove, sans ajouter de transfert aux
appels ordinaires.

## Cas exécutés

Huit méthodes dans tests/test_async_handle_vector_remove.py : treize exécutions
natives, dont un arrêt contrôlé hors bornes, et sept programmes invalides
vérifiés avec verify_program et compile_source.

- Extraction locale consignée, destruction unique de 7 et réemploi du slot avec 8.
- Flèche absente, vecteur partagé et usage après drop refusés.
- Retour direct, fabrique synchrone et relais async attendu.
- Trois éléments issus de deux pools : extraction du milieu, ordre 10/30
  conservé, résultat 20 encore utilisable après destruction du vecteur,
  nettoyage unique et réemploi des trois slots.
- Emprunt terminé avant extraction admis ; dernier usage après extraction refusé.
- Indice calculé par tâche avec suspension ; indice hors bornes arrêté.
- Helper synchrone et consommation directe par drop.
- Vecteur transféré à la tâche : résultat sortant du bloc de son pool admis,
  directement et via fabrique ; pool de l'élément trop court refusé.
- Remplacement d'un receveur : ancienne allocation détruite une fois, nouvelle
  allocation nettoyée en fin de tâche ; ancien contenu encore emprunté refusé.

## Journaux et corrections

Tous les journaux sont dans validation/.

| Journal | Résultat |
| --- | --- |
| async-handle-vector-remove-first-o0.log | Harnais incomplet et transfert de bloc manquant dans le test corrigés ; raccords de fabrique et retour sync manquants |
| async-handle-vector-remove-second-o0.log | Relais perdant la provenance ; pont sync effaçant les sources des éléments |
| async-handle-vector-remove-third-o0.log | Les chemins précédents passent ; drop direct ne reconnaît pas son transfert |
| async-handle-vector-remove-fourth-o0.log | Six méthodes, code 0 |
| async-handle-vector-remove-fifth-o0.log | Huit méthodes, 5,864 s, code 0 |
| async-handle-vector-remove-sync-regression.log | Cinq méthodes, 6,278 s, code 0 |
| async-handle-vector-remove-regression-o2.log | 77 méthodes, 60,691 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_remove -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_remove test_async_handle_vector_push test_async_handle_vector_captures test_async_handle_vector_borrows test_async_handle_vector_borrow_returns test_async_vector_remove test_async_result_storage test_async_owned_struct_returns test_factory_owned_effects -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_handle_vector_remove_preserves_identity_and_frees_origin_after_drop test_foundation_rules.FoundationTests.test_handle_vector_remove_dynamic_index_inside_function test_foundation_rules.FoundationTests.test_handle_vector_extraction_returns_injected_handle test_foundation_rules.FoundationTests.test_handle_vector_extract_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_handle_vector_extraction_infers_drop_pool_through_a_call -v
```

C11/pthread, avertissements en erreurs, UBSan fatal. Les cinq méthodes Foundation
utilisent le harnais historique O2/UBSan avec legacy-reset ; reset reste exclu
du prototype normal. Les oracles portent sur les valeurs, refus, destructions
et réemplois observés. Aucun nouveau modèle indépendant ni campagne de
mutations ; l'audit croisé approfondi reste prévu séparément. La régression
réexécute notamment le modèle de liste existant pour remove Int/u8 (graines 81
et 183, 32 opérations chacune), sans l'étendre aux handles.

## Limites

Le contrat async conserve l'union des pools possibles des éléments ; il ne
promet pas une provenance précise par index dans tous les relais. Cette
approximation peut refuser des programmes valides. Les scénarios ci-dessus ne
prouvent ni la sûreté générale ni toutes les combinaisons de règles.
Pop, replace, try_push et les constructions locales/retours de vecteurs dans les
états async restent des travaux distincts. Les arbitrages de scheduler public,
construction des mutex et captures de handles inactifs restent ouverts.

Snapshot : /tmp/crust-before-async-handle-vector-remove/.
Diffs : validation/async-handle-vector-remove-{async_lowering.py,async_result_storage.py,crust.py,results.py,array_syntax.py}.patch.
