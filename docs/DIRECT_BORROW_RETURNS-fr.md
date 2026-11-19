[English](DIRECT_BORROW_RETURNS.md)

# Retours directs d'emprunts &Int

Extension ultérieure : les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) sont
maintenant disponibles. Les restrictions et mesures ci-dessous décrivent le
périmètre du cycle historique, dont les sources brutes et empreintes sont conservées.

Cycle du 2 novembre 2026, demandé par l'utilisateur. Références :
[guidelines de validation](VALIDATION_GUIDELINES.md), règles B5/D1/B1–B3/A5 et
[matrice des 66 règles](VERIFICATION_MATRIX.md). Ce cycle implémente B5 dans
un sous-ensemble en lecture ; il n'autorise aucune promotion implicite.

Les exemples ont été mis à jour pour la [règle des valeurs de référence](REFERENCE_VALUES.md) :
`return data`, `borrow(data)` depuis un paramètre emprunté. Les rapports bruts
de ce cycle conservent l'ancien état de syntaxe et leurs empreintes ; la nouvelle
validation est consignée séparément. Aucun `&` sur une référence n'est désormais
aplati en référence vers sa cible.

## Comportement et frontières

```rust
fn borrow(data: &Int) -> &Int {
    return data;
}

fn relay(data: &Int) -> &Int {
    let mut view = borrow(data);
    return view;
}

let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
let mut view = relay(&data);
print(view);
drop(-> data); // Autorisé après le dernier usage de view.
```

Un retour ne crée pas d'allocation, n'utilise pas `<-`, ne reçoit pas la cible
dans un nouvel ordre de destruction et ne modifie ni son adresse ni sa source.
Les usages futurs du résultat protègent la cible. Placer le drop avant le print
fait refuser le programme ; il en va de même d'un reset, déplacement ou accès
mutable incompatible. Après la dernière lecture, drop/reset et réutilisation
du slot sont autorisés, sans réactiver l'ancien accès.

À chaque frontière quittée, toutes les cibles doivent être vivantes, certaines
et rattachées au parent ou à un ancêtre. Ce contrôle s'applique aussi aux blocs
imbriqués et aux appels successifs. Un pool durable ne rend pas ses allocations
locales exportables par emprunt :

```rust
fn wrong(memory: &mut Pool<Int>) -> &Int {
    let mut local = new(memory) Int(42);
    let mut view = borrow(&local); // Retour valide vers le scope de wrong.
    return view;             // Refusé à la frontière suivante.
}
```

Une allocation Int injectée par `->` descend dans la fonction et ne peut pas
en sortir par emprunt. Une entrée `&mut Int` peut donner un résultat partagé,
qui reste en lecture. Son parent mutable ne reprend ses accès incompatibles
qu'après le dernier usage du résultat. Les contrôles d'accès depuis le nom
d'origine restent actifs durant cette suspension.

Les retours conditionnels réunissent toutes les cibles possibles, même avec
une condition littérale ou plusieurs cibles dans le même pool. Un reset d'un
seul pool possible est donc interdit avant un usage futur du résultat. Les
références peuvent être passées aux appels suivants ou stockées dans les champs
&Int déjà disponibles : les alternatives et les parents mutables suivent ces
opérations. Aucune analyse dépendante de la valeur du prédicat n'est ajoutée.

## Contrats et traduction C

`results.py` infère `reference_targets`, ensemble d'identités de paramètres
empruntés. Les relais substituent les paramètres, sans annotation de provenance.
L'inférence seule refuse les cibles locales et les paramètres Int transférés,
même dans une fonction inutilisée. `constraints.py` conserve l'historique des
cibles déjà existantes : un résultat emprunté ne constitue pas une nouvelle
allocation qui ferait oublier un reset antérieur.

Le vérificateur applique le contrat opaque sans ouvrir le corps appelé. Un
descripteur statique rassemble toutes les cibles possibles ; il n'est inscrit
ni dans le registre d'allocations réelles, ni dans une liste de nettoyage.
Les emprunts actifs et les arguments déjà préparés protègent l'ensemble de
ces cibles. Les constructeurs de porteurs &Int conservent également cet ensemble.
Le backend spécialisé vérifie que les cibles observées respectent le contrat.
Un test avec contrat volontairement faux contrôle ce dernier garde-fou.

Le C utilise le pointeur `Cell *` existant, sans handle, compteur de références
ou allocation supplémentaire. Le résultat est un pointeur vers le slot Int,
et non vers la variable de paramètre C. Le pointeur de nettoyage de l'allocation
d'origine reste séparé du descripteur du résultat. Le runtime de pool et le
format des slots n'ont pas changé.

## Validation exécutée

