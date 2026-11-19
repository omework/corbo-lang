[English](NESTED_OWNED_BORROWS_CYCLE.md)

# Emprunts dans les descendants possédés d'une tâche

## Règles et portée

Ce cycle applique ST6–ST15, H1/H2, B1–B5, D1, T1/T6, AS2/AS8–AS15,
RT6/RT8 et SL1. Aucune règle normative n'est modifiée. Les graphes de types
finis peuvent maintenant contenir des champs &Int/&mut Int dans leurs
descendants A<T>. Le transfert et le retour du graphe entier conservent les
sources et les cibles de ces descendants.

Le cas `validation/open-nested-owned-borrowed-capture.crust`, auparavant
refusé, est exécuté avec la sortie 1. Le voisin qui détruit number avant
l'attente est refusé aux deux étapes. Le journal initial du lot précédent
reste historique ; les premières décisions après correction sont dans
`validation/nested-owned-borrows-first-probe.log`.

## Implémentation

- `owned_reference_paths` énumère les références via les arêtes possédées,
  avec un chemin complet tel que `.left/.view`. Les champs homonymes de
  descendants différents ne sont pas confondus. La traversée s'arrête au
  premier type répété ; les graphes de types cycliques ne sont pas généralisés
  par ce lot.
- Les contrats de résultats, contraintes de stockage, paramètres symboliques
  de tâches et captures concrètes propagent ces chemins. Le backend conserve
  les prêts des enfants lors de la construction de leur porteur.
- Après join, les dépendances retournées sont redistribuées sur les enfants
  du graphe reconstruit. Les laisser uniquement sur la racine protégeait les
  durées de vie globales mais faisait échouer la lecture d'un enfant avec
  « provenance de champ emprunté manquante ». Ce refus est reproduit dans
  `nested-owned-borrows-sync-explicit-read.log`, puis couvert par le test
  `test_sync_caller_result_keeps_nested_target`.
- Le backend accepte l'emprunt explicite du contenu d'un champ A<Structure>,
  par exemple `read(&*result.inner)`. Il passe le descripteur de l'enfant et
  conserve la réservation du parent. Le chemin implicite `result.inner.view`
  n'est pas ajouté : les tests finaux emploient le déréférencement explicite.

Les patches de source sont dans `validation/nested-owned-borrows-*.py.patch`,
comparés à la copie antérieure `/tmp/crust-before-nested-owned-borrows`.

## Validation exécutable

`tests/test_nested_owned_borrows.py` comporte quinze méthodes finales.
Le comptage O0 est dans `validation/nested-owned-borrows-complete-count-o0.log`.
Il passe en 8,258 s : 23 exécutions natives, 32 programmes invalides et
64 vérifications de refus, une par étape pour chaque programme.
Les preuves O2 sont la base de treize méthodes de
`nested-owned-borrows-final-mutations-o2.log`, puis les deux ajouts
`nested-owned-borrows-mut-return-o2.log` et
`nested-owned-borrows-identity-o2.log`, exécutés séparément.

Le harnais emploie Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal à O0/O2. Les programmes invalides sont
testés par verify_program et compile_source. Aucun résultat ASan/TSan nouveau.

Les scénarios comprennent :

- Le modèle indépendant des huit dispositions des trois durées de vie
  (pool extérieur, pool intérieur, cible) : seul le cas où les trois
  survivent permet d'exporter la tâche.
- Les appels directs, les fabriques et un relais de tâche appelé en contexte
  synchrone ; les retours entiers en appelants synchrones et async.
- Les cibles mutables avant et après attente, le réemprunt de l'enfant et les
  refus d'accès, remplacement ou drop incompatibles avant son dernier usage.
- Deux enfants avec le même nom de champ, profondeurs deux et quatre,
  retours conditionnels et conservation des deux cibles possibles.
- Le drop d'une tâche inactive, les échecs de lancement injectés, le thread
  natif, Select perdant et le réemploi immédiat des slots après nettoyage.
- Une sonde C compare les adresses de la racine, de l'enfant et de sa cible
  empruntée pendant chaque suspension et après le retour. Les valeurs et
  destructions uniques sont également vérifiées.

