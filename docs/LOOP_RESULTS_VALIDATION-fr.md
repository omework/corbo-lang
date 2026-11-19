[English](LOOP_RESULTS_VALIDATION.md)

# Validation des transferts et résultats de boucles

Cycle du 3 novembre 2026. Les décisions sont consignées dans
[LANGUAGE_RULES.md](LANGUAGE_RULES.md), en particulier S5, S5a, V4, T6, T7,
T9–T11, D1, B2, A3, A5 et P8. La
[matrice de vérification](VERIFICATION_MATRIX.md) relie les règles aux preuves
partielles de ce cycle.

Le résultat d'un `break` est matérialisé avant le nettoyage. Une allocation
transférée conserve son adresse et change de responsable de nettoyage. Un
emprunt ne transfère aucune allocation. La jonction garde les modes, les
provenances et les cibles possibles, et le contrôle de la source ou de la cible
se répète lors des transferts successifs. Les contrats propagent les effets,
les valeurs possibles et les contraintes de reset au travers des appels.
Un `continue` nettoie le bloc d'itération puis revient à l'entrée. Un
`return` nettoie les scopes de la fonction, sans installer un résultat
de boucle interrompu.

L'évaluation d'une expression de remplacement précède la destruction de
l'ancienne allocation. L'accès au receveur est vérifié dès le début de
l'affectation. Les branches qui quittent la fonction sont exclues de la
jonction. Un Int copiable fourni par un `if` peut modifier le contenu en
place. Le point-virgule distingue le marquage `<- valeur;` de la valeur
finale `<- valeur`. Les anciens exemples et tests de retour de bloc ont
été migrés vers la forme finale.

Dans chaque stack d'un pool, l'allocation avance le curseur si elle tient
dans la capacité restante. Un trou n'est pris dans l'index qu'à la limite.
Le drop ordinaire récupère le suffixe contigu déjà mort. Un reset collectif
détruit d'abord les valeurs dans l'ordre sémantique des blocs, puis remet
chaque curseur à zéro et vide les index. Les traces de récupération peuvent
parcourir les slots dans l'ordre physique après la destruction.

## Contre-exemples et contrôles

- Un receveur déplacé sur un seul chemin est refusé au début d'un
  remplacement ultérieur. Le voisin valide quitte la fonction sur le chemin
  qui déplace le receveur. Un emprunt utilisé pour la dernière fois dans la
  partie droite est accepté, son voisin qui l'utilise après est refusé.
- Un pool local peut fournir un résultat à la boucle interne et être trop
  court pour la boucle externe. Le deuxième transfert est alors refusé.
  Une valeur dans un pool durable peut également contenir un emprunt vers
  une cible locale déjà détruite à la sortie. Le test emploie le type
  concret pris en charge, un enum à champ `&Int`.
- Un reset avant le dernier usage est refusé dès que le résultat ou un
  emprunt qu'il contient peut dépendre de ce pool. Les cas combinent
  deux provenances, appels opaques, réemprunts et usage après la jonction.
- Le prototype acceptait historiquement `<- valeur;` comme valeur finale
  d'un bloc. Les tests distinguent maintenant le marquage sans receveur
  avec avertissement et le transfert qui fournit effectivement un résultat.
- Le runtime privilégiait auparavant le trou même quand le curseur avait
  de la place. Un cas à trois slots vérifie qu'il avance d'abord, réutilise
  le trou à la limite et revient au premier slot après reset. Un autre
  vérifie qu'un reset imbriqué détruit le local puis le receveur de l'ancêtre
  avant de récupérer aussi le trou sous le curseur.

## Exécutions

- Régression globale en quatre groupes, 789 tests réussis. Elle inclut
  l'oracle C existant de 3 000 transitions de pools d'enum et le modèle
  de propagation des exigences de pools à travers les contrats.
- [test_loop_results.py](../tests/test_loop_results.py) contient 18 tests, dont
  22 exécutions de programmes admis et 36 cas refusés testés par le
  vérificateur et par le pipeline de compilation. Le modèle indépendant
  construit les traces à partir des listes d'allocations par bloc. Il compare
  huit programmes générés à leurs traces et huit voisins de mode incompatible
  au diagnostic attendu, avec la graine 20261103. Les 18 tests passent aussi
  sous UBSan, y compris avec `-O2`. Le CLI `check` et `run` affiche
  l'avertissement sur un transfert sans receveur et le binaire termine avec
  la valeur suivante dans le slot réutilisé. Une analyse des 233 préfixes
  d'un exemple mêlant réemprunt et sorties incompatibles n'a déclenché
  aucune exception Python non gérée.
- [Matrice C](../validation/loop-cycle-pool-c.json) de 12 exécutions, Homebrew
  Clang 20.1.3, C11 aux niveaux O0, O2, Os et O2 avec UBSan sans récupération.
  Elle vérifie notamment l'identité, les deux sélections de provenance,
  les variantes et l'arrêt sur épuisement.
- [Mutations](../validation/loop-result-mutations.json), lancées par
  [run_loop_result_mutations.py](../tests/run_loop_result_mutations.py).
  Les quatre fautes injectées sont détectées. La conservation du candidat
  dans l'itération provoque un crash, l'omission du contrôle de durabilité
  est reprise plus tard par un invariant interne avec un autre diagnostic,
  la priorité au trou change les adresses et le recul trop tôt change
  l'ordre des traces. Ces résultats portent uniquement sur les mutations
  choisies.
- ASan n'a pas produit de preuve exploitable sur cet hôte. Le programme
  C minimal `int main(void) { return 0; }` compilé avec
  `clang -fsanitize=address` dépasse lui aussi le délai de trois secondes.

Commandes reproductibles depuis la racine.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_results.py -q
python3 tests/validate_pool_contract_c.py --output validation/loop-cycle-pool-c.json
python3 tests/run_loop_result_mutations.py
```

## Limites

La réaffectation explicite d'un ancêtre fonctionne à travers des blocs
linéaires. Le vérificateur rejette encore la jonction de branches ou la
reprise d'une boucle si la liaison d'un ancêtre a été remplacée en chemin.
Le placement physique anticipé des allocations transférées reste une
optimisation facultative. Le runtime suit l'occupation effective des
slots. Les types structurés du prototype restent les enums à champs pris
en charge. Le cycle n'établit ni preuve générale des durées de vie, ni
couverture des destructeurs utilisateur, ni validité sur une autre famille
de compilateurs C.
