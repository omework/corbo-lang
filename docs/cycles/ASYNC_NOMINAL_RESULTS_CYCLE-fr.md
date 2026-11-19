[English](ASYNC_NOMINAL_RESULTS_CYCLE.md)

# Retours async directs de références nominales

## Règles et périmètre

Raccordement de AS8–AS12 et ST7–ST14 : une tâche peut restituer &T ou &mut T
vers une structure durable. Le résultat conserve ses provenances et capacités ;
le stockage de la cible n'est pas déplacé. Une référence vers une variable
locale détruite avec l'état reste refusée. Aucune règle normative modifiée.

## Implémentation

- Les retours async de références nominales utilisent CrustStructureView,
  déjà employé pour leurs captures. La copie du résultat précède la libération
  du slot de l'état, via les opérations existantes take/join_into.
- CrustJoinResult possède des champs de descripteur partagé et mutable.
  Le type du descripteur appartient aux déclarations communes au runtime
  autonome et au programme C complet ; ses pointeurs sont déclarés en avant.
- Les résultats d'await de tâche et de handle conservent leur type nominal
  dans les liaisons, branches et matchs. Le générateur synchrone extrait
  soit le descripteur intérieur, soit sa racine si toutes les cibles sont entières.
- L'inférence des résultats empruntés et leur projection chez l'appelant
  couvrent les références nominales, les champs stockés et les sous-structures
  contenues. Une capture déjà projetée n'applique pas deux fois son chemin.
- Les signatures publiques `runtime::Handle<&T>` et `runtime::Handle<&mut T>`
  reconnaissent les structures nominales ; leurs contrats conservent le type
  du résultat et refusent une annotation de mutabilité incompatible.
- Les chemins nominaux des champs contenus sont transmis au backend async.
  Une projection utilise les décalages et tailles du layout, et conserve les
  réservations du sous-arbre. Les métadonnées de layout survivent à la tâche.

## Cas ciblés

Les onze méthodes de `tests/test_async_nominal_results.py` couvrent douze
programmes admis exécutés et huit programmes invalides refusés par les deux
entrées `verify_program` et `compile_source`.

- Join d'une référence partagée : objet entier et sous-structure.
- Join d'une référence mutable : mutation visible chez l'appelant et accès
  concurrent à la cible refusé avant le dernier usage.
- Relais mutable par await avec suspension après réception.
- Retour d'une référence stockée depuis un porteur transféré ; la destruction
  du porteur ne détruit pas la cible, dont la réservation reste effective.
- Retour d'une référence mutable stockée dans un porteur emprunté.
- Attente d'un handle dans une tâche, liaison du résultat et match de son Ok.
- Retour conditionnel mélangeant cible entière et intérieure : les deux
  branches exécutées, sans changement d'adresse du stockage par l'opération.
- Retour de &mut p.b depuis un paramètre &mut Pair, avec protection de la cible.
- Deux refus de retour de référence vers une structure locale de l'état,
  entière ou intérieure.
- Fabrique synchrone de tâche et Select dont le résultat est une référence
  nominale ; nettoyage explicite du Select après utilisation.

- Handle public passé à une fonction synchrone : résultat nominal consommé
  puis cible réutilisable ; annotation mutable incompatible refusée.

## Exécutions

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
Compilation native C11/pthread avec warnings en erreurs et UBSan fatal.
Les sorties attendues sont écrites dans les tests, indépendamment du C généré.

| Journal dans validation/ | Résultat |
| --- | --- |
| async-nominal-results-o0-first.log | 3 méthodes, 1,765 s, code 0 |
| async-nominal-results-o0-second.log | Réexécution des 3 premières méthodes, code 0 ; l'édition précédente avait échoué avant toute modification Python |
| async-nominal-results-o0-third.log | 7 méthodes, 4,259 s, code 0 |
| async-nominal-results-o0-fourth.log | 9 méthodes, 4,640 s, code 0 |
| async-nominal-results-o0-fifth.log | 10 méthodes, 4,843 s, code 0 |
| async-nominal-results-regression-o2.log | 116 méthodes, 96,074 s, code 0 |
| async-nominal-results-handles-o2.log | Après raccordement du type public : 42 méthodes, 48,479 s, code 0 |

L'échec de l'outil d'édition était une erreur de guillemets dans un script Python
embarquant un snippet ; le script n'a appliqué aucun changement. L'édition a
ensuite été appliquée séparément, puis les nouveaux tests réellement exécutés.

La régression couvre les retours Int/u8, tableaux et vecteurs existants,
les références typées stockées, les vues directes, les porteurs synchrones,
les appels synchrones propriétaires, Select et le runtime interne des vues.
Cinq tests autonomes supplémentaires exercent la restitution du résultat avant
libération, la réutilisation concurrente des slots, le runner multithread,
la frontière scheduler et l'échec de création du thread.

## Limites

Ces tests ne prouvent ni toutes les combinaisons de graphes, ni tous les
entrelacements. Pas de nouvelle campagne de mutations ni d'audit adversarial.
Les matchs d'enums à champs références nominales et les graphes récursifs
restent des chantiers distincts. Le présent lot ne modifie ni reset retiré
par défaut, ni les arbitrages publics du scheduler encore ouverts.
L'objectif global reste en cours.

Snapshot : `/tmp/crust-before-async-nominal-results/` ; patches archivés dans
validation/ à la fin du lot.
