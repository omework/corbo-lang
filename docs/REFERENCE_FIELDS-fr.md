[English](REFERENCE_FIELDS.md)

# Champs contenant un emprunt en lecture

**Actualisation des emprunts mutables :** [MA1–MA6](MUTABLE_ACCESS-fr.md)
remplace l’exclusivité déduite du seul `&mut`. Les exemples et verdicts d’exclusion
rapportés dans les anciens cycles ci-dessous sont historiques ; ils ne définissent
pas la compatibilité actuelle des accès. Permissions, validité, synchronisation
et fins de branche se vérifient séparément.


Extension ultérieure : les [champs &mut Int](MUTABLE_REFERENCE_FIELDS.md) sont maintenant disponibles ; les mesures ci-dessous décrivent ce cycle historique.

Le prototype accepte désormais des champs `&Int` dans les enums. Cette étape
implémente la règle discutée : un objet qui doit encore lire sa référence
empêche la destruction préalable de la cible. Les exemples utilisent des pools.

```rust
enum View { Item { data: &Int } }

fn use_view(view: &View) {
    match &view {
        View.Item { data: value } => { print(value); }
    }
}

fn main() {
    let mut data_pool = Pool<Int>::new(1);
    let mut view_pool = Pool<View>::new(1);
    let mut data = new(data_pool) Int(42);
    let mut view = new(view_pool) View.Item { data: &data };
    use_view(&view);
    drop(-> data); // Autorisé après le dernier usage du champ emprunté.
}
```

Placer `drop(-> data)` avant `use_view(&view)` fait refuser le programme.
Mutation, déplacement, réaffectation ou reset de la cible sont également refusés
si un emprunt stocké doit encore servir. Les pools restant vivants ne rendent
pas valide une allocation dont la vie est terminée.

## Sous-ensemble retenu

- Champs scalaires Int et champs immuables `&Int`, mélangés dans une variante.
- Initialisation par `&nom` d'une allocation Int explicite ; pas de référence
  vers une variable scalaire, de champ `&mut` ou de référence vers un autre enum.
  Un emprunt déjà existant se fournit par son nom (`data: view`), sans `&`
  supplémentaire. Les accès incompatibles du parent mutable restent suspendus
  jusqu'au dernier usage du champ. Voir [REFERENCE_VALUES.md](REFERENCE_VALUES.md).
- Lecture via `print(view)` ou `match &view`. Dans le match, un champ Int est
  copié ; un champ &Int devient un emprunt en lecture. `print`, `address` et
  copie `let mut n = *value` sont permis dans le bras de lecture.
- Passage de ces objets aux fonctions par les modes existants, y compris
  réception par `->` et retour alloué avec vérification de durée de vie. Les champs ne donnent
  aucun droit mutable sur les cibles, même avec un paramètre `&mut View`.
- Déplacement local du porteur, réaffectation, branches et expressions if avec
  réunion conservative des cibles possibles.
- Transfert de bloc si les cibles vivent déjà dans le scope de destination ou
  un de ses ancêtres. Une cible du scope quitté fait refuser ce transfert.

Les [retours contenant des emprunts](BORROWED_RETURNS.md) sont désormais pris
en charge. Le contrat décrit les cibles de chaque champ et la vérification
enfant → parent contrôle leur durée de vie. D1 interdit désormais toute promotion
implicite des cibles locales ; l'ancienne proposition de transfert automatique
est abandonnée. Les graphes transitifs, cycles et références vers d'autres enums
restent différés. Le contrôle de D1 est couvert pour les champs &Int ; cette
étape n'implémente pas un graphe général et n'introduit pas de structs.

Tout usage du porteur est traité conservativement comme un usage de ses champs
empruntés. Même un champ ignoré par un pattern ou un usage qui observe seulement
l'adresse peut prolonger la protection. Les branches possibles sont réunies ;
on ne promet pas une analyse minimale des derniers usages par champ.

## Suivi statique et contrats

Chaque allocation porte une table immuable : chemin `Variante.champ` → cibles
possibles. Les déplacements conservent cette table, les réaffectations remplacent
le porteur, les jonctions réunissent les alternatives. Une référence n'est pas
une nouvelle allocation ni un transfert de sa cible.

Le contrôle des emprunts tient compte des accès futurs au porteur et des
arguments préparés. Une référence initialisée dans un champ est protégée pendant
l'évaluation des champs suivants, comme un argument déjà préparé. Un appel dans
un initialiseur suivant ne peut donc déplacer ou réinitialiser sa cible.

Les contraintes des paramètres incluent un symbole `allocation_field_parameter`
avec chemin de champ et indice du paramètre. Un corps qui reset une source puis
lit un champ produit la distinction nécessaire entre cette source et celle du
champ. Un wrapper substitue ces chemins. À l'appel, toutes les sources des cibles
possibles doivent satisfaire l'obligation. Le vérificateur n'ouvre pas le corps
du callee : le test opaque retire explicitement ce catalogue.

