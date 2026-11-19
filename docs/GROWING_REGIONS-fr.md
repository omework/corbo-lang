[English](GROWING_REGIONS.md)

# Corbo — data stacks, valeurs grandissantes et régions

Décisions de conception consignées le 4 novembre 2026, à la demande de
l'utilisateur. Ce document complète [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
notamment P1–P8. La consignation initiale ne modifiait pas le compilateur.
Les implémentations et vérifications réalisées depuis sont décrites dans
[GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md) et la
[matrice](VERIFICATION_MATRIX.md), avec leurs limites de placement.
Le [document de conception ouvert aux contributions](ALLOCATION_DESIGN_BRIEF.md)
présente le problème de placement, les entrées de l’analyse et les
cas de comparaison.

## 1. Placement et croissance

Le prototype distingue une data stack classique et une data stack
découpée en régions. Les emplacements de taille fixe sont alignés
dans la plage du scope sur la data stack classique. Une
valeur locale transférée est construite dans la plage durable prévue
pour son receveur. Le nettoyage de l’enfant précède le retour de sa
plage à la position d’entrée.

**G1 — Destination finale et placement anticipé.** Après la construction
de l’AST et la résolution des liaisons, des scopes et des transferts,
le compilateur suit l’identité de chaque valeur locale dans l’arbre
statique d’exécution. Sur chaque chemin, il suit les transferts jusqu’au
dernier receveur et identifie le scope chargé du nettoyage. Les
destinations qui diffèrent selon le chemin restent distinctes dans le
résultat de l’analyse.

Quand une zone durable peut être réservée dès la construction, le
compilateur place la valeur directement dans la zone de sa destination
finale. Une remontée successive peut ainsi utiliser un seul emplacement.
Chaque frontière enfant → parent reste vérifiée. Les liaisons intermédiaires
désignent la même valeur à la même adresse. L’initialisation a lieu au
point d’exécution prévu.

Pour un résultat local neuf construit par une fonction appelée,
l’appelant réserve l’emplacement dans la zone déterminée par
l’analyse de destination finale. Le compilateur transmet l’adresse
réservée à la fonction appelée, qui construit le résultat à cette
adresse au point prévu. Le contrat distingue cette construction
du transfert d’une valeur déjà construite, qui conserve son adresse.

Lorsque plusieurs scopes finaux sont connus, le compilateur traite
en priorité celui qui reçoit le plus de valeurs. Il place ensuite
autant de valeurs que possible directement dans leur scope final.
Cette priorité s’applique aux placements compatibles avec la durée
de vie et la stabilité de l’adresse.

- **Chemin choisi avant la construction.** Le plan peut prévoir
  un emplacement dans chaque destination possible. Seul le chemin
  exécuté initialise son emplacement.
- **Chemin choisi après la construction.** Le plan choisit dès la
  construction une seule adresse dans une zone qui survit à tous
  les chemins possibles. Le scope chargé du nettoyage dépend du
  chemin exécuté.

Des constructions sur des chemins mutuellement exclusifs peuvent
partager un emplacement si elles alimentent le même receveur et si la
plage satisfait leurs exigences de taille, d’alignement et de durée de
vie. Le plan réserve cet emplacement avant l’entrée dans le chemin
choisi et garde le site d’initialisation propre à chaque chemin.
Les cas dont le placement reste indéterminé suivent les autres
stratégies compatibles avec la source, la taille et la durée de vie.

**G2 — Deux data stacks.** La data stack classique reçoit les valeurs
de taille fixe, dont les descripteurs de `Vector<T>`, `String` et
`HashMap<K, V>` et les zones des pools. La data stack à régions
reçoit leurs contenus grandissants. Le descripteur porte un lien vers
la région où son contenu est construit.

L’annotation globale `datastack` se place au début du programme,
avant les déclarations. L’annotation et chacune de ses propriétés
sont facultatives.

```rust
#(datastack: size=4G, region_stack_size=4G, region_size=100M)
```

| Propriété | Taille configurée |
| --- | --- |
| `size` | Taille totale de la data stack classique. |
| `region_stack_size` | Taille totale de la data stack à régions. |
| `region_size` | Gabarit par défaut d’une région. |

Chaque taille s’écrit avec un entier décimal strictement positif
suivi de `K`, `M` ou `G`, selon les unités binaires de G6. Pour
chaque taille de data stack et pour le gabarit de région, le choix
suit cet ordre :

1. Prendre la taille explicitement déclarée, si elle est fournie.
2. Sinon, prendre le maximum nécessaire que l’analyse statique
   peut établir.
