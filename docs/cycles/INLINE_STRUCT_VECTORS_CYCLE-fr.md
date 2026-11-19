[English](INLINE_STRUCT_VECTORS_CYCLE.md)

# Cycle — Structures stockées directement dans les cases des vecteurs

## Règles et portée

Application de VE1/VE2, ST17/ST18, T1/T6, B1–B5, G9/G12 et GR1/GR2,
sans modification normative. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des
sept brouillons et les règles de représentation/copie ont été relus. Le reste
de l’objectif global demeure ouvert.

`Vector<Point>` stocke les champs de Point dans ses cases ; ce n’est pas un
`Vector<A<Point>>`. Ce premier raccordement concerne les structures à feuilles
Int, y compris imbriquées et vides, l’insertion d’une construction ou copie
explicite, len et copy(v[i]). Les copies peuvent sortir d’un bloc ou être
retournées par des fonctions et relais synchrones. Une copie indépendante ne
retient pas le pool du vecteur.

Le fichier historique open-inline-struct-vector.crust avait aussi une lecture
implicite `let point=v[0]`, interdite par ST17. Il est conservé avec son ancien
log ; le programme valide de ce cycle utilise `copy(v[0])` dans
validation/inline-struct-vector.crust. L’ancien refus « allocation Int »
mettait néanmoins en évidence le défaut de reconnaissance de Vector<Point>.

## Implémentation

- Enregistrement des vecteurs nominaux, distinct des vecteurs numériques,
  d’emprunts et de handles ; contrôle du type des champs dans le programme.
- Taille des cases calculée sur le layout aplati. Le runtime générique existant
  reçoit cette taille et un alignement adapté ; aucune allocation par élément
  n’est cachée dans les cases. Le temporaire de construction/copie est nettoyé
  après insertion de ses champs.
- Copie d’une case vers une structure locale, avec contrôle d’index et prêt
  du vecteur pendant son évaluation. Raccordement des analyses de résultats,
  de contraintes et de types, et de la réservation du résultat dans le parent.
- Paramètres Vector<Point> empruntés/transférés reconnus. Le retour d’une copie
  locale utilise le stockage fourni par l’appelant.
- Le planificateur des réservations de vecteurs conserve le chemin générique
  de placement à l’exécution pour les régions de structures ; l’optimisation
  anticipée de leur stockage croissant reste à généraliser.

Aucune modification du runtime C ni désactivation de ses assertions.

## Défauts rencontrés

La première passe a exposé la réservation manquante de `copy(v[i])` dans le
parent. Elle a été raccordée au planificateur existant. La lecture sans copy
échouait avec un diagnostic de tableau fixe ; elle explique maintenant la copie
explicite requise. Le retour depuis un paramètre Vector<Point> nécessitait aussi
de communiquer son type au planificateur des retours locaux.

Le cas de structure vide a ensuite détecté un couple taille/alignement invalide
(taille 1, alignement int), refusé par le runtime. Il utilise maintenant une
case alignée de taille sizeof(int), avec un tampon neutre pour les lectures et
écritures, sans lire hors du payload vide.

Les premières passes comportaient également des erreurs de tests : nom anglais
du diagnostic d’index, directive placée avant fn au lieu d’un bloc et sans sa
notation actuelle, motif trop restrictif pour les noms C générés. Ces attentes
ont été corrigées ; aucune règle d’acceptation n’a été assouplie pour les tests.

## Exécutions

Huit méthodes ciblées : **10 exécutions C**, dont 8 succès et 2 arrêts attendus
pour index négatif/hors longueur ; **7 programmes invalides**, chacun soumis à
verify_program et compile_source. Les valeurs imprimées sont écrites dans les
tests indépendamment du compilateur. Le layout généré fait aussi l’objet d’un
contrôle de représentation, complémentaire à l’exécution.

- Insertion, copie et destruction du vecteur avant lecture de la copie.
- Copie reçue par le parent après fin du pool local.
- Structures imbriquées et copie explicite d’une variable encore utilisable.
- Deux vecteurs grandissant en parallèle sur les deux fronts, puis avec
  annotation de région ; réemploi du pool après destruction.
- Refus d’une copie implicite, d’une flèche manquante, d’un A<Point> fourni à
  une case Point, d’un usage après drop et d’une mutation sans let mut.
