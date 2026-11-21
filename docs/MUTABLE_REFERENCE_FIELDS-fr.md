[English](MUTABLE_REFERENCE_FIELDS.md)

# Champs contenant un emprunt mutable

**Actualisation des emprunts mutables :** [MA1–MA6](MUTABLE_ACCESS-fr.md)
remplace l’exclusivité déduite du seul `&mut`. Les exemples et verdicts d’exclusion
rapportés dans les anciens cycles ci-dessous sont historiques ; ils ne définissent
pas la compatibilité actuelle des accès. Permissions, validité, synchronisation
et fins de branche se vérifient séparément.


Cycle du 3 novembre 2026, après validation explicite de la règle. Procédure :
[guidelines](VALIDATION_GUIDELINES.md), [règles](LANGUAGE_RULES.md),
[matrice](VERIFICATION_MATRIX.md).

## Règle et périmètre

```rust
enum Writer { Bound { data: &mut Int } }

fn make(writers: &mut Pool<Writer>, data: &mut Int) -> <- Writer {
    let writer = new(writers) Writer.Bound { data: data };
    return <- writer;
}
```

Le constructeur reçoit `&mut nombre` depuis une allocation mutable, ou le nom
d'un emprunt mutable existant. Une entrée `&Int` ne fournit pas cette capacité.
Le champ est initialisé entièrement, sans référence imbriquée ni conversion
silencieuse. L'objet conserve l'exclusivité sur chaque cible possible jusqu'à
son dernier usage, y compris les usages via une référence à cet objet. Pendant
cet intervalle, lire la cible par son accès d'origine, la modifier, la déplacer,
la détruire ou reset son pool est refusé. Les restrictions parentales et les
provenances passent dans les contrats de retours et les transferts successifs.
Chaque cible doit déjà vivre dans le parent ou un ancêtre à chaque frontière ;
aucune promotion implicite n'est ajoutée.

Plusieurs références partagées vers le même objet retiennent une seule capacité
de champ. Elles ne créent pas des emprunts mutables distincts. Un `match &writer`
projette le champ en lecture, avec une filiation vers cette capacité ; cette
projection ne rend pas l'accès d'origine à la cible disponible. La projection
mutable et la réaffectation de champs ne sont pas implémentées à cette étape.

Après le dernier usage protecteur, l'accès d'origine ou le réemprunt parent
redevient disponible selon ses propres droits. Cela ne détruit pas l'objet
porteur. Un `drop` explicite du porteur compte comme usage ; son destructeur
implicite démonstratif ne lit pas le champ et ne prolonge pas cet emprunt.
Des destructeurs utilisateur lisant leurs références exigeraient le contrôle
supplémentaire prévu par L4 et restent hors du prototype.

## Vérificateur, contrats et C

Les déclarations de champs distinguent les modes partagé et exclusif. Les
contrats infèrent les identités des cibles et les substituent aux appels, en
conservant la capacité exigée par chaque champ. Un champ retourné mutable doit
provenir d'un paramètre mutable ou d'un champ déjà mutable. Les alternatives
conditionnelles retiennent toutes les cibles et la restriction la plus forte
pour chacune. Les appels opaques continuent à être vérifiés sans lire les corps.
Le backend C reste spécialisé et garde ses contrôles de cohérence.

Le calcul des prêts regroupe les aliases d'un même porteur par identité
d'allocation. Les lectures projetées sont des enfants de cette capacité ; la
filiation conserve les interdictions d'accès par les noms d'origine. Les
arguments et les champs déjà préparés restent protecteurs pendant l'évaluation
des expressions suivantes, de gauche à droite.

Les deux types de référence sont représentés par `Cell *` en C, chargés et
stockés via `memcpy`. Le calcul de taille et d'offset considère bien &mut Int
comme un pointeur, y compris entre des champs Int. Il n'y a aucun nouveau
contrôle dynamique d'emprunt : la distinction de capacité est statique.
Le runtime des pools et l'ordre de destruction restent inchangés.

## Réexamen global

Les 66 règles existantes ont été réexaminées par familles :

- I1–I5/V1–V5 : intention explicite, initialisation, absence de copie
  d'allocation, mutabilité des accès et identité stable.
- S1–S6/T1–T11/U1 : activations enfant → parent, transferts successifs,
  retours conditionnels, réceptions, boucles/continue et usage des résultats.
- D1–D4/B1–B5/B4a–e : cibles durables sans promotion, ensembles de cibles,
  exclusivité, dernier usage, arguments préparés, types et contrats opaques.
- L1–L7/A1–A6/P8/P9/E1 : destructeur avant libération, ordre global de
  nettoyage, drop/reset, provenance, réutilisation et épuisement des pools.
- P1–P7/E2 et les parties futures des autres règles : aucune implémentation
  nouvelle de placement anticipé, croissance dynamique, plages à deux curseurs,
  macros, tableaux, récursion, concurrence ou FFI sûre.

Les interactions nouvelles exercées portent sur les aliases du porteur,
projections partagées, réemprunts mutables parents, retours et relais, variantes
conditionnelles, transferts imbriqués, drop/reset des deux pools, remplacement,
arguments et initialisateurs à effets, reprise de boucle et slots réutilisés.
Les tests précédents restent applicables aux backends de compatibilité.

## Contre-exemple confirmé et correction

