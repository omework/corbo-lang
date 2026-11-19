[English](ASYNC_HANDLE_VECTOR_BORROWS_CYCLE.md)

# Emprunts nommés des cibles de Vector<A<Int>> dans async

## Règles et implémentation

Application de H1–H2, VE1/VE4, B1–B5 et AS9 : &*values[i] emprunte
le contenu Int de l'allocation désignée par la case. &mut *values[i] exige
un accès mutable. Une suspension ne relâche pas la réservation ; celle-ci
cesse au dernier usage, en tenant compte des réemprunts transmis aux enfants.
Aucune règle normative modifiée.

Le lowering reconnaît ces expressions comme références Int et produit un
pointeur vers Cell.value après contrôle de l'indice. Il utilise le suivi
existant des prêts de vecteurs, de leur dernière utilisation et des descendants.
Le pointeur désigne le contenu alloué, pas la case contenant son handle.
Le vecteur reste réservé afin de conserver la cible en vie.

## Cas et exécutions

Cinq méthodes dans tests/test_async_handle_vector_borrows.py : six exécutions
natives dont une terminaison contrôlée hors bornes ; sept programmes invalides
vérifiés par verify_program et compile_source.

- Fixture historique : référence partagée conservée pendant yield, résultat 7,
  destruction du vecteur et réemploi du pool de capacité un avec 8.
- Mutation via référence partagée et annotation Int sur un emprunt refusées.
- Référence mutable, yield, écriture 9, puis écriture directe 10 après dernier
  usage : résultat 10/8 et destruction unique du contenu 10. Accès direct
  pendant l'emprunt, usage ultérieur de la référence et capture non mutable refusés.
- Réemprunt vers un enfant attendu puis reprise de la référence : 10/8.
  Utiliser le parent pendant que l'enfant le réserve est refusé.
- Vecteur transféré à la tâche : drop après dernière lecture admis, drop avant
  lecture refusé ; résultat copié 7 puis réemploi 8.
- Indice fourni par un enfant suspendu : lecture correcte ou arrêt contrôlé
  hors bornes avant lecture de la cible.

Journaux dans validation/ :

| Journal | Résultat |
| --- | --- |
| async-handle-vector-borrows-first-o0.log | Cinq méthodes, 2,971 s ; l'oracle d'annotation employait une syntaxe &mut Int non parsée dans cette position. Remplacé par l'annotation Int, qui doit être refusée par le contrôle de type. Aucun défaut runtime observé. |
| async-handle-vector-borrows-second-o0.log | Cinq méthodes, 2,726 s, code 0 |
| async-handle-vector-borrows-regression-o2.log | 41 méthodes, 35,948 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_borrows -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_borrows test_async_handle_vector_access test_async_handle_vector_captures test_async_vector_push_new test_async_local_references -v
```

C11/pthread, warnings en erreurs, UBSan fatal. Les oracles portent sur les
valeurs, diagnostics, destructions et réemploi ; les modèles déjà présents dans
les suites de régression restent inchangés. Pas de nouvelle campagne de mutations
ni d'audit adversarial approfondi. Ces exécutions ne prouvent pas la sûreté générale.

## Limites et suite

Le prêt local utilise la réservation existante du vecteur entier. Ce lot ne
prouve pas toutes les combinaisons d'indices disjoints ou inconnus.
Les retours d'emprunts depuis ces vecteurs restent à raccorder : reproduction
validation/open-async-handle-vector-borrow-return.crust et .log, refus aux deux
entrées malgré un vecteur extérieur durable. Les insertions/extractions, les
constructions locales et les retours propriétaires restent aussi à compléter.
Les arbitrages publics scheduler/mutex déjà ouverts ne sont pas clôturés.

Snapshot : /tmp/crust-before-async-handle-vector-borrows/.
Diff : validation/async-handle-vector-borrows-async_lowering.py.patch.
La fixture open-async-owned-vector-borrow.crust est désormais exécutée ; son
ancien journal de refus demeure une preuve historique.