- Prêt partagé : push refusé avant son dernier usage et accepté après.
- Insertion par fonction, copie retournée par un relais, drop puis lecture.
- Structures vides, croissance et réemploi.

Commande ciblée :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_inline_struct_vectors -v
```

Résultat final ciblé : **8 méthodes, 4,477 s, code 0**, dans
validation/inline-struct-vectors-targeted-fifth.log. Les quatre premiers logs
sont conservés. Configuration native : Clang C11, pthread, Wall/Wextra/Werror,
UBSan avec arrêt sur diagnostic. Deux arrêts de bornes sont attendus et testés.

Régression O2/UBSan : **373 méthodes, 340,917 s, code 1 : une erreur**.
Sélection reproductible dans validation/inline-struct-vectors-test-selection.txt
et sortie dans validation/inline-struct-vectors-regression.log. Les 372 autres
méthodes passent, notamment les modèles existants de durées de vie et de
signatures. Le compilateur n’a plus changé après le lancement de cette passe.

L’erreur concerne l’ancien test de résultat propriétaire d’une type feature :
sa méthode exigeait `self: -> Item`, mais son appel fournissait `p.new()`, donc
un A<Item>. Elle est reproduite sur le snapshot initial dans
validation/inline-struct-vectors-preexisting-feature-failure.log (code 1),
indépendamment de ce lot. H1/H3 et le brouillon 06 ne permettent pas cette
conversion implicite. Le test conserve désormais ce programme comme refusé aux
deux entrées et vérifie l’identité, la valeur et le réemploi sur une structure
locale conforme à la méthode. Le cas de pool enfant est également refusé au
contrôle T/A<T> ; il ne prouve donc pas une vérification de durée de vie de pool
à travers cette feature.

Complément après cette seule correction de fixture :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_type_features test_inline_struct_vectors -v
```

**30 méthodes, 16,386 s, code 0**, dans
validation/inline-struct-vectors-complement.log. La passe globale de 373 n’est
pas présentée comme un unique run vert : sa seule erreur a été expliquée,
reproduite avant modifications et couverte par ce complément. Empreintes des
fichiers source vérifiées inchangées pendant les exécutions. Aucun échec
inexpliqué ne reste dans cette sélection.

### Complément : trois exemples précédemment vérifiés seulement à la compilation

Pendant la régression, les trois fixtures déjà consignées du cycle précédent
ont été exécutées avec le même harnais O0/UBSan :
open-async-vector-result-consumer.crust, open-vector-nominal-reference-payload.crust
et open-async-vector-nominal-reference-payload.crust. Chacune imprime 7 et
détruit Item une fois ; les deux dernières détruisent aussi Point une fois.
Sortie : validation/vector-supplemental-native.log, code 0. Ces trois exécutions
s’ajoutent aux dix ciblées ci-dessus ; elles ne sont pas une preuve générale
des références nominales dans tous les conteneurs.

Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 - <<'PY'
from pathlib import Path
import test_select_source as harness
case = harness.SelectSourceTests()
for name in ('open-async-vector-result-consumer',
             'open-vector-nominal-reference-payload',
             'open-async-vector-nominal-reference-payload'):
    run = case.run_source(Path('validation', name+'.crust').read_text())
    case.assertEqual(run.stdout, '7\n')
    case.assertEqual(run.stderr.count('=Item\n'), 1)
    if 'nominal' in name:
        case.assertEqual(run.stderr.count('=Point\n'), 1)
    print(name, run.stdout, run.stderr)
PY
```

## Limites et suite

Ce cycle ne clôt pas VE1–VE6 : champs empruntés/propriétaires, déplacement d’une
structure nommée dans une case, extraction/remplacement/résultats faillibles,
emprunts et tranches de ces cases, push_new, retours du conteneur et intégration
async restent à raccorder. Le refus actuel de ces formes est une limite
d’implémentation, pas une nouvelle règle du langage. Les graphes et tests des
vecteurs de handles existants ne prouvent pas ces formes en ligne.

Pas de nouveau modèle indépendant, campagne aléatoire, mutation ou ASan dans
ce lot, conformément à la priorité donnée à l’implémentation et aux cas
énumérés. Les tests et UBSan ne constituent pas une preuve générale de sûreté.

Reproductibilité : snapshot initial /tmp/crust-before-inline-struct-vectors,
patch et empreintes validation/inline-struct-vectors.patch et
validation/inline-struct-vectors-changes.json, C généré
validation/inline-struct-vectors.c.
