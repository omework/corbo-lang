[English](NESTED_DETACHED_REFERENCES_CYCLE.md)

# Références détachées des descendants possédés

## Règles et portée

Ce cycle applique ST12–ST15, H1/H2, B1–B5, D1, T1/T6,
AS2/AS8–AS15, RT6/RT8 et SL1. Aucune règle normative n'est modifiée.
Un retour partagé depuis Outer → A<Inner> → &Int conserve la cible
extérieure, sans retenir artificiellement le stockage des porteurs détruits.
L'accès au contenu d'un enfant reste explicite : `read(&*value.inner)`.
Une référence vers un Int stocké dans le porteur ne peut pas lui survivre ;
une référence mutable n'est pas copiée pour obtenir ce détachement.

## Défauts corrigés

La fixture `validation/open-nested-detached-reference.crust` était refusée
comme retour non durable. Les projections symboliques conservent maintenant
le type de l'enfant, son chemin propriétaire et les références de ses champs.
Les fabriques de tâches et de handles composent les origines détachées.

Le premier raccordement permettait néanmoins un drop prématuré après await :
le backend ne cherchait le champ retourné que dans les membres directs.
`nested-detached-first-tests-o0.log` conserve ces acceptations invalides aux
deux étapes. Les cas minimaux sont `open-nested-detached-target-dropped.crust`
et `open-nested-detached-target-too-short.crust`. La sélection du prêt retourné
par chemin descendant corrige ces cas ; ils ne sont pas exécutés comme du C
supposé sûr.

Trois autres défauts faisaient refuser des programmes valides :

- La projection d'un contrat confondait le séparateur propriétaire `/` avec
  une partie du nom de champ. La normalisation utilise maintenant le même
  chemin que les métadonnées de stockage.
- La traversée concrète d'un contrat supposait que chaque intermédiaire était
  un emprunt. Elle suit aussi les arêtes possédées, en vérifiant la disponibilité
  de chaque enfant, puis conserve l'ascendance du champ final.
- Le pont C d'un paramètre de structure empruntée décrivait ses références
  directes mais pas ses enfants A<T>. Il réutilise la description récursive
  du graphe vivant, sans acquérir la responsabilité de le détruire.

Les journaux `nested-detached-projection-fix-o2.log` et
`nested-detached-owned-traversal-o2.log` conservent les refus intermédiaires.
Les patches sont `validation/nested-detached-*.py.patch`, par rapport à
`/tmp/crust-before-nested-detached`.

### Contre-exemple trouvé après la première clôture

Le premier bilan de treize méthodes couvrait le handle public depuis un appelant
synchrone. Son utilisation depuis un état async révèle une perte supplémentaire
du prêt après await. Les tests acceptés passaient, mais le voisin qui détruit
la cible avant de lire le résultat était accepté aux deux étapes. Un auxiliaire
synchrone consommant directement Outer pour rendre &Int avait le même défaut.

Les journaux `nested-detached-public-async-unshadowed-o2.log` et
`nested-detached-sync-owned-probe-o2.log` conservent ces échecs. Les fixtures
minimales sont `open-nested-detached-public-handle-target-dropped.crust` et
`open-nested-detached-sync-target-dropped.crust`. Aucun C invalide de ces
fixtures n'est exécuté. L'essai public initial dans
`nested-detached-public-async-o2.log` utilisait le nom r pour un enfant puis
pour la liaison du match : le backend refusait ce masquage avant le contrôle
visé. Le test final nomme distinctement la charge du match.

La cause était une double projection : les arguments propriétaires fournissent
déjà les cibles de leurs champs. Appliquer de nouveau le chemin du porteur sur
ces cibles inventait un champ dans l'Int extérieur et perdait la réservation.
`projected_argument_loans` réutilise maintenant la cible sélectionnée pour un
champ partagé détaché, dans les résultats directs comme dans les handles.
Les paramètres empruntés continuent de projeter depuis leur porteur.
Le lot a été rouvert ; les preuves antérieures ne sont pas présentées comme
validation du correctif final.

## Vérifications exécutées

