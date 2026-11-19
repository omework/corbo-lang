[English](MODULAR_CALLS.md)

# Appels vérifiés à partir des contrats

Le vérificateur mémoire ne parcourt plus le corps d'une fonction lorsqu'il
rencontre un appel. Il utilise une interface sans corps, `FunctionContract`,
définie dans [contracts.py](../contracts.py). Les exemples de cette étape utilisent
des pools explicitement typés.

```rust
fn create(memory: &mut Pool<Int>) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn main() {
    let mut memory = pool<Int>(1);
    let mut data = create(&mut memory);
    memory.reset();
    print(data); // Refusé : data doit encore être utilisée.
}
```

Le contrat indique que `create` alloue un Int dans son premier paramètre et
retourne une allocation neuve de cette source. Cela suffit à rattacher le
résultat au pool de `main`, puis à refuser le reset avant sa dernière lecture.

## Vérification et génération séparées

`Compiler.verify` effectue les étapes suivantes :

1. Valider les signatures et inférer les effets, résultats et contraintes.
2. Construire les interfaces sans corps des fonctions.
3. Vérifier chaque corps séparément avec ses paramètres symboliques. Tous ses
   sous-appels utilisent uniquement les interfaces.
4. Vérifier de la même manière les instructions au niveau du programme, s'il
   n'y a pas de `main`.

Une fonction déclarée après son appel est couverte de la même façon. Chaque
corps doit passer la vérification avant que le programme soit accepté. La
récursion reste refusée. Les analyses d'inférence parcourent les corps pour
construire les contrats ; elles réutilisent les résumés des sous-appels.

`Compiler.compile` lance d'abord cette vérification, puis le backend spécialisé
existant. Le backend parcourt encore les corps pour produire les fonctions C,
leurs captures et les nettoyages exacts. Ses contrôles de cohérence sont
conservés. La commande `check` et l'API `verify_program` s'arrêtent avant ce
backend ; elles vérifient donc sans ce second parcours de génération.

Le vérificateur des corps construit encore des fragments C temporaires pour
ses propres blocs, puis les jette. Séparer entièrement ces fragments du suivi
mémoire est un travail distinct. Les appels opaques ne produisent aucune
définition C et ne lisent aucun corps appelé.

## Contenu de l'interface

- Noms, types et modes des paramètres ; type et mode du résultat.
- Types alloués par chaque source et sources possiblement réinitialisées.
- Types de pools exigés par les signatures et sous-appels, même sans allocation.
- Possibilité de retour normal.
- Origines possibles du résultat : entrées reçues ou allocations neuves dans
  les sources reçues ; restitution garantie d'une même entrée lorsqu'elle existe.
- Contraintes d'égalité et de distinction entre les sources des paramètres.

Les paramètres d'enums portant des champs &Int disposent également de symboles
de sources par chemin de champ. Le contrat protège ces cibles lorsqu'un reset
précède leur lecture ; un wrapper substitue les chemins sans ouvrir le corps.
Les contrats des retours alloués portant ces champs décrivent leurs cibles
entrantes par identité. Leur résolution conserve la protection après l'appel,
sans consulter le corps du callee. Voir [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md)
et [BORROWED_RETURNS.md](BORROWED_RETURNS.md).

L'interface ne contient ni AST de corps ni adresse runtime. Les tableaux
d'inférence séparés ne sont pas nécessaires pour appliquer un appel opaque.

## Transition à l'appel

Les arguments sont préparés de gauche à droite avec les contrôles de modes,
types, déplacements et emprunts existants. Les arguments déjà préparés restent
protégés pendant l'évaluation des suivants. Les contraintes sont substituées
avec toutes les provenances possibles et les exigences de stockage sont
vérifiées contre les pools effectivement fournis.

Les allocations reçues avec `->` sont consommées. Les emprunts temporaires
se terminent à la sortie de l'appel ; ils n'autorisent pas la consommation d'un
paramètre reçu par `&` ou `&mut` dans le corps, vérifié séparément.

Un reset possible protège tous les usages futurs du côté appelant, y compris
ses emprunts momentanément suspendus et les arguments d'un appel englobant.
Une valeur externe potentiellement concernée perd ses accès. Le vérificateur
conserve un nettoyage conditionnel pour les chemins où elle peut survivre :
un effet possible n'est pas assimilé à une destruction runtime certaine.
La génération C spécialisée détermine le nettoyage effectif sur chaque chemin.

Le résultat alloué est reçu vivant sur chaque chemin qui revient normalement :

- Une restitution garantie réutilise l'identité entrante et conserve ses marques
  d'import/export, tout en consommant l'ancien accès déplacé.
- Une sélection ou un objet neuf reçoit un descripteur portant l'union des
  provenances et racines d'origine possibles.
- Un objet neuf retourné après un reset est vivant. De même, un reset sur un
  chemin ne détruit pas le résultat rendu vivant par un autre chemin.

Une copie scalaire faite avant un reset ne dépend plus du stockage lu.
Un contrat sans retour normal ne produit pas de chemin de continuation.

## Utilisation

```sh
python3 prototype/crust.py check examples/modular_calls.crb
python3 prototype/crust.py effects examples/modular_calls.crb
python3 prototype/crust.py run examples/modular_calls.crb
python3 prototype/crust.py check examples/invalid_modular_reset.crb
```

`check` ne demande pas de compilateur C et n'accepte ni `--run` ni `-o`.
`effects` utilise aussi le vérificateur sans lancer le backend, puis affiche
les effets, résultats et contraintes inférés en JSON.

## Validation et limites

[tests/test_modular_calls.py](../tests/test_modular_calls.py) vérifie des appels
avec un catalogue de corps vide et sans tableaux d'inférence séparés. Un autre
test compte les entrées de corps : chaque fonction est vérifiée séparément et
les sous-appels n'ouvrent jamais le corps du callee. Les cas couvrent pools,
enums, retours conditionnels, provenances multiples, resets, emprunts,
arguments, boucles, divergence, réutilisation des slots et comparaison avec
la compilation et l'exécution du C.

Ces tests ne sont pas une preuve de sûreté du langage. Le vérificateur, les
analyses d'inférence et le backend restent dans la base de confiance. Les
restrictions actuelles sur les transferts, références et types ne changent pas.
Les anciens backends de stockage restent disponibles pour compatibilité ;
cette étape n'introduit pas un nouvel allocateur ni un déplacement d'adresse.

Validation : 522 tests réussis dans la suite complète standard et 522 avec
`CRUST_SANITIZE=undefined`, dont 28 nouveaux tests sur les appels modulaires.