Le log `nested-owned-borrows-first-tests-o0.log` contient le refus d'un relais
synchrone prenant une tâche depuis un corps async. Ce cas valide reste ouvert,
et n'a pas été transformé en cas normativement interdit pour faire passer les
tests. La variante synchrone est testée ; la variante async est conservée dans
un fichier minimal indiqué ci-dessous.

Les essais exploratoires de lecture imbriquée avec points, présents dans
`nested-owned-borrows-read-o0.log` et `nested-owned-borrows-nine-o2.log`, ont
précédé le choix de conserver l'accès explicite H2. Le code de traversée
implicite a été retiré ; ces anciens passages ne sont pas les preuves de la
syntaxe finale. `nested-owned-borrows-explicit-read-o0.log` et les suites finales
exercent `&*`.

## Mutations

Six fautes sont détectées dans des copies temporaires par
`tests/run_nested_owned_borrow_mutations.py` :

- Couper les chemins descendants et omettre les prêts du constructeur font
  accepter à tort des destructions précoces. L'absence d'erreur est détectée
  aux deux étapes.
- Oublier le préfixe d'un descendant, sa dépendance après restitution ou sa
  cible symbolique fait refuser des programmes valides.
- Classer un champ possédé comme simple référence provoque une fuite de slot,
  détectée par le réemploi d'un pool de capacité deux (`pool capacity exceeded`).

Le passage final est `nested-owned-borrows-final-mutations-o2.log`.
Les neuf mutations du lot mixte précédent sont également détectées dans
`nested-owned-borrows-historical-mutations-o2.log`. Leur point d'injection sur
la classification des layouts a été adapté au nouveau calcul partagé, avec
le même objectif de refuser artificiellement un layout mixte valide.
Ces fautes choisies ne constituent pas un taux général de détection.

## Régressions et limites

`nested-owned-borrows-regression-o2.log` : 98 méthodes passent en 92,504 s,
après propagation des captures mais avant le correctif de restitution des
dépendances sur les enfants. `nested-owned-borrows-final-regression-o2.log` :
96 méthodes passent en 91,087 s sur le code final. Ce dernier passage couvre
les contrats de captures par champ, les enveloppes locales, les retours de
structures propriétaires/empruntantes, les ponts de handles à champs et les
captures de structures par référence. Les deux sélections demandent
CRUST_SANITIZE=undefined et se recouvrent ; leurs comptes ne s'additionnent
pas comme des tests uniques.

Le complément synchrone `nested-owned-borrows-sync-regression-o2.log` passe
87 méthodes en 41,780 s : champs partagés/mutables, tableaux de références
imbriqués et résultats propriétaires, avec CRUST_SANITIZE=undefined. Il teste
les analyses communes touchées par la propagation des chemins descendants.
Tous les processus finaux cités sont terminés.

Ces preuves sont finies. Elles ne démontrent ni la sûreté générale du modèle,
ni toutes les compositions, ni les graphes cycliques. reset() reste retiré
du profil normal, sans réintroduction dans ce cycle.

## Cas encore ouverts

- `validation/open-nested-detached-reference.crust` : restituer seulement le
  champ partagé d'un descendant via `read(&*value.inner)` reste refusé comme
  retour non durable, bien que la cible extérieure survive. Il faut projeter
  la cible indépendamment du stockage des deux porteurs.
- `validation/open-async-task-relay-argument.crust` : un appel synchrone
  prenant une tâche comme argument depuis un état async reste non raccordé.
- Les modifications des champs d'un descendant via un auxiliaire ne sont pas
  généralisées. Les probes `nested-owned-borrows-replacement-probe.log` et
  `nested-owned-borrows-sync-replacement-probe.log` enregistrent les refus
  actuels, pour l'ancienne comme pour la nouvelle cible.
  `validation/open-nested-field-replacement.crust` conserve le voisin valide
  qui libère seulement l'ancienne cible ; son refus aux deux étapes est
  reproduit dans `nested-owned-borrows-replacement-fixture.log`.

Les deux premiers refus sont reproduits aux deux étapes dans
`nested-owned-borrows-next-probes.log`. L'API publique du scheduler, le
placement général, les autres signatures et les deux arbitrages sur les
handles lancés restent aussi ouverts. L'objectif global demeure actif.
