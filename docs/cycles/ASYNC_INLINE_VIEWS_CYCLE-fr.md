[English](ASYNC_INLINE_VIEWS_CYCLE.md)

# Captures async de sous-structures

## Périmètre et décisions

Raccordement des règles existantes AS2–AS4, ST7–ST14 et ST17–ST18 : une tâche
peut capturer une vue vers une sous-structure durable, sans copier ni déplacer
la cible. Le mode de capture conserve les obligations d'emprunt pendant la
vie de la tâche et de ses résultats empruntés. Aucune règle normative modifiée.

Ce lot porte sur les structures dont les champs terminaux sont déjà représentés
par le backend async : Int, références Int et descendants propriétaires pris
en charge. Les références nominales stockées dans ces structures restent un
chantier distinct ; le refus explicite existant est conservé et testé.

## Implémentation

- Les références de structures traversent la frontière async avec le même
  descripteur `CrustStructureView` pour les objets entiers et intérieurs.
  Les captures, membres de frame, tâches enfants et appels synchrones
  conservent la racine, le décalage, la taille et le layout.
- Les ponts synchrones décrivent une vue symbolique sans déplacement de cible.
  Le chemin vide est une projection identité, et conserve les variantes,
  champs propriétaires et dépendances de nettoyage de sa racine.
- Les copies utilisent le stockage désigné par la vue ; les emprunts de champs
  Int calculent leur adresse depuis ce même stockage. Les projections de
  descendants propriétaires dans un match adaptent leur représentation.
- Les paramètres copiés implicitement sont inférés et propagés dans les
  contrats de stockage. Une vue dans un pool d'un autre type ne peut pas
  utiliser ce pool pour sa copie implicite. Une racine locale ou une destination
  explicite du bon type est nécessaire. La restriction vaut aussi par relais.

## Cas ciblés

`tests/test_async_inline_views.py` : neuf méthodes, neuf programmes admis
exécutés nativement, huit programmes invalides refusés par `verify_program`
et `compile_source`.

1. Lecture de la deuxième sous-structure après yield et lancement sur un worker ;
   drop de racine et écriture concurrente refusés avant lancement.
2. Capture mutable, attente d'une tâche enfant, appel synchrone et mutation
   observée par l'appelant ; lecture concurrente refusée.
3. Même routine appelée avec un objet entier puis une sous-structure.
4. Destruction d'une tâche inactive : corps non exécuté et accès mutable rendu.
5. Retour d'un &mut Int vers un champ de la vue, puis usage après join ;
   destruction de la racine refusée avant cet usage.
6. Réemprunt mutable retourné par un helper synchrone, suspension et copie locale.
7. Vue contenant A<Int> et &Int : mutation du descendant et lecture de la cible ;
   destruction prématurée de la cible refusée.
8. Copie implicite depuis une vue de Pool<Pair> refusée, directement et par
   relais ; copie vers un Pool<Point> explicitement injecté exécutée.

9. Fabrique synchrone créant une tâche depuis un emprunt de structure : copie
   depuis Pool<Point> compatible exécutée, depuis une vue de Pool<Pair> refusée.

## Défauts rencontrés et corrections

La première régression a révélé des accès C `->fields`/`->source` encore écrits
pour Cell*, ainsi que des affectations de pointeurs entiers dans un descripteur.
Ces accès et conversions sont raccordés. Les ponts perdaient aussi les champs
lors d'une projection vide, puis les variantes du porteur canonique : les
contrats de remplacement signalaient les provenances manquantes. Les tests
historiques concernés passent après correction.

Le cas de copie de Point dans Pool<Pair> était accepté après l'introduction
des captures de vues ; il est maintenant refusé statiquement aux deux entrées.
L'exigence est transmise par contrat, sans réanalyse opportuniste du corps à
chaque capture. Les tests distinguent copie locale, pool compatible pour un
objet entier, destination explicite et pool incompatible pour une vue.

Deux erreurs de fixture ont également été corrigées : une accolade de match
supprimée par le montage du snippet, puis une redéclaration du nom `pair`.
Le dernier raccordement de copie conserve la distinction entre représentation
en descripteur et véritable sous-structure : un objet entier dans un pool
compatible reste copiable, y compris à travers une fabrique synchrone de tâche.

Une fixture supplémentaire déclarait une valeur sans usage explicite ; elle
la détruit désormais explicitement. Aucun résultat attendu n'a été affaibli.

## Exécutions

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
Le harness compile en C11 avec pthread, warnings en erreurs et UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`).

| Journal dans validation/ | Résultat |
| --- | --- |
| async-inline-views-o0-first.log | 4 méthodes, 3 échecs de fixture, 0,461 s ; commande shell terminée par tail, code unittest non capturé séparément |
| async-inline-views-o0-second.log | 4 méthodes, 1,741 s, code 0 |
| async-inline-views-regression-first.log | 54 méthodes, 18 échecs/sous-cas, 24,205 s, code 1 |
| async-inline-views-regression-second.log | 54 méthodes, 11 échecs/sous-cas, 28,545 s, code 1 |
| async-inline-views-o0-third.log | 22 méthodes, 2 échecs, 11,111 s, code 1 |
| async-inline-views-o0-fourth.log | 7 méthodes, 3,075 s, code 0 |
| async-inline-views-regression-third.log | 127 méthodes O2, 93,036 s, code 0, avant ajout final de l'exigence de copie |
| async-inline-views-o0-fifth.log | 8 méthodes, 1 échec de fixture, 3,069 s, code 1 |
| async-inline-views-o0-sixth.log | 8 méthodes, 3,426 s, code 0 |
| async-inline-views-final-o2.log | 58 méthodes, 7 échecs/sous-cas et 1 erreur, 31,043 s, code 1 |
| async-inline-views-final-second-o2.log | 58 méthodes, 35,864 s, code 0 |
| async-inline-views-factory-final-o2.log | 32 méthodes, 18,647 s, code 0 |

La passe de 127 méthodes couvre les nouveaux cas, les structures mixtes,
remplacements propriétaires et empruntés async, copies, vues stockées sync,
résultats mixtes sync, captures de structures, champs références et leurs retours,
helpers de structures locales, appels synchrones propriétaires et type features.
La passe finale après l'exigence de copie vise les copies, exigences de stockage,
captures locales, helpers et méthodes directement concernés.

## Limites

- Pas de preuve générale de sûreté, ni couverture de tous les entrelacements.
  La sortie attendue est écrite dans les tests indépendamment du générateur C.
- Pas de nouvelle campagne adversariale, mutation ou génération aléatoire.
  L'audit indépendant prévu avec un autre agent n'est pas exécuté dans ce lot.
- La capture d'un porteur contenant une référence nominale intérieure reste
  refusée explicitement. Les captures de vues ne terminent pas l'ensemble du
  support async des références typées et de leurs résultats.
- Pas d'extension de reset : API toujours retirée du prototype par défaut.
- L'interface publique du scheduler et les arbitrages déjà ouverts demeurent
  ouverts ; ce lot ne les modifie pas. L'objectif global reste en cours.

Snapshot avant modification : `/tmp/crust-before-async-inline-views/`.
Les patches des quatre fichiers Python modifiés sont archivés dans validation/.
