[English](STORED_INLINE_VIEWS_CYCLE.md)

# Stockage de références vers des sous-structures

## Périmètre et représentation

Raccordement de ST7, ST10–ST14 et ST17–ST18 aux références stockées dont la cible
est une sous-structure contenue. Aucune modification des règles normatives.
La référence conserve la racine physique et son chemin ; elle ne possède pas
cette racine et ne crée pas un nouveau slot pour la sous-structure.

Le champ C d'une référence nominale contient désormais un `CrustStructureView`
par valeur : racine, décalage, taille et description statique du type. Ce choix
augmente la taille de ces champs, y compris lorsqu'ils ciblent un objet entier.
Les champs &Int et A<T> gardent leur représentation pointeur existante.
Les tailles et les catégories de champs sont partagées entre les générateurs
sync et async. Les écritures d'une référence entière initialisent également
les métadonnées du descripteur ; les lectures sont spécialisées selon les cibles
prouvées. Aucune référence stockée ne pointe vers un descripteur temporaire du
producteur.

Les copies de structures copient le descripteur. La destruction du porteur ne
détruit pas la cible empruntée. Les retours utilisent les contrats existants,
en conservant les chemins intérieurs et les réservations mutables. Le remplacement
retire les anciennes réservations intérieures devenues sans cible. Les contrôles
de cycles comparent la racine physique d'une vue, et pas seulement son identifiant
de projection.

## Cas ciblés

`tests/test_stored_inline_views.py` : neuf méthodes, huit programmes admis
exécutés, cinq programmes invalides refusés aux deux entrées. Un sixième refus
est une limite d'implémentation explicite : la capture async d'un porteur
contenant une vue reste à raccorder et n'est pas présentée comme interdite par
le langage.

- Référence partagée copiée dans une autre structure, champs Int voisins préservés,
  destruction des porteurs autorisée, destruction précoce de la racine refusée.
- Construction et retour du porteur, extraction de sa référence par deux relais,
  puis usage après la fin du producteur.
- Réemprunt mutable stocké et retourné par fonction ; mutation et lecture de la
  bonne sous-structure, accès concurrents et drop précoce du porteur refusés.
- Remplacement d'une référence entière par une vue, puis inversement ; ancienne
  racine libérable après son dernier usage.
- Écriture du descripteur à travers une vue sur le porteur lui-même.
- Projections d'enum par match emprunté et consommant.
- Copie dans un pool et conservation du descripteur après réutilisation du slot
  de son porteur initial.
- Référence d'une racine vers sa propre sous-structure refusée par l'interdiction
  déjà retenue des cycles d'allocations empruntées.

## Exécutions

Clang C11/pthread, avertissements comme erreurs, UBSan fatal. Les programmes
admis passent d'abord par `verify_program`, puis `compile_source`, puis exécutent
le C généré avec un résultat attendu. Les refus passent aux deux entrées.

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Premier O0 | 5 méthodes, 4 échecs, 0,964 s, code 1 | `stored-inline-views-o0-first.log` |
| Deuxième O0 | 5 méthodes, 1 échec, 2,037 s, code 1 | `stored-inline-views-o0-second.log` |
| Troisième O0 | 5 méthodes, 2,299 s, code 0 | `stored-inline-views-o0-third.log` |
| Quatrième O0 | 8 méthodes, 4 échecs de sous-cas, 2,757 s, code 1 | `stored-inline-views-o0-fourth.log` |
| Cinquième O0 | 8 méthodes, 2 échecs de sous-cas, 2,728 s, code 1 | `stored-inline-views-o0-fifth.log` |
| Sixième O0 | 8 méthodes, 1 échec, 3,526 s, code 1 | `stored-inline-views-o0-sixth.log` |
| Septième O0 | 8 méthodes, 3,891 s, code 0 | `stored-inline-views-o0-seventh.log` |
| Final O0 | 9 méthodes, 3,625 s, code 0 | `stored-inline-views-o0-final.log` |
| Régression O2 avant normalisation des cycles | 90 méthodes, 58,614 s, code 0 | `stored-inline-views-regression-o2.log` |
| Références typées O2 avant normalisation des cycles | 12 méthodes, 10,671 s, code 0 | `stored-inline-views-typed-o2.log` |
| Final O2 après normalisation des cycles | 33 méthodes, 17,997 s, code 0 | `stored-inline-views-final-o2.log` |

Les premiers échecs ont révélé la perte du chemin intérieur dans le résultat
construit, les anciennes réservations conservées après remplacement et
l'ascendance manquante du réemprunt mutable retourné. Une déclaration de type
locale incorrecte a été déplacée au niveau programme dans la fixture.
Les passages suivants corrigeaient les fixtures d'enums : constructeur avec
pool, notation existante `match (->c)` et lecture du champ dans une liaison
avant print, compatible avec la validation actuelle des bras. Le test de limite
async vérifie le diagnostic d'implémentation rencontré, sans changer l'attente
de refus ni prétendre que ce cas est maintenant implémenté.

La régression large comprend les modules de vues, de constructions contenues,
de réemprunts stockés, de structures mixtes async et de remplacements propriétaires.
Les douze tests historiques de références typées sont listés intégralement dans
leur journal ; ceux utilisant reset activent le profil de compatibilité.
La normalisation finale des cycles est suivie d'une validation O2 ciblée sur
les vues stockées, les vues à champs propriétaires, l'ABI des vues et les douze
cas historiques typés.

## Limites

Les captures et résultats async contenant ces vues restent ouverts. Les signatures
de capture typée non raccordées sont toujours refusées ; le contrôle de création
des tâches refuse aussi les graphes contenant des vues, au lieu de transmettre
leur racine comme un pointeur de cible ordinaire. Les résultats mélangeant
références entières et intérieures restent à raccorder.

Pas de nouvelle campagne de mutations ou de génération adversariale ; pas de
nouveau modèle indépendant. La suite reprend des sondes C existantes de l'ABI.
ASan et un second compilateur C n'ont pas été exécutés. Ces résultats ne prouvent
pas la sûreté de toutes les compositions.

Diffs : `validation/stored-inline-views-*.py.patch`, comparés à la copie antérieure
`/tmp/crust-before-stored-inline-views/`.
