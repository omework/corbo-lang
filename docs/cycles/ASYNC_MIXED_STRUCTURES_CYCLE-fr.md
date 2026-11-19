[English](ASYNC_MIXED_STRUCTURES_CYCLE.md)

# Structures async à champs possédés et empruntés

## Périmètre et règles

Ce cycle applique ST1/ST6–ST16, B1–B5, D1, T1/T6, P3/P4, AS2/AS8–AS15,
RT6/RT8 et SL1. Aucune sémantique normative n'est modifiée. Une structure
peut posséder des allocations dans ses champs A<T> tout en empruntant d'autres
cibles. Transférer cette structure conserve séparément les obligations de
ses pools et de ses cibles ; détruire la structure détruit ses enfants possédés,
jamais les cibles qu'elle emprunte.

Le lot couvre les champs empruntés directs &Int/&mut Int et les descendants
possédés sans emprunts. Il ne clôt pas le chantier des graphes récursifs mixtes.
PR1 reste inchangé : reset() est retiré du profil normal.

## Contre-exemples et corrections

- `validation/open-mixed-owned-borrowed-capture.crust`, précédemment refusé,
  s'exécute et produit 16. Les familles de layouts autorisées étaient calculées
  séparément dans le backend et l'analyse des effets. `structure_shapes.py`
  partage désormais le calcul des graphes représentables.
- Une fabrique synchrone appelée depuis un état async pouvait restituer une
  tâche dont le contrat mentionnait `allocation_field_parameter`, mais le pont
  rejetait cette source. Il conserve désormais les pools de l'argument possédé,
  descendants compris. Cette couche conserve une union conservative de ces
  sources ; elle ne prétend pas une précision individuelle de tous les champs.
- Un remplacement dans une boucle était refusé lorsque le nouveau porteur
  local traversait une tâche qui le retournait. Le plan de placement suivait
  les créations fraîches, mais pas ces retransmissions. Il suit maintenant les
  paramètres retournés dans les contrats async et les sources de résultat des
  fabriques, jusqu'au constructeur original. L'adresse n'est pas déplacée.

Les refus initiaux sont conservés dans
`validation/mixed-structures-before-storage-fix.log` et
`validation/mixed-structures-expanded-o2.log`. Les tests conservent aussi les
voisins invalides : pools trop courts, emprunts détruits prématurément, copie
de propriétaire et promotion implicite d'une cible créée dans un enfant.

## Preuves exécutées

`tests/test_async_mixed_structures.py` contient treize méthodes finales.

- `validation/mixed-structures-final-count-o0.log` : 13 méthodes en 13,402 s,
  23 exécutions natives, 32 programmes invalides et 64 contrôles de refus
  (verify_program et compile_source).
- La base de `validation/mixed-structures-audited-mutations-o2.log` passe les
  mêmes 13 méthodes à O2 en 13,696 s.
- Harnais natif : Clang C11/pthread, Wall/Wextra/Werror, Wno-unused-function,
  UBSan fatal, O0/O2. Les refus de lancement natif et de soumission sont injectés.

Le modèle indépendant de durabilité croise trois booléens : pool du porteur,
pool du champ possédé, cible empruntée. Les huit dispositions sont exercées
par appel direct et par fabrique. Seule la disposition où les trois survivent
est admise. Un cas supplémentaire garde le pool extérieur mais crée sa cible
dans le bloc enfant : il reste refusé, conformément à l'absence de promotion.

Les essais couvrent aussi les champs mutables, le retour du porteur entier,
le détachement d'une vue après destruction du porteur et de son enfant,
les helpers synchrones, le réemploi de pools de capacité un, les boucles et
remplacements, les tâches inactives, les échecs de lancement, les threads
natifs, les arguments préparés et les branches perdantes de Select.
Une sonde C observe la racine, son enfant possédé et sa cible empruntée à
chaque suspension et après transfert : mêmes adresses et mêmes valeurs.

Deux erreurs de la sonde ont été corrigées sans changement du compilateur :
un transfert descendant `a ->;` manquait, puis la sonde lisait un Int scalaire
avec le lecteur de payload de structure. Les logs initiaux
`mixed-structures-identity-o2.log` et `mixed-structures-identity-final-o2.log`
sont conservés. La sonde corrigée utilise le champ scalaire `Cell.value` et
passe dans les deux suites finales.

## Mutations et audit du test survivant

`tests/run_mixed_structure_mutations.py` injecte neuf fautes dans des copies
temporaires. Toutes sont détectées dans le passage final : refus artificiel
d'un layout mixte, refus d'une source de champ, fuite d'un enfant, destruction
d'une cible empruntée, oubli d'un propriétaire préparé pendant une suspension,
perte du prêt retourné direct ou via fabrique, perte du placement via tâche
directe ou via fabrique.

Les deux pertes de prêt font accepter à tort un programme invalidant sa cible
avant usage ; les tests détectent l'absence d'erreur aux deux étapes. Les
mutations de destruction échouent sur les traces, le réemploi ou les gardes
runtime. Les mutations trop restrictives échouent sur les programmes valides.

L'oubli de propriétaire préparé avait survécu dans les passages
`mixed-structures-final-mutations-o2.log` et
`mixed-structures-complete-mutations-o2.log`. Le point d'injection concernait
le destructeur d'un état suspendu, alors que le test sélectionné exerçait un
retour ordinaire. Un test spécifique suspend maintenant l'évaluation du second
argument, fait perdre cette branche de Select puis réemploie les slots des
pools injectés après son nettoyage. La faute est détectée dans
`mixed-structures-audited-mutations-o2.log`. Aucun taux général de détection
n'est déduit de ces neuf fautes choisies.

## Régressions et chronologie

- `mixed-captures-initial-regression-o0.log` : 46 méthodes réussies avant les
  correctifs de source et de placement de ce cycle.
- `mixed-structures-regression-o2.log` : 161 méthodes réussies en 134,650 s,
  avec le correctif de source, avant celui du placement. Modules : captures
  et retours propriétaires, captures empruntantes, contrats par champ,
  fabriques détachées, résultats locaux propriétaires/empruntés et leurs
  enveloppes, effets de structures, pools de structures et pools empruntants.
- `mixed-structures-placement-regression-o2.log` : 33 méthodes réussies en
  34,414 s après le correctif de placement : boucles, placement parent et
  résultats locaux à descendants possédés.

Les deux sélections O2 demandent explicitement CRUST_SANITIZE=undefined.
Elles se recouvrent et ne sont pas additionnées comme des tests uniques.
Les passages ciblés finaux couvrent les derniers ajouts. Tous les processus
cités sont terminés. Pas de nouvelle validation ASan/TSan ni de preuve formelle.

## Écarts restants

Mise à jour : le [cycle des emprunts descendants](NESTED_OWNED_BORROWS_CYCLE.md)
corrige le refus de capture du graphe ci-dessous et ajoute ses retours entiers.
Les limitations décrites ici sont celles de la fin du présent lot.

`validation/open-nested-owned-borrowed-capture.crust` contient un Outer qui
possède un Inner contenant &Int. Les pools et la cible survivent à l'attente,
mais ce programme est encore refusé aux deux étapes :
`validation/mixed-structures-next-nested-probe.log`. Il faut étendre les chemins
de captures et de résultats aux emprunts des descendants possédés. La présente
restriction ne devient pas une règle normative.

Les signatures async générales, l'API publique de remplacement du scheduler,
le placement général et les deux arbitrages sur les handles lancés restent
ouverts. L'objectif global n'est ni achevé ni bloqué par ce lot.