Une variante connue vide ne porte aucune dépendance. Le vérificateur conserve
les variantes possibles des constructeurs, moves et if. Il vérifie les types
dans les bras impossibles d'un match sans inventer une cible vivante ; ces bras
C restent inaccessibles tant que les variantes ne changent pas en place, comme
l'impose le sous-ensemble actuel.

La destruction du porteur ne détruit pas ses cibles. Après son dernier usage,
les cibles peuvent être détruites avant le nettoyage automatique du porteur :
le destructeur démonstratif actuel affiche le nom de variante sans lire les
champs. Les dépendances de destructeurs utilisateur restent hors périmètre.

La décision conservative concernant les appels divergents reste inchangée :
tout reset possible protège les usages futurs, même si le chemin qui reset
ne revient jamais. Une régression dédiée conserve le refus validé par l'utilisateur.

## Traduction en C

Un champ &Int stocke un `Cell *` dans le payload du slot ; aucun handle ni
allocation runtime supplémentaire n'est ajouté. La taille et les offsets des
champs utilisent `sizeof(int)` et `sizeof(Cell *)`. Les métadonnées de chaque
stack de variante contiennent les offsets et catégories des champs.

Les accès aux champs utilisent `memcpy` : un pointeur placé après un Int peut
être non aligné, et aucun cast vers un `Cell **` non aligné n'est utilisé. Les
slots restent alignés et les bras gardent des tailles propres. Le runtime oracle
historique, qui utilise des payloads uniquement Int, conserve sa représentation.

`cell_print` lit les cibles Int uniquement lors d'un usage validé du porteur.
Le nettoyage d'un porteur expiré ne déréférence pas ses champs. Une adresse de
slot réutilisée ne réactive ni l'identité de l'ancien objet ni ses emprunts.

## Validation exécutée et limites

Les [tests ciblés](../tests/test_reference_fields.py) comprennent 27 méthodes,
avec appels, champs mixtes, masquage de variantes, reset, réaffectation,
transferts bornés, arguments, boucle et réutilisation. Le modèle indépendant
énumère 32 scénarios, graines 0–31, avec trois cibles, deux champs et opérations
drop/mutation/reset avant ou après le prochain usage du porteur : 19 programmes
attendus valides et 13 attendus invalides. Il ne lit pas les décisions du
vérificateur pour déterminer ces attentes. Un décompte initial erroné 18/14 dans
le harnais a été corrigé en 19/13 ; les attentes de chacun des 32 programmes
n'ont pas été modifiées.

Commandes supplémentaires :

```sh
python3 tests/run_reference_field_mutations.py --output validation/reference-field-mutations.json
python3 tests/validate_reference_field_c.py --output validation/reference-field-c.json
```

La campagne de mutations injecte quatre fautes en copies temporaires : table de
dépendances omise, source de champ absente du contrat, emprunt préparé omis et
offsets de pointeurs incorrects. Un premier contrôle d'empreintes a été perturbé
par l'ajout concurrent du script C au projet ; il a été relancé sur un ensemble
de fichiers stable. Le résultat final est dans le
[rapport de mutations](../validation/reference-field-mutations.json), sans taux de
détection global extrapolé de cet échantillon.

La campagne C comporte trois programmes × O0/O2/Os/O2-UBSan : huit exécutions
normales et quatre arrêts attendus pour capacité dépassée. Les valeurs,
adresses et destructions sont spécifiées dans le harnais, indépendamment du
compilateur. Le [rapport C](../validation/reference-field-c.json) conserve les
résultats. Une seule famille C est disponible, Clang ; ASan reste indisponible
sur cet hôte selon les essais antérieurs. Les contrôles UBSan ne prouvent pas
la sûreté de tous les chemins.

La [matrice des règles](VERIFICATION_MATRIX.md) est mise à jour. Les graphes
transitifs, collections, mutations de variantes et
destructeurs utilisateur restent non vérifiés. Le modèle est un modèle de
frontière de dépendances simple, pas un oracle général des emprunts.

## Résultat des suites complètes

Les deux suites complètes ont terminé sans échec :

| Commande | Résultat exécuté |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 572 tests, OK, 386,082 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 572 tests, OK, 385,870 s |

Les modèles de nettoyage, de routes de types de pools et l'oracle runtime
existants sont inclus dans ces deux exécutions. Les 27 nouvelles méthodes et
le modèle de 32 scénarios le sont également. Les quatre mutations ont été
détectées lors de la relance ; les empreintes avant/après y sont identiques.
Les douze exécutions C optimisées sont une campagne distincte terminée sans
écart aux attentes. Il ne reste aucun échec ouvert de ce cycle.

Les [résultats structurés](../validation/reference-field-suites.json) conservent
les commandes, durées et limites d'instrumentation. Le nombre total de programmes
admis/refusés par toutes les sous-variantes de la suite n'est pas agrégé ; les
comptes 19/13 concernent exclusivement le modèle de frontière des champs.
Aucune preuve formelle ni validation générale de tous les graphes n'est revendiquée.