3. Sinon, utiliser la valeur par défaut correspondante. Pour une
   data stack, c’est la mémoire disponible divisée par le nombre de
   cœurs CPU. Pour une région, c’est `100M` (100 Mio).

La mesure de la mémoire disponible et l’arrondi du quotient
restent à préciser. La taille obtenue fixe une limite de réservation.
L’engagement des pages suit G11.

### Déduction des tailles à partir de l’arbre statique

Le calcul utilise les [représentations du vérificateur](MEMORY_REPRESENTATION.md#scopes-et-data-stacks).
Il suit les points d’exécution et les chemins des scopes, les
identités des valeurs et les liens qui maintiennent leur stockage
occupé. Les réservations anticipées sont comptées dès leur
création. Un transfert conserve le lien vers la zone qui survit.

- **`size`**. Le compilateur détermine la taille et l’alignement des
  valeurs fixes, des descripteurs et des zones des pools. Il suit le
  curseur du placement sur chaque chemin, en comptant les espaces
  d’alignement et les emplacements réservés chez le receveur.
  La capacité déduite est le maximum atteint par le curseur. Un
  emplacement intérieur nettoyé reste dans l’espace occupé jusqu’à
  ce qu’un suffixe libre permette de reculer le curseur. Une branche
  hérite des emplacements encore occupés dans le parent. Si le
  maximum ne peut pas être borné, la taille omise prend la valeur
  mémoire disponible divisée par le nombre de cœurs CPU.
- **`region_size`**. Le lien du descripteur vers le contenu permet
  d’associer chaque opération de croissance à sa région. Le
  compilateur borne les octets occupés au fil des opérations.
  Le calcul suit le nombre et la disposition des éléments pour
  un vecteur, les octets UTF-8 pour une chaîne et le stockage
  des entrées et de l’index pour une table de hachage. Le gabarit
  déduit est le plus grand besoin parmi les contenus qui utilisent
  le gabarit global. Si l’un de ces besoins reste inconnu, la taille
  omise prend la valeur `100M`. Un gabarit local explicite suit G6.
- **`region_stack_size`**. Le compilateur suit les réservations
  d’emplacements et leur récupération dans la stack à régions.
  Il compte les emplacements réservés par un `count` explicite
  dès leur réservation, y compris ceux qui restent vides. Dans
  une boucle, une région nettoyée peut être réutilisée. Une région
  retenue par une tâche ou un thread encore vivant reste occupée.
  Pour un gabarit uniforme, le pic d’emplacements réservés est
  multiplié par le pas d’un emplacement, alignement compris.
  Les stacks à régions dédiées sont dimensionnées séparément. Si
  le pic de réservation reste inconnu, la taille omise prend la
  valeur mémoire disponible divisée par le nombre de cœurs CPU.

Une taille inconnue conserve les déductions établies pour les
autres. Si le nombre d’emplacements est borné et que la croissance
d’un contenu ne l’est pas, le calcul de `region_stack_size` utilise
ce nombre avec le gabarit explicite ou, à défaut, `100M`. Si la
taille d’une région est connue et que le nombre d’emplacements ne
peut pas être borné, seul `region_stack_size` utilise sa valeur par
défaut.

**G3 — Curseurs à sens unique.** Chaque data stack et chaque région
a un seul front d’allocation. Le curseur avance vers les adresses
croissantes à l’allocation et peut revenir en arrière lors de la
récupération. Le placement à deux fronts opposés est reporté.

**G4 — Espace restant et dépassement.** Une allocation ou une
croissance doit tenir avant la borne supérieure de sa zone, en
tenant compte de l’alignement. Une demande qui dépasse cette borne
arrête le programme avec un diagnostic. Les contrôles comprennent
le calcul de taille et le chevauchement des emplacements.

## 2. Régions et intention du développeur

**G5 — Région comme sous-stack.** Une région est un espace borné dans la data
stack englobante, avec sa propre gestion de croissance et son curseur interne.
Un slot de pool est un bloc adapté à un type ; une région est une sous-stack
destinée au contenu grandissant. La taille réservée de la région ne varie pas
avec la longueur utilisée de la valeur qu'elle accueille.

Un pool de descripteurs gère ses slots dans une zone de la data
stack classique. Le placement du contenu référencé relève de la data
stack à régions. Le descripteur et son contenu conservent leurs
adresses lors des déplacements entre liaisons.

Quand le contenu grandit dans une région, `max_size` borne
les octets de cette donnée. Le descripteur et les métadonnées hors région
occupent leurs propres espaces. `Vector<T>` n’expose pas de champ `capacity`.

**G6 — Configuration des régions d’un scope.** L’annotation
`stack_region`, placée avant un bloc, configure le découpage de la
data stack à régions en emplacements pour ce scope.

```rust
fn main() -> i32 {
    #(stack_region: max_size=4M, count=8)
    {
        // Huit emplacements de région de 4 Mio chacun.
    }

    #(stack_region: max_size=1G)
    {
        // Autre gabarit : 1G par région.
    }
    return 0;
}
```

`max_size` est obligatoire. Il fixe le gabarit et la taille maximale de
chaque région. `count` est un entier décimal strictement positif
facultatif. Il fixe le nombre d’emplacements réservés dans la zone du
scope. Lorsqu’il est omis, le placement détermine le nombre
d’emplacements à réserver. Les emplacements peuvent accueillir les
contenus de plusieurs états de tâches ou de threads simultanément
vivants. Chaque région occupée compte jusqu’au nettoyage de son contenu.
Les espaces autour de `=` sont facultatifs.

| Suffixe | Nombre d'octets par unité |
| --- | ---: |
| `K` | 1 024 |
| `M` | 1 048 576 |
| `G` | 1 073 741 824 |

Un entier décimal strictement positif suivi de `K`, `M` ou `G` fixe la
limite. Ainsi, `4M` borne la région à 4 194 304 octets. Le paramètre borne
le contenu de la région selon G5 et suit les règles d'héritage et de
transfert de G7.

**G7 — Héritage et transferts.** Un enfant hérite de la configuration de son
parent et peut la remplacer avec sa propre annotation. Il peut utiliser
les emplacements réservés sous la configuration héritée. En l’absence de configuration locale ou héritée, le scope utilise
le gabarit par défaut du programme.
Une région déjà créée conserve son gabarit et sa limite quand sa valeur est
transférée : la configuration du receveur ne la redimensionne pas et ne déplace
pas son contenu. Le stockage doit survivre à la valeur transférée.

**G8 — Régions de même gabarit gérées comme des slots.** Sous une même
configuration, chaque région réserve le même gabarit. Ce choix rend leurs
emplacements interchangeables pour cette classe, même si leurs contenus ont des
longueurs utilisées différentes. On peut donc gérer les régions comme les slots
d'un pool :

- privilégier une nouvelle région au curseur englobant lorsque cela tient ;
- à la limite, réutiliser une région libre de l'index du même gabarit ;
- restituer une région seulement après le nettoyage requis de son contenu ;
- récupérer un suffixe libre par recul du curseur englobant en maintenant
  l'index cohérent.

```text
Même configuration : 4M par région
[ région A ][ région libre ][ région B ][ espace disponible ]
     4M           4M            4M
                   ^
            index des régions libres
```

Une région transférée reste occupée jusqu'au nettoyage de sa valeur à
destination. Des configurations de tailles différentes donnent des gabarits
différents ; aucune interchangeabilité arbitraire n'est supposée. L'alignement
et les métadonnées doivent permettre un pas de réservation cohérent dans chaque
classe. Le protocole exact de coexistence des classes reste à définir.

## 3. Choix de la stack et récupération

**G9 — Choix de la data stack à régions.** Avant la construction,
le compilateur détermine si la stack à régions courante peut accueillir
le contenu tout en laissant la place aux allocations qui coexistent
avec lui. Si le placement est possible, on utilise cette stack
selon G8. Si la coexistence ne peut pas être établie ou si le scope
demande un autre gabarit, on utilise une stack à régions dédiée.
Les valeurs fixes de ce scope continuent à relever de la data stack
classique.

Lorsque tous les emplacements réservés par `count` sont occupés,
un nouveau contenu peut utiliser une stack à régions dédiée en
conservant la même limite par région. Une fois le contenu construit,
son adresse reste stable. Une croissance qui dépasse la limite de
sa région déclenche le diagnostic de G4.

**G10 — Destruction, curseurs et pools.** Le destructeur s'exécute avant la
récupération du stockage. Un scope peut restaurer les positions de ses curseurs
après nettoyage uniquement si aucune valeur vivante n'est récupérée. Les
transferts empêchent une restauration aveugle. Une région libre ou un slot libre
ne réactive jamais les anciens accès.

Le pool reste une data stack de slots typés comportant éventuellement des trous,
avec un index des emplacements libres. La politique de préférence au curseur,
réemploi à la limite et récupération des suffixes est conservée. Les régions
reprennent cette organisation à l'échelle de sous-stacks de même gabarit. Elles
ne modifient pas les règles de destruction et de dépendance au pool.

Quand un scope lance plusieurs threads qui utilisent sa région, la
sortie du scope peut ramener le curseur de cette région à sa position
d’entrée en une opération, une fois ces threads terminés et leur
nettoyage achevé. Les zones qui contiennent un état, un résultat ou
une donnée encore nécessaire restent réservées. Un thread autonome
qui peut survivre au scope utilise dès le départ un stockage qui
lui survit. La récupération suit les garanties de RT7 et RT8.

Le nettoyage utilise `drop(valeur)` ou la fin du scope responsable.
En contexte multithread, MT7 impose une gestion sûre des métadonnées
partagées.

**G11 — Réservation, engagement et performances.** Réserver la capacité d'une
région ou d'une stack ne signifie pas engager immédiatement autant de mémoire
physique. Les pages sont mises à disposition selon le modèle P1. Les régions
et leurs index constituent une stratégie à mesurer, sans gain de performances
présumé. Leur disposition et leur politique pourront être ajustées sur la base
de mesures, sans changer silencieusement les limites explicites ni les règles
mémoire observables.

`#(datastack: reclaim_threshold=64M, region_reclaim_threshold=16M)`
configure les seuils de la datastack classique et de la datastack à régions,
respectivement. Chaque seuil est facultatif. Un seuil absent désactive la
restitution automatique correspondante. Les unités sont celles de G6.
Après le nettoyage et le recul du curseur, le runtime restitue les pages
entières libres qu'il peut regrouper si leur volume atteint le seuil.
Les pages conservées sous le seuil peuvent être reprises lors d'une sortie
ultérieure.

`#(free_pages)` s'écrit avant les accolades d'un bloc. Si ce bloc porte
aussi une annotation `#(stack_region: ...)`, celle-ci vient en premier.
À chaque sortie du bloc, après le nettoyage des valeurs et le recul des
curseurs, `free_pages` demande la restitution au système des pages
entièrement libérées par ce bloc, pour les deux datastacks, même sous leur
seuil de restitution automatique. La plage d'adresses virtuelles reste
réservée. Toute page qui contient encore une partie d'une valeur vivante
reste accessible, y compris si cette valeur a été transférée hors du bloc.

**G12 — Stabilité et emprunts.** Ni la croissance, ni le transfert, ni le
réemploi des autres régions ne doivent déplacer les éléments vivants dont les
adresses sont garanties stables. Cette stabilité ne dispense pas des règles
d'emprunt : elle n'autorise pas une mutation incompatible avec une réservation
active. Les contrats doivent conserver les dépendances envers les contenus,
régions et stacks d'origine, y compris via objets référents et tâches.

## 4. Limites et travaux reportés

Restent à définir, sans modifier les choix ci-dessus :

- les détails de calcul de la taille par défaut d’une data stack ;
- le compte des métadonnées, de l'alignement et des pages dans les limites ;
- l'algorithme de placement, les choix statiques/runtime et les conditions
  déclenchant la création d'une stack dédiée ;
- la représentation binaire des tranches et le contrat de leur éventuelle
  interface C ;
- la cohabitation de gabarits provenant de scopes imbriqués et de transferts ;
- le protocole concret des régions partagées entre threads ;
- l'API des collections grandissantes et leur grammaire. `Vector`, `push` et
  `growing_stack` ont servi d'illustrations, pas d'API validées par cette discussion ;
- les mesures de coût, mémoire réservée/engagée et fragmentation à effectuer.

`count` borne le nombre d’emplacements réservés dans la zone du
scope. La borne du nombre de valeurs simultanément vivantes se déduit
séparément, notamment quand certaines utilisent des stacks dédiées.

## 5. Statut

Le modèle à deux data stacks, le placement à sens unique, la
récupération après nettoyage des threads et les annotations
`datastack` et `stack_region` sont des décisions de spécification. Le
compilateur historique conserve l’annotation
`#(directive: stack_region_max_size=4M)` et ses chemins de stockage
existants.

G1–G12 sont des décisions de conception, **non implémentées et non vérifiées par
exécution dans cette passe**. Les tests historiques de slots fixes ne prouvent
pas la récupération des régions après le nettoyage des threads. Les scénarios de
validation future sont dans [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md),
et la portée documentaire du cycle dans
[GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md).