Les 27 nouvelles méthodes de test incluent des couples admis/refusés et des
sous-cas : contrats sans appel, cibles locales et reçues par transfert, parent et
ancêtres, relais, retours conditionnels, réemprunts de parents mutables, aliases
dans les arguments, champs &Int, historique de reset, réaffectation de référence,
boucle avec continue, adresse et destruction unique, réutilisation de slot.
Le test opaque retire le corps et interdit une entrée de bloc lors de l'appel.

Le modèle indépendant de cibles utilise 24 graines (0–23), des permutations de
paramètres, des unions de cibles et 1–4 relais. Son oracle calcule les ensembles
d'indices depuis la construction du graphe, sans lire les contrats inférés.
Il exige 12 programmes admis et 12 refusés ; les admis sont également exécutés
et leurs valeurs comparées à la sélection du chemin concret. Ce modèle ne
modélise pas l'ensemble du vérificateur ou tous les historiques d'emprunts.

Cinq mutations choisies sont détectées dans des copies temporaires : omission
des cibles du contrat, acceptation d'une cible locale par l'inférence, perte des
alternatives de l'alias, perte des parents mutables et rejet erroné d'une cible
ancêtre valide. Les quatre mutations des champs et les cinq des retours de
porteurs sont rejouées et détectées. Les points d'injection de deux anciennes
mutations ont été adaptés au code conservant les alternatives ; leurs assertions
n'ont pas été affaiblies. Les empreintes Python du projet sont inchangées par
les trois campagnes. Aucun taux global de détection n'en est déduit.

Trois programmes C fixes (relais/sélection/réutilisation, parent mutable,
épuisement) sont exécutés chacun en O0, O2, Os et O2+UBSan : douze observations
conformes, dont huit sorties normales et quatre arrêts attendus sur capacité.
Les assertions comparent adresses, valeurs, ordre/nombre de destructions et
diagnostic d'épuisement. UBSan arrête au premier diagnostic ; aucun n'est émis.
L'exemple [direct_borrow_returns.crb](../examples/direct_borrow_returns.crb)
est également exécuté par le lanceur CLI.

Rapports bruts : [C](../validation/direct-borrow-c.json),
[mutations directes](../validation/direct-borrow-mutations.json),
[régression mutations champs](../validation/direct-borrow-field-regression-mutations.json),
[régression mutations porteurs](../validation/direct-borrow-holder-regression-mutations.json).
Suite globale standard : **632 tests réussis en 417,129 s**.
Suite globale avec `CRUST_SANITIZE=undefined` : **632 tests réussis en 416,912 s**.
Les 27 nouvelles méthodes s'ajoutent aux 605 du cycle précédent. Les modèles
existants de nettoyage, provenance, exigences de pools, champs et oracle runtime
font partie de ces exécutions. Les noms et contrats des tests précédents sont
conservés ; aucun échec n'est laissé non résolu. Le comptage 12/12 ci-dessus
concerne les programmes générés nouveaux, et non l'ensemble des fixtures des
632 méthodes (qui ont leurs propres sous-cas).

Le [bilan brut des suites](../validation/direct-borrow-suites.json) conserve les
commandes, sorties, durées, graines et empreintes Python. Un cas complémentaire
[de temporaire chez l'appelant](../validation/direct-borrow-temporary.json) a été
exécuté sous UBSan : lecture de la référence, reset, puis nouvel objet dans le
pool de capacité un, avec deux destructions exactement. Aucune divergence de
règle non résolue n'est identifiée dans ce périmètre testé.

La mise au point initiale a corrigé des fixtures du harnais : réaffectation de
scalaire parent non prise en charge dans une boucle, receveur inutilisé après
réécriture d'un scénario et appel interne non indexé dans le test opaque.
Ces corrections n'ont pas modifié les règles du langage.

## Limites

Retours `&Int` uniquement, en lecture, avec `return` explicite. Les retours
`&mut`, vers d'autres types, les références aux scalaires locaux et le retour
d'un champ extrait dans un bras de match restent hors du prototype. Les
expressions if qui produisent une référence et les réemprunts stockés généraux
ne sont pas ajoutés. Un résultat d'appel &Int peut toutefois être reçu puis
réemprunté lors d'un autre appel, retour ou constructeur de champ &Int.

L'inférence, l'application de contrats et les vérifications spécialisées restent
dans la base de confiance ; ce ne sont pas trois modèles indépendants. Les
modèles existants de nettoyage et du runtime sont réexécutés par les suites
globales. Le placement général, graphes transitifs, destructeurs utilisateur,
récursion, threads, async et frontière C externe restent hors périmètre.
ASan n'est pas relancé : les essais antérieurs de ce poste échouent même avec
un programme C vide. Une seule famille C est disponible (Clang ; le nom gcc
local pointe également vers Clang). UBSan instrumente les binaires construits
par le harnais et les oracles ; les binaires CLI ne sont pas instrumentés par
la seule variable `CRUST_SANITIZE`. Voir [SAFETY.md](SAFETY.md).
Ces contrôles bornés ne constituent pas une preuve de sûreté générale.
