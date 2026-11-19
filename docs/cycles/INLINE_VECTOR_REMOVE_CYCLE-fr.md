[English](INLINE_VECTOR_REMOVE_CYCLE.md)

# Cycle — Extraction de structures stockées directement dans les vecteurs

## Règles et portée

Suite de INLINE_STRUCT_VECTORS_CYCLE.md. VE1–VE4, ST17/ST18, T1/T6,
B1–B5/B4a, ME1/ME2, F2–F4 et TF1–TF5 restent inchangées. AGENTS.md et
l’index des brouillons ont été relus ; VALIDATION_GUIDELINES.md a été lue
intégralement dans ce travail continu. Les règles d’extraction, de stockage
local, de transfert et d’évaluation des arguments ont été consultées.

`let point = <-v.remove(i)` retire une structure en ligne, décale les cases
suivantes et produit une valeur locale indépendante. Il ne produit pas un
A<Point>. Le résultat peut sortir d’un bloc, d’une branche, d’une boucle ou
d’une fonction, en utilisant le stockage du destinataire. Le pool du vecteur
n’a pas à survivre à cette valeur indépendante à champs Int.

Ce lot conserve le périmètre d’éléments du précédent : feuilles Int, structures
imbriquées et vides. Il ne clôt pas la généralisation de Vector<T>.

## Raccordements

- Lecture/copie et extraction utilisent une même réception de payload local.
  Remove demande un accès mutable et appelle vector_remove, qui préserve
  l’ordre ; aucune modification du runtime C.
- Les analyses de types, résultats et contraintes savent que l’extraction
  produit une structure locale fraîche, sans dépendance au pool du vecteur.
- La réservation du résultat dans le parent/appelant reconnaît le producteur
  remove, y compris derrière une fonction, un relais, un if ou un break.
- Les retours et le drop direct conservent la notation de consommation
  explicite. La résolution statique d’une type feature voit le type Point
  du résultat et refuse une signature incompatible.

## Défauts et corrections pendant le lot

Le premier raccordement avait oublié le résultat typé dans l’analyse d’effets
et utilisait un mauvais champ de la valeur abstraite des résultats. Ces erreurs
internes ont été corrigées. Le break direct et le return direct nécessitaient
également de conserver explicitement l’opération transférée.

La deuxième passe ciblée ne terminait pas l’analyse d’un relais de fonction.
Le processus était confirmé vivant, occupait le CPU et restait sur ce test ;
il a été interrompu explicitement (code 130). Sa trace est conservée. La cause
était l’utilisation de l’identité du tuple d’opération reconstruit à chaque
passe d’inférence : le contrat changeait sans cesse. La provenance est désormais
rattachée au nœud source stable du receveur de cet appel. Le même relais termine
et s’exécute dans les passes suivantes.

Une attente initiale de test a été corrigée selon ME1/ME2 et B4a :
`v.remove(v.len()-1)` tente de lire le receveur alors que son emprunt mutable
direct est déjà fourni à l’appel externe. Ce programme reste refusé. Le cas
admis calcule l’indice dans l’instruction précédente. Le test vérifie les deux
comportements ; aucune réservation à deux phases n’est ajoutée implicitement.

## Tests ciblés exécutés

Huit méthodes, **15 exécutions C** (13 succès et deux arrêts attendus sur
index invalide), **8 programmes invalides** contrôlés par verify_program et
compile_source. Les valeurs attendues sont écrites indépendamment du compilateur.

- Retrait du premier élément, longueur et ordre du reste ; résultat lu après
  destruction du vecteur.
- Fonction take et relais ; le résultat local est refusé sous une signature
  A<Point>. Un emprunt partagé encore utilisé empêche l’appel mutable.
- Réception dans un parent, les deux branches du if, break avec receveur, et
  sortie d’un bloc contenant le pool du vecteur.
- Consommation immédiate `drop(->v.remove(0))` et réemploi à chaque itération.
- Indice préparé avant l’appel, dernier usage d’un emprunt, refus de l’accès
  au receveur pendant ses arguments et de l’usage après drop.
- Structures imbriquées sur le second front de croissance et structure vide.
- Résolution de remove via une type feature, signature incorrecte refusée.
- Index -1 et index égal à la longueur : arrêt diagnostiqué avant lecture.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_inline_vector_remove -v
```

Résultat final ciblé : **8 méthodes, 5,127 s, code 0**, dans
validation/inline-vector-remove-targeted-fifth.log. Les logs first à fourth
sont conservés : première passe en échec, deuxième interrompue, troisième
encore en échec, quatrième réussie sur les sept premières méthodes.

Compilation native : Clang C11, pthread, Wall/Wextra/Werror et UBSan fatal.
Les deux arrêts sur bornes sont attendus et distincts d’un diagnostic UBSan.

## Régression et limites

Régression O2/UBSan : **185 méthodes, 116,345 s, code 0**, sélection dans
validation/inline-vector-remove-test-selection.txt, journal
validation/inline-vector-remove-regression.log. La sélection couvre les
vecteurs de valeurs et handles, contrats, fonctions, boucles, copies et retours
locaux, type features et extractions async existantes. Les autres familles
inchangées ne sont pas systématiquement rejouées.
Les empreintes du compilateur et du test ciblé sont restées inchangées pendant
cette exécution. Les modèles existants de signatures et de contraintes des
familles sélectionnées sont rejoués ; aucun modèle nouveau de l’extraction
structurée n’est revendiqué.

Les champs empruntés/propriétaires, déplacements de variables nommées dans les
cases, pop/replace/try_push, emprunts de cases et tranches, push_new et intégration
async des structures en ligne restent à raccorder. Une extraction de handles
conserve une provenance de pool ; ce lot ne remplace pas cette sémantique par
une copie en ligne. Aucun reset n’est réintroduit.

Pas de nouveau modèle indépendant, de campagne aléatoire ou de mutations dans
ce lot. L’oracle natif contrôle les valeurs et la longueur de la séquence, les
refus vérifient les règles aux deux entrées. UBSan et cette sélection ne prouvent
pas la sûreté générale de toutes les compositions.

Reproduction : /tmp/crust-before-inline-vector-remove ; patch et empreintes
validation/inline-vector-remove.patch et validation/inline-vector-remove-changes.json ;
fixture et C généré validation/inline-vector-remove.crust et .c.
