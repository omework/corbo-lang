[English](BUILTIN_FEATURES_CYCLE.md)

# Cycle — Méthodes intégrées et résultats empruntés des type features

## Périmètre et invariants

Ce cycle applique TF1–TF5 aux opérations intégrées déjà retenues pour les
vecteurs, tableaux, chaînes et pools. Il ne change pas leurs règles mémoire.
Le catalogue `builtin_signatures.py` décrit les signatures ; les opérations
concrètes continuent de passer par leurs contrats et vérifications ordinaires.
Les effets ne sont pas remplacés par un contrat abstrait supposé neutre.

Le contre-exemple `Vector.len()` du cycle précédent est corrigé. La
normalisation commune des signatures reconnaît notamment `&str`, les tableaux,
les résultats faillibles et les handles. Les retours concrets `&String` et
`&mut Vector<Int>` sont désormais utilisables après spécialisation. Une vue
construite depuis un retour de `&String` conserve les cibles et parents de
l'emprunt, y compris pendant l'évaluation des arguments suivants.

## Contre-exemples recherchés

- Une méthode connue du parseur (`try_slice`, `char_at`, `byte_len`) ne doit
  pas contourner les garanties abstraites parce qu'elle a déjà été convertie
  en une opération interne. Les exigences absentes sont refusées dans un
  corps non appelé, sur un receveur nommé ou fourni par un retour.
- Une méthode de bon nom mais de mauvaise signature ne satisfait pas une
  feature, même si le corps de la fonction ne l'appelle jamais.
- `push_new` et les retours mutables réservent la cible jusqu'au dernier usage.
- Une découpe retournée par deux relais conserve l'emprunt de la chaîne ;
  mutation et `drop` prématurés sont refusés. Un caractère décodé indépendant
  peut au contraire être utilisé après destruction de la chaîne.
- Le retour `identity(&s).try_slice(...)` protège `s` et son stockage, aussi
  contre un reset historique pendant le calcul de la borne suivante. Le
  profil public continue de refuser reset.
- Une méthode de pool retournant `A<Int>` conserve la source à travers deux
  appels. Un pool trop court est refusé ; destruction puis réemploi conserve
  l'adresse du slot. `merge` consomme et détruit une seule fois sa source.
- Les remplacements d'octets refusant un résultat UTF-8 invalide laissent la
  chaîne inchangée. Les paramètres de mauvais type et conflits d'emprunt
  restent refusés après résolution d'une feature.

Deux défauts de support concret ont été révélés pendant ce travail : le
filtre des types de retour refusait `&String`, puis la construction d'une vue
depuis ce retour ne matérialisait pas son origine. Ils sont corrigés et
couverts par les cas minimaux de `test_builtin_features`.

## Exécutions

Journaux conservés dans `validation/builtin-features-*.log`.

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_builtin_features test_type_features -v` : 32 méthodes réussies,
  15,832 s. Même suite à O2 : 32 réussies, 14,673 s.
- Les programmes natifs du helper utilisent C11, UBSan et
  `-fno-sanitize-recover=all` aux deux niveaux d'optimisation.
- Le passage instrumenté du seul nouveau module relève 18 programmes
  compilés/exécutés et 57 programmes refusés, dans 16 méthodes, 7,963 s.
  Son modèle indépendant énumère 36 signatures source (receveur, arguments,
  résultat), dont 2 admises/exécutées et 34 refusées. Il n'appelle pas le
  normaliseur du compilateur. Ces nombres sont inclus dans les précédents.
- Régression ciblée contrats, corps, exigences de pools, retours partagés et
  mutables, directives, méthodes et structures locales : 173 méthodes
  réussies, 41,763 s, avec `CRUST_SANITIZE=undefined`.
- `PYTHONPATH=tests:. python3 -m unittest test_utf8_try_slice
  test_utf8_try_slice_async test_integer_conversions -v` : 32 méthodes
  réussies, 16,412 s. Cela couvre les chemins de découpes et conversions
  concernés par la mise en commun des modes de signature.

Les comptes de méthodes ne sont pas des comptes de propriétés indépendantes.
Les régressions ne couvrent pas l'ensemble des fonctionnalités du projet.

## Mutations

`python3 tests/run_builtin_feature_mutations.py` utilise des copies temporaires
du compilateur et les assertions originales. Quatre mutations détectées :

1. Omission du contrôle abstrait des méthodes déjà transformées par le
   parseur : méthodes non garanties acceptées.
2. Existence du nom utilisée à la place de la signature complète : les 34
   signatures interdites du modèle sont acceptées à tort.
3. Omission de la normalisation des modes texte : programme admis rejeté
   avec `type de paramètre inconnu 'str'`.
4. Effacement de l'origine de la vue construite depuis un retour de
   `&String` : `drop` prématuré accepté à tort.

Ce sont des fautes ciblées ; aucun taux général de détection n'en est déduit.

## Limites et suite

Le catalogue inclut d'autres signatures qui n'ont pas toutes un test natif
via une feature. Leur présence ne prouve pas que chaque forme composée est
supportée. Le cas `char.utf8_len()` via une feature reste à intégrer. Le
support général des projections, des contraintes imbriquées et de l'async
reste à compléter. Le diagnostic produit par une fonction jamais instanciée
ne constitue pas une preuve universelle de ses propriétés mémoire.

Un contre-exemple TF2 a été reproduit à la fin du cycle : une feature dont
la méthode prend un autre argument de la même feature est à tort substituée
comme si cet argument devait avoir le type du receveur. Cette égalité de
types est précisément reportée par TF2 ; la correction fait l'objet de la
suite du travail. Il n'y a pas d'ambiguïté normative bloquante sur ce point.

Mise à jour : cet écart et les résultats de méthodes contraints sont corrigés
dans [NESTED_FEATURES_CYCLE.md](NESTED_FEATURES_CYCLE.md), qui ajoute les
premières interactions exécutées avec l'async.

Aucune preuve formelle, nouvelle campagne ASan/TSan ou validation générale
du multithread n'est revendiquée. Le lot 06 et l'objectif global restent ouverts.
