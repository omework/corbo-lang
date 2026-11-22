[English](MEMORY_REPRESENTATION.md)

# Représentation mémoire du vérificateur Corbo

La décision [permission de mutation](MUTABLE_ACCESS-fr.md) prévaut sur les
passages qui déduisent une exclusivité du seul `&mut`. Séparer permission
d’écrire, dépendances de validité, fin de chaque branche et contrats de verrou
explicites. Corboc implémente cette séparation ; les preuves manquantes restent refusées.

Ce document décrit le modèle de conception du vérificateur. Il évolue avec
les décisions de conception et leur intégration. Les garanties du langage
sont définies dans les [règles du core](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture).

## Arbre statique d’exécution

L’arbre imbrique les scopes et porte leurs opérations dans l’ordre
d’évaluation. Des liens relient les opérations à leurs entrées, à leur
résultat et à leurs suites possibles. Un token pertinent peut être
représenté par le rôle qu’il donne à un nœud ou à un lien.

Une liaison a une identité propre, un nom, un scope de déclaration,
un type et une mutabilité. Son état par chemin indique l’entité qu’elle
désigne et son état `Disponible | Déplacée(PointExécution)`. Le point
identifie l’opération qui porte la destination du déplacement. Le scope
d’origine conserve cet état après la sortie de l’enfant. À une jonction,
chaque état et son point restent associés aux chemins qui les produisent.
Une liaison peut aussi désigner un
pool. Un usage de nom conserve l’identité de la liaison résolue. Un
déplacement garde l’identité de l’entité déplacée et relie la liaison
source à sa destination. Une nouvelle liaison du même nom a sa propre
identité.

L’analyse de placement intervient après l’AST et la résolution des
transferts dans l’arbre statique. Elle relie chaque identité de valeur
à ses dernières destinations possibles, avec le chemin et le scope
de nettoyage associés. Le plan de placement peut relier plusieurs
sites de construction exclusifs au même emplacement lorsqu’ils
alimentent le même receveur. Le site de construction reste propre au
chemin exécuté.

Une déclaration de fonction porte sa signature et son scope de corps.
Un appel porte la cible résolue, les arguments dans leur ordre
d’évaluation, leur correspondance avec les paramètres et la destination
du résultat s’il est reçu. Le corps statique est partagé. Le lien d’appel
situe l’activation dans le scope appelant. Une signature externe porte
son ABI. Un bloc `unsafe` porte le contexte lexical de ses opérations.

### Provenance et résumés dans le post-AST Rust

Dans une fonction, `Value.temp` identifie une valeur du post-AST.
`Value.provenance` relie une lecture à sa liaison, un déplacement local
à sa liaison et au nœud qui le déclenche, et un receveur à son temporaire
source. Lorsqu'un receveur peut être alimenté par plusieurs chemins, les
arêtes `Receive` ou `Break` portent les sources.

Le résumé de dépendances de `Value` référence des listes internées
d'origines et de projections. Il distingue les dépendances de la valeur
et celles qu'une future ou un handle transmet à son résultat. Un passage
de bloc à source unique réutilise les mêmes identifiants de résumés.
Une jonction de chemins combine les origines des résultats possibles.

Le placement calcule ses propres résumés par temporaire. Il propage les
origines de stockage le long des liaisons, réceptions et contrats d'appel.
Chaque origine de construction retenue référence un emplacement réservé
dans un scope du post-AST ou un emplacement fourni par l'appelant.
Les chemins exclusifs peuvent partager la même destination. Les deux
analyses réutilisent les résumés déjà calculés à travers les scopes.

Le programme post-AST porte aussi le plan de possession des agrégats.
Chaque entrée décrit les champs possédés, les éléments d'un tableau ou
les champs de chaque variante dans l'ordre de nettoyage. Un lien vers
un agrégat incorporé poursuit le parcours dans son plan. Un lien vers
un slot passe le relais au registre d'enfants du runtime, qui rend les
descendants avant le slot parent. Le générateur C traduit ces liens en
accès aux champs et en appels au runtime.
L'adoption et le transfert consultent ce même plan pour choisir le
parcours de possession à appliquer à la valeur transmise.

