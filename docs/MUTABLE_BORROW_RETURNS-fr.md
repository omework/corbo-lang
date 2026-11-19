[English](MUTABLE_BORROW_RETURNS.md)

# Retours d'emprunts mutables : exclusivité et durabilité

Extension ultérieure : les [champs &mut Int](MUTABLE_REFERENCE_FIELDS.md) sont maintenant disponibles ; les mesures ci-dessous décrivent ce cycle historique.

Cycle du 2 novembre 2026, validé par l'utilisateur avec l'écriture `let mut vue`.
Règles B5/B1–B3/D1/D3 dans [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
[matrice des 66 règles](VERIFICATION_MATRIX.md) et
[guidelines de validation](VALIDATION_GUIDELINES.md).

## Comportement

```rust
fn borrow_mut(data: &mut Int) -> &mut Int {
    return data;
}

let mut memory = pool<Int>(1);
let mut nombre = new(memory) Int(10);
let mut vue = borrow_mut(&mut nombre);
vue.set(30);
nombre = 40; // Après le dernier usage de vue.
```

Le résultat utilise la même allocation, à la même adresse. Aucun nouvel objet
ou emplacement, transfert de rattachement, réception ou destructeur n'est
associé au retour de cet emprunt. La syntaxe ne rajoute pas de & à la référence
reçue. Le [programme complet](../examples/mutable_borrow_returns.crb) montre les
adresses, un relais, la reprise du nom d'origine et le drop/reset.

Avant le dernier usage de vue, accéder à nombre directement, le modifier, le
déplacer, le drop ou reset son pool est refusé. Le nom de la référence peut
être mutable comme demandé dans l'exemple ; sa capacité d'écriture provient
cependant du type &mut Int, selon la distinction déjà retenue avec let mut.
Une entrée &Int, même déclarée mut, ne peut fournir un résultat &mut Int.

Un réemprunt enfant autorisé peut suspendre le parent. Un enfant mutable garde
l'exclusivité ; un enfant partagé suspend les écritures incompatibles du parent.
Les chaînes sont conservées dans les relais et les appels imbriqués, même sans
variable intermédiaire. Après le dernier usage de l'enfant, le parent reprend
ses accès sous réserve des autres emprunts. Deux arguments mutables qui peuvent
viser la même allocation ne peuvent pas être préparés ensemble.

Un résultat conditionnel retient toutes ses cibles possibles. Chacune doit déjà
être vivante et rattachée au scope parent ou à un ancêtre à chaque frontière.
Leurs capacités exclusives et leurs sources sont protégées, même si le chemin
concret ne choisit qu'un candidat. Un objet local ou reçu par transfert ne
s'échappe pas par emprunt, même si son pool survit. Aucun déplacement de bytes
ou promotion implicite n'est ajouté.

## Analyse et traduction C

Le parseur, les résultats symboliques et les contrats distinguent désormais
`mode: mut` d'un résultat partagé. Les identités `reference_targets` sont
substituées à travers les appels. L'inférence exige des provenances depuis des
paramètres &mut Int ; le vérificateur opaque refuse également un contrat forgé
qui promettrait un résultat mutable depuis un paramètre partagé.

Le C reste un retour de `Cell *` vers le slot existant. Les descripteurs de
référence sont purement statiques et ne sont pas enregistrés comme allocations
ou responsabilités de nettoyage. Les résultats mutables peuvent être fournis
directement aux paramètres compatibles par une expression d'appel ; un & ajouté
à une référence reste une référence imbriquée non supportée, sans aplatissement.
Un résultat mutable peut être restreint à la lecture par une signature &Int.

Le calcul des prêts recense un binding une seule fois pour chaque cible possible.
Il conserve son mode sur les cibles secondaires et suit les parents dans les
réemprunts partagés comme exclusifs. Cette distinction évite à la fois de compter
un alias deux fois et de réduire implicitement un prêt exclusif secondaire à un
prêt partagé. Un résultat utilisé directement en argument participe aussi à la
suspension de ses parents alors qu'il n'a pas encore de nom dans le scope.
Les arguments déjà préparés restent protecteurs pendant l'évaluation suivante.
Le runtime, le layout des slots et les pointeurs de nettoyage sont inchangés.

## Écart confirmé corrigé pendant le cycle

Le contrôle de dernier usage traitait encore toute affectation d'un nom comme
un remplacement, malgré la mutation de contenu introduite au cycle précédent :

```rust
fn make(memory: &mut Pool<Int>) -> <- Int {
    let data = new(memory) Int(10);
    return <- data;
}

let mut memory = pool<Int>(1);
let mut nombre = make(&mut memory);
nombre = 20;
```

Ce programme était refusé à tort comme résultat reçu sans usage explicite.
Une écriture de contenu utilise pourtant l'objet et ne remplace pas le binding.
L'analyse distingue maintenant ce cas depuis le mode du binding et le type de
RHS déjà disponible dans la signature/contrat, sans ouvrir un corps de fonction.
Elle continue au-delà de ces écritures pour suivre les usages suivants.
Les remplacements et réaffectations de références restent des fins du binding
précédent. La régression couvre RHS littéral et résultat scalaire de fonction,
la destruction unique avec le contenu 20 et un emprunt mutable futur qui doit
continuer de faire refuser cette écriture. Aucune règle n'a été relâchée pour
faire passer ce programme ; le suivi a été aligné sur V4/U1 déjà retenues.

## Validation exécutée

Le cycle précédent avait 672 méthodes réussies dans chaque configuration.
Les 28 nouvelles méthodes passent leurs contrôles ciblés. Le comptage du
[nouveau corpus](../validation/mutable-return-fixtures.json) recense **28 programmes
distincts admis et exécutés**, et **58 programmes distincts refusés** à la fois
par `verify_program` et `compile_source`. Des tests supplémentaires contrôlent
les résumés sans backend, les contrats opaques et un contrat volontairement faux.
Ces comptes concernent ce corpus, pas tous les programmes des suites globales.

Le modèle indépendant utilise 24 graines (0–23), des ensembles d'indices de
feuilles, des permutations de paramètres, des unions et 1–4 relais. Il ne lit
pas les décisions ni les résumés du compilateur. Il impose **12 programmes
valides exécutés et 12 invalides refusés**, puis compare les valeurs modifiées
sur le chemin concret. Les tests fixes couvrent en plus parents successifs,
enfants partagés, champs &Int, appels imbriqués, arguments préparés, mode let /
let mut, cibles locales, drop/reset, slot réutilisé, boucles/continue, historique
de source et return anticipé annulant l'appel et libérant ses prêts préparés.

Cinq fautes sélectionnées sont détectées dans des copies temporaires : résultat
opaque rétrogradé en lecture, prêt secondaire rétrogradé en lecture, perte d'un
parent mutable, acceptation d'un contrat mutable depuis un paramètre partagé,
et fin erronée du binding sur une écriture de contenu. Les tests de lecture
interdite utilisent une lecture ultérieure du résultat, sans compter sur une
mutation qui ferait simplement échouer son type. Ils vérifient donc la
protection exclusive, même lorsque les opérations C elles-mêmes seraient des
lectures valides. Aucun taux global de détection n'est déduit.

Les 24 fautes des cycles précédents sont rejouées. Le point d'injection de
l'omission des cibles du résultat direct était initialement devenu inapplicable
avec l'expression désormais commune aux modes ref et mut : la campagne s'est
arrêtée avant injection. L'[incident](../validation/mutable-return-initial-mutation-anchor.json)
est conservé. Le point a été adapté, sans changer la faute ou son assertion,
puis les campagnes ont été relancées avec des empreintes cohérentes. Les
résultats terminés sont référencés ci-dessous ; un statut d'injection inapplicable
n'est pas compté comme une détection.

Cinq campagnes C (retours mutables, contenu, retours partagés, porteurs et pools)
ont chacune trois programmes en O0, O2, Os et O2+UBSan : **60 exécutions conformes**.
Elles comparent valeurs, adresses, destructions, resets, réutilisation et échecs
de capacité. La fin d'un prêt ne libère pas prématurément l'allocation : le cas
d'épuisement garde le premier slot vivant et s'arrête sans dérouler les
destructeurs. Les configurations instrumentées s'arrêtent au premier diagnostic
UBSan ; aucun n'est émis. Une seule famille C est disponible. L'exemple CLI est
aussi exécuté, sans instrumentation implicite par CRUST_SANITIZE.

Rapports : [mutations nouvelles](../validation/mutable-return-mutations.json),
[let](../validation/mutable-return-let-mutations.json),
[valeurs de référence](../validation/mutable-return-value-mutations.json),
[retours partagés](../validation/mutable-return-direct-mutations.json),
[porteurs](../validation/mutable-return-holder-mutations.json),
[champs](../validation/mutable-return-field-mutations.json),
[C mutable](../validation/mutable-return-c.json),
[C contenu](../validation/mutable-return-content-c.json),
[C partagé](../validation/mutable-return-direct-c.json),
[C porteurs](../validation/mutable-return-holder-c.json),
[C pools](../validation/mutable-return-pool-c.json).
Les suites globales sont terminées : **700 tests standard réussis
(461.15 s)** et **700 sous UBSan (460.252 s)**,
sans saut ni échec non résolu. Les modèles et oracles précédents font partie de
ces exécutions. Les **29 mutations sélectionnées sont détectées** ; leurs
empreintes correspondent au Python final du projet. Le
[bilan brut](../validation/mutable-return-suites.json) conserve commandes, sorties,
durées, configurations et empreintes. La réparation du point d'injection ne
modifiait ni le compilateur ni les méthodes de test des suites en cours.

## Limites

Retours &mut Int seulement, sans référence imbriquée, projection de champ
mutable, champ &mut stocké, graphe transitif, destructeur utilisateur, récursion,
async ou FFI. Le modèle de cibles est borné et ne formalise pas tous les prêts.
L'inférence, le vérificateur et le backend restent dans la base de confiance.
ASan n'est pas relancé : son échec antérieur sur cet hôte se produisait aussi
avec un programme C vide. Les configurations d'une même famille ne remplacent
pas un compilateur indépendant. Le lanceur CLI n'est pas instrumenté par la
seule variable CRUST_SANITIZE ; voir [SAFETY.md](SAFETY.md).
Aucune preuve générale de sûreté n'est revendiquée.
