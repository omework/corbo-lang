[English](ASYNC_COLLECTION_CREATION_CYCLE.md)

# Cycle — création directe de collections dans les états

Suivi : le raccordement des pools locaux aux états est décrit dans
[le cycle suivant](ASYNC_LOCAL_POOLS_CYCLE.md), avec son statut de validation.

Suite du [cycle des pools injectés](ASYNC_POOL_INJECTION_CYCLE.md).
Aucune règle normative modifiée. Références : A1–A4/A6, B1–B5, V4/V5,
T6/T11, U1, L1/L6, H1, VE1, TX9/TX10/TX21, G9/G12, AS2/AS8–AS13 et RT8.
Les sept brouillons restent partiellement implémentés.

## Raccordements

`p.new()` construit maintenant directement String, Vector<Int> ou Vector<u8>
dans un corps async ou natif qui reçoit le pool correspondant. Le type vient
du pool ; la construction vide conserve l’invariant UTF-8. Un argument Int
ne transforme pas une construction de String/Vector en création d’Int.
Les constructeurs du runtime existant sont réutilisés, sans modification de
leur politique de croissance. Sans annotation applicable, la limite transmise
reste zéro, sélectionnant la politique existante sans région annotée.

Le résultat garde le type de collection, son adresse et sa provenance à
travers suspension, tâche enfant, retour et remplacement. Le suivi des
origines reconnaît aussi le wrapper de transfert d’une création directe :
un second pool non retourné n’est pas retenu sans raison. Le pool réellement
utilisé doit toujours survivre au résultat.

Les tests de construction ont révélé un manque voisin : `&vector[i]` et
`&mut vector[i]` n’étaient pas raccordés aux états pour Int/u8. Les projections
utilisent maintenant le contrôle d’indice du runtime et réservent la collection
pendant l’évaluation de l’indice, même suspendue. Les prêts protègent la
collection pendant leur dernier usage ou celui d’une tâche enfant. Le contrôle
reste conservateur au niveau de la collection ; aucune preuve générale de
disjonction de cases dynamiques n’est ajoutée.

## Contre-exemples et corrections de validation

Le programme [minimal](../../validation/open-async-collection-new.crb) était
refusé avec « création directe dans un état exige un Pool<Int> injecté ».
Le [diagnostic initial](../../validation/async-collection-new-before.log), le
[C final](../../validation/async-collection-new.c) et la
[trace native](../../validation/async-collection-new-artifact.log) sont conservés.

Le premier passage a trouvé le manque des emprunts directs de cases et une
erreur de fixture : `pool` avait été utilisé comme nom de variable alors que
le parseur le reconnaît comme constructeur. Le passage étendu a ensuite
refusé à raison une réception mutable sans `let mut`. Les fixtures ont été
corrigées. Des variantes négatives contenaient aussi un second drop final ;
ce refus parasite a été retiré avant la validation finale pour que le scénario
porte sur le conflit d’emprunt recherché. Les journaux initiaux restent en échec.

## Exécutions

`tests/test_async_collection_new.py` : 14 méthodes, 34 exécutions normales,
sept arrêts runtime diagnostiqués attendus et 64 vérifications négatives.
Clang C11 pthread, O0/O2, warnings bloquants et UBSan fatal. Les sept arrêts
portent sur trois épuisements de pools avant remplacement et quatre indices
hors limites avant exposition du pointeur. EAGAIN est également injecté dans
trois exécutions normales pour tester l’erreur de lancement et le réemploi.

- [O0 final](../../validation/async-collection-new-final-o0.log) : 14 méthodes,
  13,932 s, OK.
- [Baseline O2 et mutations](../../validation/async-collection-new-mutations-o2.log) :
  14 méthodes, 25,113 s, OK avant injection.
- L’artefact C minimal a aussi été compilé et exécuté séparément à O2 avec
  UBSan fatal ; il affiche `été` et détruit sa collection une fois.
- [Interactions O2](../../validation/async-collection-new-interactions-o2.log) :
  97 méthodes, 69,168 s, OK, incluant opérations de vecteurs, push_new,
  remove, retours empruntés, boucles, emprunts u8 et exigences de pools.
- [Régression native/runtime O2](../../validation/async-collection-new-native-o2.log) :
  177 méthodes, 154,100 s, OK. Cette passe inclut les 14 méthodes nouvelles
  et le module des pools injectés. Elle recouvre partiellement la sélection
  d’interactions ; leurs comptes ne représentent pas des tests tous distincts.
- [Mutations des pools rejouées](../../validation/async-collection-new-pool-mutations-o2.log) :
  baseline de 19 méthodes, 11,525 s, OK ; les sept fautes du lot précédent
  restent détectées. L’ancre de la mutation de type est adaptée au nouveau
  contrôle ; les attentes des tests sont inchangées.

Commandes reproductibles depuis la racine :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_collection_new -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_collection_new_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_pool_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_vector_operations test_async_vector_push_new test_async_vector_remove test_async_loop_references test_async_reference_returns test_sync_byte_borrows test_pool_requirements -v
```

Les oracles comparent les valeurs attendues, les adresses de descripteurs,
les nombres de destructions et le réemploi de pools bornés. Les régressions
des vecteurs rejouent leurs modèles indépendants de listes ; aucun modèle
général du vérificateur ou des ordonnancements n’est ajouté dans ce lot.

Six fautes isolées sont détectées avec les tests inchangés : effacement du
type de collection, perte de provenance du retour direct, omission de
nettoyage, mauvais indice de pointeur, réservation absente pendant l’indice,
emprunt mutable permis sur une liaison immutable. Les tests détectent des
acceptations et des refus incorrects, ainsi que des erreurs d’exécution.
Ce résultat ne constitue pas un taux général de détection.

## Limites et suite

Les blocs async annotés, les pools créés localement dans les états et les
autres types de collections/pools restent ouverts. Le cas
`validation/open-native-async-local-pool.crust` est revérifié et son refus
actuel conservé dans `validation/async-collection-new-next-local-pool.log`.
La limite des signatures générales et des captures de structures demeure.
Aucun nouveau résultat ASan/TSan, second compilateur C ou preuve formelle.
Les passages UBSan propres ne prouvent pas toutes les interleavings.

Les cinq fichiers Python modifiés ou ajoutés passent l’analyse syntaxique.
Les liens locaux du rapport ont été contrôlés. Le
[diff du lowering](../../validation/async-collection-new-implementation.patch)
conserve la comparaison avec le snapshot antérieur au lot.