Pour les scalaires, le plan remonte les liaisons déplacées jusqu'au site
d'initialisation. Les liaisons intermédiaires peuvent désigner la même
réservation que le receveur final. Si plusieurs chemins transmettent une
valeur, ils peuvent partager une adresse qui reste accessible à tous
leurs receveurs. La sélection des emplacements partagés d'agrégats traite
d'abord les scopes qui ont le plus d'origines de construction candidates.

Un résultat de Future peut être construit dans le champ résultat de sa
frame. Une attente de scalaire peut écrire directement dans la
réservation du receveur dans la frame en cours. Les pointeurs des
liaisons ainsi placées restent dans la frame pendant la suspension.
Le runtime suit le scope logique de possession des slots de pool
indépendamment de l'adresse choisie par le placement.

## Identités, places et valeurs

Une opération porte un point d’exécution, son scope, ses opérandes
ordonnés et son résultat éventuel. Un fait encore à résoudre garde ses
entrées et son rôle. Par exemple, un appel de méthode porte le receveur,
le nom de méthode et les arguments avant que la méthode concrète et ses
effets soient connus.

Une place décrit une racine et une suite de projections. Les projections
identifient une indirection, un champ, une variante, un indice, une clé
ou une plage. Les indices, clés et bornes non résolus conservent leurs
expressions. Une borne omise conserve son rôle de borne implicite.
Une référence vers une partie de la racine conserve la projection
avec la cible. Une écriture conserve aussi la place évaluée et, pour
une opération composée, l’opérateur et l’opérande de droite.

Un littéral conserve sa valeur et sa catégorie. Pour le texte, la valeur
est la suite d’octets UTF-8 décodée. Pour un type écrit dans une signature,
une liaison ou une construction, le chemin et ses arguments restent
distincts. Une conversion porte la valeur source, le type demandé et
la forme d’opération. Un tableau littéral porte ses expressions dans
l’ordre, ou une expression et son nombre de répétitions.

## Adresses

Une adresse identifie symboliquement un emplacement. Un emplacement
empruntable peut recevoir une identité même si le générateur de code
détermine sa position physique plus tard. La réutilisation d'un slot crée
une nouvelle identité pour la nouvelle allocation.

```text
Adresse {
    id: AdresseId
    type_concret: TypeId
    pool_source: Option<PoolId>
}

ÉtatAdresse {
    scope: ScopeId
    owner: Option<ElementId>
    vivante: bool
}
```

Le scope indique le rattachement de l'allocation pour le nettoyage.
`owner` identifie la liaison ou la collection chargée de ce nettoyage.
Pour une adresse vivante sans owner, cette charge revient directement
au scope. Un déplacement peut changer l'owner et le scope. L'allocation
conserve son identité et son pool d'origine.

Un `ElementId` identifie une adresse, une référence, une collection ou
une liaison, selon le champ qui l'utilise. Chaque état décrit les faits
établis sur les chemins qui atteignent le point analysé.

## Références

```text
Référence {
    id: RéférenceId
    type_concret: TypeId
    mode: Partagé | Mutable
}

ÉtatRéférence {
    scope: ScopeId
    owner: Option<ElementId>
    origines: Ensemble<Origine>
    active: bool
}

Origine {
    cible: AdresseId
    projection: Suite<Projection>
    parent: Option<RéférenceId>
}
```

Une référence est une valeur à part entière. Son scope et son owner
décrivent son rattachement courant, indépendamment du rattachement
de sa cible. La référence peut appartenir à une liaison ou à un champ
de capture. Un déplacement conserve son identité et ses origines,
change son rattachement selon la destination et rend la liaison source
indisponible. La cible garde son propre scope et son propre owner.

