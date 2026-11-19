[English](ASYNC_STORED_VIEWS_CYCLE.md)

# Références typées stockées et captures async

## Périmètre

Implémentation des règles déjà retenues AS2–AS4, AS11–AS12 et ST7–ST18 pour
les structures contenant des références vers d'autres structures, notamment
vers leurs sous-structures. Pas de nouvelle sémantique ni promotion implicite.

La fermeture des layouts async inclut les références nominales dont la cible
est représentée. Une référence utilise le descripteur de vue existant ; elle
ne devient pas une allocation propriétaire. Les cycles de types qui ne peuvent
pas être fermés par ce calcul restent hors du périmètre représenté.

## Modifications

- Lecture et réemprunt mutable d'un champ &T/&mut T avec chargement du
  descripteur complet, y compris après yield et dans une tâche enfant.
- Extension du suivi des champs partagés/exclusifs et des contrats de
  remplacement au type référencé, au lieu de les limiter à Int.
- Ponts synchrones : reconstruction symbolique du graphe des références
  typées et conservation des racines, layouts et capacités.
- Construction et copie de porteurs dans une tâche ; capture par transfert
  et retour d'un porteur conservant sa cible intérieure.
- Au join, conservation des réservations par identité de la racine canonique,
  et non par égalité entre identités d'une vue et de son objet extérieur.

Le test qui documentait le refus provisoire des captures de vues stockées
vérifie désormais leur création puis destruction inactive. Il s'agissait d'une
limite d'implémentation, pas d'une interdiction normative.

## Tests ciblés

`tests/test_async_stored_views.py` : huit méthodes, neuf programmes admis
exécutés et neuf programmes invalides refusés aux deux entrées, dans la version
finale de la suite.

- Référence partagée stockée : lecture après suspension, destruction du porteur
  ou de la racine et mutation concurrente refusées.
- Référence mutable stockée : réemprunt transmis à une tâche enfant, mutation
  visible après join, écriture concurrente refusée.
- Chaîne Link → View → Point, avec copie préalable du porteur partagé.
- Extraction partagée puis mutable par un helper synchrone appelé dans la tâche.
- Remplacement direct ou via contrat : nouvelles cibles conservées après join.
  L'ancien et le nouveau référent restent protégés lorsque le lancement peut
  échouer et donc laisser le champ inchangé.
- Capture propriétaire de View puis restitution au join : la référence extraite
  reste liée à la sous-structure après destruction du porteur. Une mutation de
  la cible avant son dernier usage est refusée.
- Construction et copie locale de View dans une tâche ; la référence partagée
  extraite survit à la destruction des deux porteurs.

La suite `test_stored_inline_views` conserve les cas synchrones et exerce
également la destruction inactive nouvellement admise.

## Défauts et corrections

Le passage d'un champ mutable par helper utilisait une origine `field_parameter`
que le générateur async ne projetait pas encore pour ce résultat. La projection
utilise maintenant le même contrat de champ que la lecture directe. Les ponts
C déclarent également explicitement l'usage des descripteurs nécessaires au
modèle statique, même lorsqu'ils ne sont pas lus par le corps C spécialisé.

Le retour propriétaire révélait un défaut réel : une écriture sur `pair.b.x`
était acceptée alors qu'une référence partagée issue du porteur retourné était
encore utilisée. Le descripteur intérieur était présent, mais la sélection des
parents conservait seulement les identités exactes. La comparaison par racine
canonique conserve maintenant la réservation de `pair.b`. Le test refusé passe
par verify_program et compile_source.

Les premières fixtures de remplacement utilisaient une affectation de référence
sans réemprunt explicite ; elles utilisent maintenant `&*p`. Elles détruisaient
également l'ancien référent avant le dernier usage du champ après join : ce cas
est effectivement invalide si le lancement échoue. Le programme admis conserve
l'ancienne cible jusque-là, et le programme initial reste un test refusé.
Le premier test de drop dans un bras échouait d'abord sur le transfert parent →
enfant requis ; une mutation de la cible dans ce bras teste directement le
conflit d'emprunt voulu, sans cette autre interdiction préalable.

## Exécutions

Commandes : `PYTHONPATH=.:tests CRUST_TEST_OPT=-O0|-O2 python3 -m unittest ... -v`.
Harness C11, pthread, warnings en erreurs, UBSan fatal. Les valeurs attendues
sont écrites dans les tests indépendamment du générateur C.

| Journal dans validation/ | Résultat |
| --- | --- |
| async-stored-views-o0-first.log | 3 méthodes, 1,206 s, code 0 |
| async-stored-views-o0-second.log | 14 méthodes, 2 échecs, 4,187 s, code 1 |
| async-stored-views-o0-third.log | 14 méthodes, 4,879 s, code 0 |
| async-stored-views-o0-fourth.log | 6 méthodes, 2 échecs/sous-cas, 1,876 s, code 1 |
| async-stored-views-o0-fifth.log | 6 méthodes, 2 échecs/sous-cas, 1,795 s, code 1 |
| async-stored-views-o0-sixth.log | 6 méthodes, 2,517 s, code 0 |
| async-stored-views-o0-seventh.log | 8 méthodes, 2 échecs de diagnostic attendu, 3,348 s, code 1 |
| async-stored-views-o0-eighth.log | 17 méthodes, 2 refus manquants, 6,355 s, code 1 |
| async-stored-views-o0-ninth.log | 17 méthodes, 6,346 s, code 0, avant ajout des deux refus de destruction de l'ancien référent |
| async-stored-views-regression-o2.log | 118 méthodes O2, 74,459 s, code 0 |

La régression liée couvre les vues stockées, captures directes de vues,
références Int stockées et leurs retours, structures mixtes, remplacements
propriétaires/empruntés, copies, helpers locaux, appels synchrones propriétaires
et vues typées synchrones.

## Limites et suite

- Pas de preuve générale, ni examen de tous les entrelacements ou graphes.
- Pas de nouvelle campagne de mutations, génération ou audit adversarial.
- Les retours async directs de références nominales, les matchs de variantes
  contenant ces références et certaines projections imbriquées restent à
  raccorder complètement. Ce rapport n'en affirme pas la validation.
- Les types récursifs et les combinaisons de graphes non représentées restent
  distincts de la fermeture finie exercée ici.
- Pas de changement à la suppression de reset par défaut, à l'interface publique
  du scheduler laissée ouverte ou aux autres arbitrages reportés.
- L'objectif global n'est pas terminé.

Snapshot : `/tmp/crust-before-async-stored-views/`. Patches archivés dans
validation/ pour les trois modules modifiés et l'ancien test de limite remplacé.
