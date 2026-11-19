[English](TYPE_FEATURES_CYCLE.md)

# Cycle — Résolution statique des type features

## Règles intégrées et architecture

Le brouillon 06 est intégré sous les identifiants TF1–TF5 dans
[TYPE_FEATURES.md](../TYPE_FEATURES.md), avec renvois depuis I5/B4/B5 et
ME1/ME2/ME4. Les directives ont leur cycle séparé.

Le parseur reconnaît une feature contenant exactement une méthode, avec
receveur `&self`, `&mut self` ou `-> self`. La résolution dans
`type_features.py` intervient avant l’inférence des effets, des résultats et
des contraintes. Elle produit des fonctions aux signatures concrètes ; il
n’y a pas de table de dispatch dynamique ajoutée au C.

Deux vérifications restent distinctes :

- Le corps contraint est parcouru avec ses seules garanties déclarées, même
  sans appel. Une méthode supplémentaire du type concret ne justifie pas
  une exigence directe ou indirecte absente de la signature.
- Chaque spécialisation concrète passe ensuite par les vérificateurs de
  contrats, emprunts, transferts, origines et nettoyage existants. Le résultat
  d’une feature peut ainsi rester un `&Console`, un `&mut Counter` ou un
  propriétaire `Item`, sans effacement de sa source de stockage.

Le cache distingue les types concrets des arguments. Les paramètres d’une
même feature peuvent donc être résolus indépendamment. La vérification des
signatures inclut les modes, les arguments, le résultat et les marqueurs de
handles ; les noms de paramètres et la mutabilité de leur liaison locale
ne sont pas des exigences ajoutées à la feature.

## Contre-exemples et frontières examinés

- Méthode supplémentaire appelée directement, par alias, dans une branche
  fausse ou une expression conditionnelle : refus avant spécialisation.
- Relais vers une autre feature non garantie : refus même lorsque le type
  concret possède par ailleurs la méthode supplémentaire.
- Deux features de noms différents mais de même exigence : relais admis.
- Mauvais mode de receveur, d’argument ou de résultat, méthode absente : refus.
  L’exigence reste obligatoire si le corps ne l’utilise pas.
- Feature utilisée pour un champ, un pool, une collection ou une annotation
  locale de stockage : refus. Paramètres dupliqués, absence de receveur,
  feature vide/multiple, `main` contraint : refus.
- Emprunt mutable retourné : accès direct à la cible refusé avant son dernier
  usage et admis après. Emprunt de champ retourné par deux relais : son
  allocation cible reste protégée contre `drop`.
- Consommation d’une allocation de pool par méthode : nettoyage unique,
  ancien accès invalide, slot réutilisé à la même adresse.
- Retour propriétaire à travers deux fonctions : adresse et pool conservés ;
  transfert depuis un pool trop court refusé.
- Effet de reset d’une méthode propagé par deux relais, dans le profil
  historique explicitement activé : usage ultérieur refusé ; reset après
  lecture admis, nettoyage unique. Le reset public reste retiré du prototype.
- Retours conditionnels d’une feature : un type concret commun est requis.
  Deux paramètres de types différents peuvent être utilisés ensemble, mais
  ne deviennent pas un résultat unique de type effacé.

Une erreur de la nouvelle analyse a été corrigée avant clôture : le type
`None` d’un `break;` d’une boucle statement était ajouté aux candidats du
résultat de la fonction. `test_statement_loop_break_does_not_become_a_function_result`
préserve désormais le programme minimal admis avec une boucle puis `return t`.
Les breaks d’une expression boucle restent traités comme ses propres résultats.

Des fixtures initiales employaient des formes absentes de la grammaire actuelle
(`p.new(Item{...})`, `new(p) Item{...}`, emprunt de structure fourni directement
par un bloc/if). Elles ont été remplacées par `p.new(value:...)` et par des
receveurs explicites. Ces corrections n’établissent pas un support des formes
écartées. Un relais propriétaire conserve aussi un receveur avant `return <-`.

## Preuves exécutées