L'audit a trouvé un écart entre le type réel et un descripteur de capacité.
Le descripteur nouvellement utilisé pour emprunter un porteur de champ mutable
héritait du type Int par défaut. Ce programme était alors accepté :

```rust
enum W { Bound { data: &mut Int } }
// p: Pool<Int>, q: Pool<W>, n: allocation Int mutable.
let mut w = new(q) W.Bound { data: &mut n };
let x = new(q) W.Bound { data: &mut w }; // Doit être refusé : w est W.
print(x);
```

La référence avait bien pour cible w, mais le contrôle de type du champ voyait
Int. Le descripteur conserve désormais le type de sa cible réelle. Les tests
de refus couvrent &mut W vers &mut Int et &W vers &Int ; une mutation qui efface
cette correction fait partie de la campagne dédiée. Aucun changement de règle
n'a été nécessaire : V2, B4 et P9 imposaient déjà cette distinction.
Les campagnes lancées avant cette correction ne sont pas les résultats finaux.

## Validation exécutée

La suite dédiée comporte **29 tests**. Son corpus enregistré contient **24
sources distinctes admises et exécutées**, et **43 sources distinctes refusées**
par `verify_program` et `compile_source`. Un contrôle supplémentaire construit
un vérificateur disposant uniquement des contrats pour tester le reset d'une
cible de champ, sans table de corps. Les [sources exactes et résultats](../validation/mutable-field-corpus.json)
sont conservés. Les [suites globales finales](../validation/mutable-field-suites.json) passent
**729 tests en standard (700,596 s)** et **729 en configuration UBSan
(701,048 s)**, sans test ignoré. Les deux exécutions précédentes, lancées avant
la correction du type de descripteur, ont été interrompues et ne sont pas
comptées comme résultats finaux.

Les **six injections dédiées** sont détectées : capacité exclusive dégradée,
filiation exclusive perdue, mauvais offset de pointeur, parent de projection
oublié, champ préparé non protecteur et type réel du descripteur effacé.
Les **29 injections précédentes rejouées** sont également détectées. Ce sont
35 injections sélectionnées sur des copies temporaires, sans taux global
inféré. Les empreintes de tous les fichiers Python du compilateur et des tests
correspondent à la version finale pour les sept campagnes.
[Mesures et liens vers chaque campagne](../validation/mutable-field-summary.json).

Deux premiers tests choisis n'étaient pas sensibles à leur injection : le
reset restait refusé par les contraintes de source malgré l'absence de prêt de
champ préparé, et l'accès au nom d'origine restait protégé par un second contrôle
malgré la dégradation d'un prêt secondaire. Le premier est désormais confronté
au cas de deux champs mutables aliasés ; le second à des lectures par les deux
parents mutables d'un résultat conditionnel, en conservant les assertions
d'écriture existantes. Les rapports initiaux et les incidents sont conservés
[séparément](../validation/mutable-field-incidents.json) ; ils ne sont pas comptés
comme les résultats finaux. Les nouvelles assertions sur les lectures des
parents ont aussi été exécutées dans la baseline de la campagne correspondante.

**48 exécutions C** respectent les observations attendues : quatre familles de
trois programmes, chacune en O0, O2, Os et O2 avec UBSan sans récupération.
La nouvelle famille exerce layout mixte, identité des adresses, retour de
porteur, aliases, reset, réutilisation et épuisement ; les trois autres rejouent
les champs partagés, retours d'objets empruntants et retours mutables directs.
Les diagnostics UBSan font échouer ces contrôles. Les épuisements attendus
arrêtent le programme sans dérouler les destructeurs, conformément à E1.
Compilateur disponible : Homebrew Clang 20.1.3, une seule famille C.

La configuration globale `CRUST_SANITIZE=undefined` instrumente les binaires
construits par le harness des tests et les oracles runtime. Cette variable
n'instrumente pas automatiquement chaque binaire produit par la CLI ; la
campagne C dédiée passe directement les options UBSan au compilateur C.

Le modèle indépendant utilise un intervalle de protection : une opération sur
la cible est permise seulement après le dernier usage du porteur. La graine
381 produit 24 scénarios, 12 admis et 12 refusés, avec lecture, écriture, drop
ou reset. L'oracle ne consulte ni les contrats ni les décisions du compilateur.
Il s'agit d'un modèle borné, sans prédiction générale des graphes d'emprunts.

Une ancienne attente refusait toute déclaration de champ &mut Int. Cette attente
est remplacée, conformément à l'approbation utilisateur ; le contrôle que les
champs &Int restent en lecture demeure dans les tests.

## Limites

Aucune preuve formelle de sûreté ni couverture exhaustive des compositions.
Les références stockées ciblent uniquement Int ; aucun graphe transitif d'enums,
cycle, référence imbriquée ou destructeur utilisateur. Les projections sont en
lecture et les corps de match gardent leur grammaire restreinte. La réunion des
cibles et des variantes reste conservative, sans corrélation générale des
chemins. Les scénarios générés et mutations sélectionnées ne constituent pas
une mesure globale de la couverture.

Les exécutions C utilisent une seule famille de compilateur disponible sur
cet hôte ; elles ne comparent pas des implémentations C indépendantes. ASan
reste indisponible sur cet environnement, d'après l'échec antérieur même sur
un programme C vide ; il n'a pas été présenté comme exécuté dans ce cycle.
UBSan apporte une observation des chemins instrumentés, sans preuve générale.