Le parent désigne l'emprunt dont dérive un réemprunt. Le vérificateur
suit cette relation pour suspendre les usages incompatibles du parent.
À la jonction de chemins, il conserve chaque couple cible et parent.

## Collections

```text
Collection {
    id: CollectionId
    type_concret: TypeId
    adresse: Option<AdresseId>
}

ÉtatCollection {
    liens: Ensemble<Lien>
    contraintes: Ensemble<Contrainte>
}
```

Un lien de possession associe la collection à une valeur qu'elle doit
nettoyer. Un lien d'emprunt conserve la provenance d'une référence
reçue ou situe la zone empruntée par une référence issue de la collection.
Un élément lié peut désigner une adresse, une référence ou une autre collection.

La représentation peut être partielle. Les opérations créent les liens
utiles à la vérification et précisent leur position quand elle est connue.
Un indice, une clé ou un champ peut être résolu en position interne.
Une position incertaine représente les zones possibles. La longueur
d'un tableau fixe suffit à contrôler ses bornes, même avec un ensemble
de liens vide.

Une instance de pool porte son identité, son scope, son type d’élément
et sa capacité. Une construction via ce pool lie l’initialisation à
l’instance résolue et à la nouvelle adresse. Le déplacement de la valeur
laisse ce lien de provenance en place.

Une collection à variantes porte le discriminant et les champs de la
variante présente sur chaque chemin. Un bras de `match` porte le motif,
ses liaisons de projection et son scope. Les positions d’une collection
gardent leur sélecteur source tant qu’elles n’ont pas de position
interne résolue.

## Scopes et data stacks

```text
Scope {
    id: ScopeId
    parent: Option<ScopeId>
    enfants: Liste<ScopeId>
    liaisons: Liste<LiaisonId>
    entrée_parent: Option<PointExécution>
    sorties: Liste<SortieScope>
    zones: Liste<ZoneStockage>
}

ZoneStockage {
    datastack: DataStackId
    région: Option<RégionId>
    borne_inférieure: Position
    borne_supérieure: Position
    curseur_parent_à_l_entrée: Position
    curseur_relatif: Décalage
}
```

Le point d’entrée situe le scope dans l’ordre d’exécution du parent. Il
identifie une opération ou une frontière entre opérations et peut être
atteint par plusieurs chemins. Le repère de curseur conserve la position
théorique du parent sur le chemin d’entrée. Une position peut être
symbolique. Chaque zone porte ses bornes et son repère de curseur.
Le décalage vaut zéro à l’entrée. À la sortie, le repère permet
de récupérer la zone libérable. Un emplacement encore requis limite le recul. Le placement
anticipé dans la zone du parent peut permettre de récupérer toute la zone
de l'enfant après un transfert.

Le descripteur fixe se rattache à une zone de la data stack classique.
Son lien de stockage identifie la région du contenu dans la data stack
à régions. Une région utilisée par des threads porte les dépendances
à leurs états jusqu’à leur nettoyage.