`tests/test_type_features.py` contient 16 méthodes. Sur l’état final :

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest test_type_features -v` :
  réussite en 8,868 s ; `/tmp/crust-features-O0-final.log`.
- À O2, même suite exécutée par `/tmp/crust_features_counted.py` : réussite en
  12,342 s ; `/tmp/crust-features-O2-final.log`.
- Le compteur O2 relève 21 compilations/exécutions natives et 115 programmes
  refusés. Une compilation supplémentaire de l’exemple inspecte directement
  le catalogue concret et ses contrats, sans exécution native supplémentaire.
- Les programmes C utilisent `-std=c11 -fsanitize=undefined
  -fno-sanitize-recover=all` aux deux niveaux d’optimisation.
- Le modèle indépendant des signatures compare des capacités exprimées dans
  le source, sans appeler le normaliseur de signatures du compilateur :
  81 combinaisons cartésiennes, 9 admises/exécutées et 72 refusées. Il est inclus
  dans les nombres ci-dessus, sans aléatoire.
- `/tmp/crust_features_regression.py` : 173 méthodes réussies en 50,543 s,
  `/tmp/crust-features-regression.log`. Contrats opaques, corps de fonctions,
  exigences de pools, emprunts retournés, directives, méthodes et structures
  locales. `CRUST_SANITIZE=undefined` active UBSan fatal dans les helpers
  historiques ; le helper Foundation utilise déjà O2/UBSan fatal.
- `/tmp/crust_features_interactions.py` : 36 méthodes réussies en 23,231 s,
  `/tmp/crust-features-interactions.log`. Le script injecte une feature et un
  relais générique non appelé dans les tests de méthodes/structures locales,
  puis conserve les assertions originales. Cela exerce aussi le nouveau
  parcours sur des corps concrets complexes qui ne font pas appel à la feature.
- Compilation Python de `crust.py`, `type_features.py` et du nouveau module de
  tests réussie.

Les nombres de méthodes de régression ne sont pas des nombres de programmes.
Les 36 tests injectés recouvrent une partie des 173 précédents ; les compter
comme 209 propriétés indépendantes serait incorrect.

## Mutations exécutées

`/tmp/crust_feature_mutations.py` modifie des copies temporaires du module de
résolution ; les tests et leurs attentes restent ceux du dépôt. Journal :
`/tmp/crust-feature-mutations.log`.

1. Suppression de la vérification abstraite : détectée, huit configurations
   interdites acceptées à tort.
2. Omission du résultat dans la comparaison des signatures : détectée.
   Le cas dont le corps n’appelle pas la méthode est accepté à tort ; un autre
   cas est refusé plus tard par U1 avec un diagnostic différent.
3. Fusion des spécialisations d’arguments de types différents : détectée par
   le rejet incorrect d’un programme admis (Journal confondu avec Console).
4. Omission d’une exigence indirecte lorsque l’argument est encore abstrait :
   détectée par l’acceptation incorrecte d’un relais exigeant `flush`.

Ces quatre fautes ne constituent ni une couverture exhaustive des mutations,
ni une mesure générale de sûreté. Les modèles et les tests ne prouvent pas la
correction de toutes les inférences de types ou de durées de vie.

## Écarts restants — lot non terminé

Mise à jour : le contre-exemple builtin ci-dessous est désormais corrigé et
testé dans [BUILTIN_FEATURES_CYCLE.md](BUILTIN_FEATURES_CYCLE.md). Le passage
suivant conserve le constat historique de ce premier cycle.

Le catalogue résolu couvre les méthodes de structures déclarées dans le
programme. Les méthodes builtin n’y figurent pas encore. Contre-exemple admis
par l’intention structurelle, encore refusé à l’exécution du vérificateur :

```rust
type feature Compter { fn len(&self) -> Int; }
fn count(v: &Compter) -> Int { return v.len(); }
fn main() {
    let mut p = pool<Vector<Int>>(1);
    let v = p.new();
    print(count(&v));
}
```

Diagnostic observé : `type 'Vector<Int>' : exigence de feature 'Compter' non
garantie`. Il faut intégrer les signatures/contrats builtin, sans neutraliser
leurs effets ni leur suivi d’emprunts.

Restent aussi à éprouver et compléter les signatures de méthodes déclarant
elles-mêmes d’autres features, les projections plus générales et l’interaction
avec les états async. La récursion reste refusée par le prototype. Le parcours
abstrait contrôle les garanties, mais ne remplace pas une preuve universelle
sur toutes les instanciations possibles : les contrôles mémoire s’exécutent sur
les instanciations concrètes effectivement produites.

Aucun nouveau passage ASan/TSan, aucune preuve formelle, aucune couverture
générale du multithread n’est revendiquée. Le lot 06 et l’objectif global restent
ouverts ; les écarts de stockage et le brouillon 04 demeurent dans leur périmètre.