`tests/test_nested_detached_references.py` comporte quatorze méthodes.
Le passage O0 antérieur au complément de projection est
`validation/nested-detached-final-count-o0.log` :
13 méthodes en 21,273 s, 20 exécutions natives, 25 programmes invalides et
50 contrôles de refus, une vérification et une compilation pour chaque cas.
À O2, les douze premières méthodes passent en 9,670 s dans
`nested-detached-interactions-o2.log`, puis l'ajout du thread natif passe
séparément en 1,102 s dans `nested-detached-native-o2.log`.

Après le correctif de double projection, les quatorze méthodes passent à O2
en 12,105 s dans `nested-detached-final-targets-o2.log`. Le comptage final O0
dans `nested-detached-complete-count-o0.log` passe en 17,753 s : 22 exécutions
natives, 27 programmes invalides et 54 contrôles de refus.

Les tests couvrent :

- Direct, fabrique, auxiliaires imbriqués, handle public et fonction d'attente.
  Le complément exerce le handle public depuis un état async et l'auxiliaire
  synchrone consommant le porteur pour rendre sa référence.
- Un modèle indépendant cible × instant × chemin d'appel : avant terminaison
  les deux cibles sont retenues ; après terminaison seul le champ retourné
  reste réservé. Le handle public vérifie aussi la libération du champ inutilisé.
- Les deux chemins d'un retour conditionnel et la protection de l'union de
  leurs cibles, même quand un argument est une constante.
- La fin des pools des porteurs avant utilisation de la cible extérieure,
  et le refus du cas inverse. Le stockage possédé n'est jamais promu implicitement.
- Tâche inactive, échec de lancement injecté, thread natif normal/échoué,
  Select perdant, suspensions et réemploi immédiat de slots en boucle.
- Valeurs attendues et destructions uniques des porteurs ; les cibles
  empruntées ne sont pas détruites avec eux.

Le harnais natif utilise Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal à O0/O2. Pas de nouvelle preuve ASan/TSan.

## Mutations et régressions

La campagne initiale de `tests/run_nested_detached_mutations.py` détecte six
fautes dans des copies temporaires. Le retrait du prêt retourné fait accepter deux drops invalides,
détectés par les tests. Les cinq autres fautes font refuser un programme valide :
perte du type projeté, de la normalisation, de la traversée possédée, des enfants
dans le pont C ou de l'origine détachée du handle. La baseline de douze méthodes
et les six détections sont dans `nested-detached-mutations-o2.log`.

Les six mutations du lot précédent sont également détectées après une baseline
de quinze méthodes : `nested-detached-historical-mutations-o2.log`.
Ces fautes choisies ne définissent pas un taux général de détection.

Le correctif de double projection ajoute une septième mutation, détectée par
l'acceptation incorrecte du drop de la cible après attente du handle public
dans un état async. `nested-detached-final-mutations-o2.log` contient la
baseline finale de quatorze méthodes et les sept détections à O2.

La régression des champs partagés/mutables passe 56 méthodes en 50,678 s :
`nested-detached-sync-regression-o2.log`, avec CRUST_SANITIZE=undefined.
La régression async et des ponts C passe 110 méthodes en 120,916 s :
`nested-detached-regression-o2.log`, avec CRUST_SANITIZE=undefined.
Elle couvre les descendants empruntants, les fabriques détachées, les structures
mixtes, les retours de champs, les ponts de références, les appels synchrones
et les handles publics empruntants. Ces régressions précèdent le correctif de
double projection. Le passage élargi final de 110 méthodes passe en 107,404 s
dans `nested-detached-final-regression-o2.log`, avec les mêmes options UBSan.
La sélection se recouvre avec la précédente ; ces comptes ne s'additionnent
pas comme des tests uniques. Tous les processus cités sont terminés.

## Limites et suites

Les preuves concernent des graphes de types finis et des feuilles &Int.
Elles ne prouvent pas la sûreté générale, tous les types, toutes les profondeurs,
ni toutes les compositions. Les graphes cycliques ne sont pas généralisés.
reset() reste retiré du profil normal.

Le relais synchrone recevant une tâche depuis un corps async
(`open-async-task-relay-argument.crust`) et les modifications de champs descendants
par auxiliaire (`open-nested-field-replacement.crust`) restent ouverts.
Leurs refus aux deux étapes sur le code final sont conservés dans
`nested-detached-remaining-probes.log`.
L'API publique du scheduler, le placement général et les arbitrages sur les
handles lancés ne sont pas résolus par ce cycle. L'objectif global reste actif.