Le [dimensionnement](GROWING_REGIONS.md#déduction-des-tailles-à-partir-de-larbre-statique)
utilise trois familles de faits dans cette représentation. Le type
concret fournit la taille et l’alignement d’un emplacement fixe.
Le lien descripteur → région associe les opérations de croissance
au stockage qu’elles occupent. Les réservations, sorties et liens
de durée de vie indiquent quand les emplacements de la stack à
régions sont retenus ou récupérables.

Une sortie de scope porte son point de départ, sa destination de
contrôle et, le cas échéant, la valeur produite et le receveur. La dernière
expression d’un bloc produit une valeur sur la sortie normale. Le
point-virgule d’une instruction d’expression indique une sortie sans
résultat de cette instruction. Les opérations de la frontière décrivent
les liaisons et les responsabilités qui y changent.

## Valeurs appelables

Une closure possède un type concret d’instance, une signature, un corps
et des liens de capture vers les liaisons extérieures résolues. Une
capture identifie sa liaison source, le champ de destination et l’entité
placée dans ce champ. La création et l’appel ont des points d’exécution
distincts. Le marqueur `move` s’attache à la création de l’instance.
Le champ devient l’owner de la valeur transférée, y compris pour une
référence partagée. La liaison source passe à `Déplacée` au point de
création. Le lien de capture porte la présence du marqueur et le mode
effectif lorsqu’il est établi. Pour une occurrence extérieure sans
marqueur, il conserve la source et le champ même si le mode effectif
est encore indéterminé.

## Tâches, attentes et contrats

Une définition async porte une signature et un corps statique. Une
instance porte son identité, sa définition, ses captures, sa source
de stockage et les liens vers son résultat et son nettoyage. Un point
de suspension porte le point de reprise et les entités conservées.
Un lancement relie la tâche à la branche et à son handle. Une attente
porte l’entité attendue, le point de reprise ou de continuation et
les issues possibles. Une issue de résultat conserve son discriminant
et les effets associés au chemin correspondant.

Les annotations portent leur cible et leurs propriétés. Un contrat
de type conserve ses paramètres, les types admis et les signatures
de méthodes exigées. Un contrat de branche relie la fin à l’opération
exprimée sur le résultat, lorsque celle-ci est écrite. Un contrat de
verrou porte la cible de l’exclusivité et, si indiqué, le lien qui en
prolonge la durée à travers le résultat. Une directive de capacité
conserve le chemin de la définition et la valeur déclarée. Une
annotation de région conserve son scope, sa limite, son unité et le
nombre facultatif d’emplacements réservés.

## Exemple de transfert de responsabilité

Les copies V3 de primitifs et d’enums admissibles créent une liaison disponible distincte et laissent
la source disponible. Elles ne créent ni lien de possession ni dépendance de
nettoyage vers la source. Une valeur `usize` issue de `addr()` conserve toutefois
sa dépendance vers la cible et son confinement dans `@unchecked`. Les déplacements
de valeurs non primitives continuent de marquer la source déplacée au moment
correspondant.



Dans une `HashMap<i64, A<i32>>`, on insère `a` avec
`table.insert(cle, a)` puis on le retire avec
`table.remove(&cle)`. La clé primitive est copiée implicitement : `cle` reste disponible, tandis que `a` est déplacée.

| Moment | Scope de l'allocation | Owner | Lien de possession |
| --- | --- | --- | --- |
| Avant l'insertion | Scope principal | Liaison `a` | `a` détient l'allocation. |
| Après l'insertion | Scope principal | Collection | La collection détient l'allocation sous la clé. |
| Après le retrait, dans `Some(recu)` | Scope du bras | Liaison `recu` | `recu` détient l'allocation retirée. |

Le pool d'origine doit rester valide aux trois étapes. Si la table
est déplacée vers une autre liaison, son identité de collection permet
de retrouver les mêmes liens de possession.

Le stockage de base identifie les pools nécessaires au porteur lui-même.
Les champs et entrées propriétaires ajoutent leurs propres liens. Le
retrait d’un lien peut retirer sa provenance du porteur si le stockage
de base est connu et qu’aucun autre lien ne retient ce pool. Une
provenance de base inconnue oblige à conserver les pools possibles.

## Jonction de chemins

Un receveur peut désigner une allocation différente selon le chemin.
Une condition relie son expression aux entrées possibles. Une jonction
lie chaque entrée au résultat ou à l’état qu’elle apporte. Une sortie
anticipée indique la fonction ou la boucle qu’elle vise. Une reprise
indique son point de retour et les scopes quittés. Pour `while`, ce
point est l’évaluation du test.

Une affectation identifie la place cible et la valeur évaluée à droite.
Ses opérations ordonnées distinguent l’écriture du contenu et le
remplacement d’une valeur. Pour un remplacement, elles conservent
l’ancienne identité jusqu’à l’évaluation du résultat de droite, puis
relient le nettoyage de l’ancienne valeur et l’installation de la nouvelle.

Le nettoyage utilise l'allocation du chemin exécuté. L'analyse
conserve les dépendances possibles de ces allocations, y compris les
pools, verrous et écritures qu'une valeur peut transmettre à un
résultat différé. Quand plusieurs chemins portent des mises à jour,
la jonction garde leurs effets possibles sans les traiter comme un
effet certain unique.

Cette fusion s’applique aussi à la valeur produite par un `match` ou
un `break` et aux représentations d’une charge extraite d’une
collection. À la reprise d’une boucle, le compilateur compare les
provenances et variantes du résultat différé, y compris celles de
ses champs. Pour une origine créée pendant l’itération, il compare
sa source connue afin de rester indépendant des identifiants recréés
par l’analyse.

Pour une écriture différée, la comparaison inclut la destination,
les liens de dépendance et de possession et les parents d’emprunt.
Une écriture sous verrou identifie aussi la charge protégée. Lorsque
les positions d’une collection sont connues, la comparaison inclut
leurs sources et provenances. Pour les effets dont l’exécution exacte
est établie, elle conserve l’ordre et la multiplicité.

Le contrôle de durée de vie suit la valeur qu’une écriture peut
installer, ses descendants et ses effets différés. Une écriture
gardée conserve le verrou, la charge protégée et les cibles que
ses nouveaux liens doivent garder vivantes.

## Bornes littérales et texte inline borné

Le compilateur conserve l’argument générique littéral dans un nœud AST de genre
94 avec sa plage source. La spécialisation le substitue dans le tableau fixe de
String<N>, représenté comme une structure ordinaire. Les résumés de provenance,
de placement et de dépendances existants sont réutilisés. L’emprunt de la charge
de A<T> vise la liaison de l’allocation ; une vue texte dans Result conserve sa
racine source. La visibilité privée suit chaque déclaration concrète générée et
son implémentation, plutôt que l’emplacement d’un modèle effacé.

Voir les [résultats d’intégration](cycles/BINARY_TIME_BOUNDED_CYCLE.md).

## Faits d’accès et de protection implémentés

`CheckedValue.writable` porte la permission d’écrire, indépendamment de la
mutabilité de liaison et des liens de cible, de réemprunt et de possession.
Les nœuds statiques portent `access_mode` (effet démontré sur le contenu sans
invalidation du stockage) et `protection` (identité de verrou résolue). Ces résumés
sont établis après résolution lexicale et instanciés aux appels et captures.
Les verrous portés par résultat gardent un marqueur dédié, sans permission
d’écriture induite. Un effet ou un verrou inconnu n’établit aucune preuve de
synchronisation. Voir [MA1–MA6](MUTABLE_ACCESS-fr.md).

## Contrats de verrou objet (MT11)

Un `#(lock)` sur une struct est représenté par son nœud d’annotation ; les méthodes conservent leur visibilité `pub`. Le contrat effectif du receveur est déduit de cette déclaration avant l’analyse des accès et conservé par spécialisation. Les appels associent les paramètres formels aux racines des receveurs effectifs, via les helpers privés et fonctions libres. Aucun nom de type concret ne fournit de fait de protection et aucun verrou runtime n’est généré.

## Représentation du déplacement entre threads (TR1)

Un nœud d’annotation `thread` possède la propriété `transfer=false`. Un résumé
monotone distinct associe déclarations nominales concrètes, champs possédés,
liaisons et états d’exécution à l’annotation restrictive d’origine, ou à zéro
si aucune restriction n’est trouvée. Les liens de possession et de liaison
propagent le fait ; les références conservent leurs dépendances de validité et
protection séparées. Les captures de closure réutilisent les champs de leur
struct générée. Les états async incluent captures possédées, locaux retenus aux
suspensions et résultats. Le lancement d’une branche consulte ces faits sans
modifier les résumés de possession, durée de vie ou verrou.
