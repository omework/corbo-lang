[English](VECTOR_PAYLOAD_CONTAINERS_CYCLE.md)

# Cycle — Retours de vecteurs contenant des graphes d’objets

## Règles et portée

Suite de VECTOR_PAYLOAD_EXCHANGES_CYCLE.md. H1–H3, VE1–VE4, B1–B5/B4c,
D1–D3, F2–F4 et les règles de nettoyage restent inchangés. Les consignes,
les guidelines, l’index des sept brouillons et les règles concernées ont été
lus dans cette session. La validation reste centrée sur les fonctionnalités
retenues et les régressions directes, conformément à la priorité utilisateur.

Les retours synchrones de Vector<A<Item>> conservent maintenant les graphes de
leurs éléments dans les fabriques, relais et transformations testés. Le résultat
peut être neuf ou restituer un vecteur reçu par transfert. Le pool du vecteur,
les pools des objets et les cibles de leurs emprunts restent distincts.

## Implémentation

- Le contrat FunctionResult porte `vector_values`, inventaire des graphes actifs
  du conteneur retourné. Les descriptions de positions/suppressions existantes
  conservent leur rôle ; les chemins virtuels `[]` ne deviennent pas des champs
  propriétaires ordinaires du vecteur.
- L’inférence des résultats restitue ces graphes au retour d’un sous-appel et
  dans les relais. Les références et descendants possédés suivent les éléments.
- Le vérificateur opaque résout les graphes avant de publier les effets de
  l’appel, puis les rattache aux identités des éléments du résultat. Les sources
  et cibles sont contrôlées à la destination avec les mécanismes existants.
- La vérification des corps et la génération C conservent les graphes des chemins
  retournants, y compris lorsque les objets neufs ne reçoivent leur identité
  concrète qu’au cours de cette vérification.
- L’analyse de contraintes rattache les graphes aux identités des éléments
  retournés. Elle conserve les champs hérités et descend récursivement dans les
  charges propriétaires, au lieu de ne reporter que leurs sources directes.

Les adresses, le runtime et le format C ne changent pas. Le placement des objets
n’est pas modifié par ce lot.

## Tests ciblés

Neuf méthodes, **12 exécutions C** après verify_program et compile_source,
et **18 programmes invalides** refusés aux deux entrées.

- Fabrique avec pools injectés et référence Int ; relais supplémentaire.
- Restitution d’un vecteur transféré, directement et via un relais ; flèche
  obligatoire et protection de la cible après le retour.
- Item possédant Inner qui emprunte Int : lecture du descendant, nettoyage et
  réemploi d’un pool de capacité 1.
- Charge contenant &mut Int : lecture par l’objet admise, lecture/écriture
  directe de sa cible refusée avant extraction.
- Pools du vecteur ou de ses objets trop courts : transfert parent refusé.
- Deux retours conditionnels empruntant respectivement a et b : sorties 7 et 9,
  chacune des cibles possibles protégée chez l’appelant.
- Fabrique retournant un vecteur vide ou rempli : longueurs 0 et 1.
- Vecteur reçu, ancienne entrée détruite puis nouvelle entrée transférée avant
  restitution : valeur 9 et cible de la nouvelle entrée protégée.
- Deux éléments puis suppression du premier avant restitution : le second garde
  sa référence et sa cible reste protégée après extraction.

## Défaut rencontré et précision

Le premier essai sur le graphe Item/Inner a échoué : l’analyse de contraintes
créait une identité de résultat différente de celle portée par les cases du
vecteur. Le filtrage des charges actives perdait donc son graphe. L’association
utilise désormais les éléments effectivement décrits par le contrat de stockage.
Leurs champs hérités et les références des descendants sont également résolus.

Les graphes peuvent être joints par provenance lorsque le contrat ne distingue
pas davantage les identités. Cette union est conservative ; elle ne promet pas
une corrélation complète entre chaque indice, chaque branche et chaque cible.
Les scénarios exécutés ne couvrent pas tous les cycles ou types de champs.

## Exécutions et artefacts

- Premier cas enregistré exécuté : sortie 7, code 0,
  `validation/vector-payload-containers-first-o0.log`.
- Premier ciblé O0 : cinq méthodes, 2,226 s, un échec sur Inner,
  `validation/vector-payload-containers-targeted-first-o0.log`.
- Deuxième : cinq méthodes, 2,630 s, code 0.
- Troisième : huit méthodes, 5,017 s, code 0.
- Ciblé final O0 : **neuf méthodes, 5,179 s, code 0**,
  `validation/vector-payload-containers-targeted-fourth-o0.log`.
- Régression O2/UBSan : **168 méthodes, 164,706 s, code 0**, sélection
  `validation/vector-payload-containers-test-selection.txt`, journal
  `validation/vector-payload-containers-regression-o2.log`.

C11, pthread, Wall/Wextra/Werror et UBSan fatal. Le programme
`validation/open-vector-payload-container-contract.crust` précédemment refusé
est désormais exécuté ; son ancien journal reste historique. Le C et le contrat
sont dans `validation/vector-payload-containers.c` et
`validation/vector-payload-containers-contract.json`. Le contrat sépare la
source vp du vecteur, la source p de son élément et la cible empruntée n.

Snapshot : `/tmp/crust-before-vector-payload-containers`. Patches exacts et
empreintes des trois modules et du test :
`validation/vector-payload-containers-changes.json`.

## Limites et suite

Les captures/résultats async de vecteurs contenant des emprunts restent ouverts.
Le cas minimal `validation/open-async-vector-payload-graph.crust` transfère un
vecteur à une tâche qui suspend, extrait et lit un Item, puis est attendue par
join. Il reste explicitement refusé aux deux entrées, journal associé conservé.
Les références nominales générales, certains consommateurs de résultats et les
compositions récursives demandent encore leur raccordement et leur validation.

Reset reste retiré du profil normal. Aucun nouveau modèle indépendant ou test
de mutation n’est ajouté ; les modèles antérieurs de la régression ne prouvent
pas les nouveaux graphes de conteneurs. Les scénarios exécutés et UBSan ne sont
pas une preuve générale de sûreté. L’objectif global reste actif.
