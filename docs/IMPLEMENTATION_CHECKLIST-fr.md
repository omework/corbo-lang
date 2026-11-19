[English](IMPLEMENTATION_CHECKLIST.md)

# Checklist globale d'implémentation

## Packages et modules

- [x] Charger un package depuis `package.toml` et compiler son point d’entrée
  `src/main.crb` avec des modules par dossier, `pub`, des alias et des imports
  groupés. Vérifier les refus de collisions et d’accès privés.
  [Validation](cycles/CORE_COMPOSITION_CYCLE.md#single-package-modules)
- [x] Charger les packages externes par chemin local ou commit Git épinglé.
- [x] Charger la bibliothèque standard livrée avec le compilateur.


## Placement fixe dans le compilateur Rust

- [x] Structures synchrones à champs scalaires. Destination finale déduite
  après l’AST, emplacement partagé entre bras exclusifs et stockage réservé
  par l’appelant. Quatre témoins C sous UBSan.
- [x] Placer les liaisons et résultats scalaires et de référence du backend
  Rust et raccorder leurs réservations et celles des structures à la datastack
  à curseur. Sept témoins C sous UBSan à `-O0` et `-O2`.
- [x] Abaisser les autres primitifs, les tableaux à longueur littérale,
  les enums nominaux, les structures imbriquées et le stockage des pools
  locaux. Les huit nouveaux témoins passent sous UBSan à `-O0` et `-O2`.
- [x] Transmettre les pools par emprunt et les allocations `A<T>` par
  valeur, dans les signatures et entre scopes. Lire les variantes des enums
  directement dans leur slot de pool.
- [x] Propager les dépendances des agrégats à références et emprunter les
  agrégats, leurs champs et leurs cases. Quatorze témoins et dix refus
  ciblés. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dépendances-des-agrégats-et-transferts-de-pool).
- [x] Suivre les provenances par champ et par case, réemprunter à travers
  un agrégat emprunté et lier les champs agrégés d’un match emprunté.
  Huit nouveaux témoins et six refus. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#provenances-par-position-et-match-emprunté).
- [x] Dimensionner la datastack classique selon la taille explicite, la borne
  post-AST ou le défaut. Dix témoins C et six refus d’annotation.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dimensionnement-de-la-datastack-classique).
- [x] Raccorder la datastack à régions aux `Vector<T>` à éléments fixes
  sans dépendances et aux `String` créés en pool. Les tailles globales et
  locales, le transfert et la récupération sont exercés.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-régions-dans-le-backend-rust).
- [x] Raccorder les `HashMap` à valeurs primitives et les vecteurs qui
  stockent des références ou possèdent des `A<T>`. Sept témoins C et
  quatre refus ciblés.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#collections-à-dépendances-et-régions).
- [x] Construire un littéral de structure directement dans le slot de
  `Pool.new` quand le plan post-AST établit que le littéral est consommé
  immédiatement. Le parcours de possession adopte les enfants depuis ce slot.
- [x] Raccorder `pop` et `remove` pour `Vector<A<T>>`. L’extraction
  rattache l’allocation à son receveur et conserve son pool d’origine.
  Le suivi statique du vecteur garde une union conservatrice des provenances.
- [x] Admettre les types de références imbriquées et les résultats de
  `get` et `get_mut` pour les valeurs `A<T>`, `&T` et `&mut T`.
  Le backend valide les lectures et les réemprunts à deux niveaux.
- [x] Suivre les dépendances de HashMap par clé connue. Une clé dynamique
  conserve une union des provenances possibles.
- [x] Propager les remplacements d’emprunts de HashMap par les contrats
  synchrones, y compris les relais. Les effets conditionnels préservent
  les provenances possibles.
- [x] Conserver les effets de remplacement différés jusqu’à l’attente
  dans le même contexte d’analyse. `join()` et `.await` mettent à jour
  le résumé avec les provenances possibles, succès ou échec de lancement.
- [x] Transmettre les effets différés dans les contrats d’attente
  synchrones et async et dans le retour direct d’une fabrique native.
- [x] Encoder la position du handle dans le contrat de résultat et
  approximer les écritures des appels récursifs synchrones.
- [x] Transporter les handles et leurs effets dans les agrégats fixes,
  les retours de workers et les relais récursifs qui préservent les chemins.
  Valider les attentes récursives sync et async, succès et échec de lancement.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-imbriqués-et-récursifs-dans-le-backend-rust).
- [x] Résoudre les contrats des cycles récursifs qui reconstruisent les chemins
  ou combinent attente et restitution. Stocker et extraire les handles dans
  les pools et vecteurs, avec propagation des effets différés.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-en-collection-et-contrats-des-cycles-récursifs).
- [x] Déduire la case unique de `remove(index)` et la fin des dépendances
  sur le bras `None` de `match handles.pop()`. Vérifier une sortie anticipée.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#déduction-de-la-case-unique-et-vidage-dun-vecteur-de-handles).
- [x] Mesurer la restitution intégrée sur un programme Corbo à pics répétés.
  [Mesures](G11_DATASTACK_BENCHMARK.md#restitution-intégrée-sur-un-programme-crust).
- [x] Placer les états des threads natifs avec `join()` immédiat dans une
  région. Les captures scalaires nommées et les datastacks propres au
  worker sont exercées sur succès et échec de lancement.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#état-régional-des-threads-natifs).
- [x] Conserver les handles de thread et les transférer entre scopes ou
  appels. Suivre les captures d’emprunts scalaires jusqu’au join et
  nettoyer les tâches autonomes abandonnées.
- [x] Placer les Futures du sous-ensemble Rust en région. Conserver
  variables, pools et contenu grandissant entre les polls de `yield`.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-et-contextes-async-en-région).
- [x] Abaisser `.await` d’une Future inactive et `yield` dans les scopes
  imbriqués. Le plan post-AST conserve les points de reprise, temporaires
  et marques de scope. Les captures et résultats fixes à emprunts
  conservent leurs provenances. Quinze témoins C et treize refus ciblés.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#attente-directe-et-agrégats-empruntés-dans-le-backend-rust).
- [x] Transférer les agrégats fixes qui possèdent des slots `A<T>` entre
  l’appelant, l’état async et le receveur. Nettoyer les captures et
  résultats sur les sorties qui les abandonnent.
- [x] Propager les dépendances du résultat de `join()` à travers les
  signatures, puis dans le seul bras `Ok`.
- [x] Abaisser `spawn_blocking` et `AsyncHandle.await` avec mise en sommeil,
  réveil et nettoyage sur `LaunchFailed`. Le lot compte 27 témoins C,
  18 refus ciblés et 53 témoins de régression.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#ressources-et-complétions-de-tâches-dans-le-backend-rust).
- [x] Composer le nettoyage des structs, slots de pool et éléments de
  vecteur. Le même parcours rattache les slots possédés, puis le runtime
  restitue les enfants avant leur parent. Une trace C vérifie cet ordre.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#nettoyage-composé-des-slots-possédés).

## Checklist actuelle — grammaire et règles

La version du 11 novembre 2026 sert de référence du core. Elle couvre
la grammaire EBNF, son intégration au parseur et l’énoncé des règles N1 à N8,
y compris les signatures de closure `fn(...) -> R`.

Le [guide de reprise pour l’audit indépendant](CORE_AUDIT_HANDOFF.md)
regroupe les références du core et le protocole de reproduction.

- [x] **Grammaire et parseur.** Les formes validées du core sont consignées
  dans [l’EBNF](../CORE_GRAMMAR.ebnf) et intégrées au parseur.
  `check --syntax-only` expose ce périmètre. TX1 fixe les échappements JSON.
- [x] **Énoncé des règles.** Les invariants N1 à N8 sont consignés dans
  [LANGUAGE_RULES.md](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture),
  avec leurs références normatives.

### Closures

- [x] **Grammaire.** `|…| { … }` crée une closure et `fn(...) -> R`
  décrit sa signature d’appel. `&fn` et `&mut fn` indiquent le mode d’emprunt.
- [x] **Parseur.** `check --syntax-only` reconnaît ces formes et
  `mut f: fn(...) -> R`. Il distingue l’emprunt de l’instance de celui du
  résultat et refuse l’ancienne notation `closure(...) -> R`.
- [x] **Règles.** Le passage par valeur suit les règles ordinaires de copie
  et de déplacement. L’emprunt de l’instance est explicite au point d’appel.
  Un appel qui modifie l’état de la closure exige un accès mutable, fourni
  par `mut f` sur le paramètre reçu par valeur ou par `&mut fn`.

SelectGroup reste reporté. La vérification sémantique et la validation
relèvent d’une passe ultérieure.

Le travail restant sur le vérificateur figure dans
[Vérification sémantique du core](#vérification-sémantique-du-core).
Les migrations de tests et ASan sont suivis dans
[Alignement et validation du core](#alignement-et-validation-du-core).

## Grammaire et parseur

- [x] Partager la production des arguments de type entre types nommés
  et appels qualifiés paramétrés. Vérifier les noms définis par le
  programmeur, `MonType::new()` et `HashMap<i64, Point>::new()` au parseur.

- [x] Écrire les signatures de closure avec `fn(...) -> R`. Reconnaître
  le passage par valeur, `&fn`, `&mut fn` et `mut f: fn(...) -> R`.
  Le parseur du core conserve ces formes avant l’élaboration.

- [x] Vérifier quatre formes au parseur. Paramètre de closure typé ou
  sans type, clé entière ou flottante dans une HashMap.
- [x] Exposer l'analyse syntaxique avant élaboration et reconnaître les
  trois formes de l'annotation `branch`, y compris `result.await`.
- [x] Parser les annotations de type empilées, la déclaration libre
  `#(type: R)` et les contrats de méthodes avec ou sans `with`.
- [x] Conserver les chemins de types qualifiés dans les signatures,
  y compris dans les types de closures, de HashMap et de handles.
- [x] Exiger `#(directive: …)` dans le profil du core et vérifier les
  suffixes binaires `K`, `M` et `G` ainsi que les noms de pools qualifiés.
- [x] Aligner les listes de bras de `match` sur l'EBNF du core.
  Au moins un bras, virgule entre les bras et virgule finale facultative.
- [x] Reconnaître les motifs de `match` dans l'arbre syntaxique avant
  les contrôles d'exhaustivité et la traduction des résultats builtin.
- [x] Parser les références dans les arguments de types imbriqués et
  vérifier les séparateurs des listes de paramètres des closures.
- [x] Reconnaître les tranches dynamiques sous emprunt dans les
  signatures, les types imbriqués et les annotations de liaison.
- [x] Lire les signatures `AsyncHandle` et les littéraux annotés `u8`
  avant leurs contrôles de typage.
- [x] Parser les chemins qualifiés dans `impl`, les deux formes de
  `lock` et les déclarations d'enums non vides.
- [x] Parser les chemins de valeurs qualifiés comme valeurs, appels et
  opérandes d'une attente async.
- [x] Distinguer la syntaxe des littéraux entiers de leurs bornes de
  représentation. Vérifier les décimaux, les plages et les comparaisons.
- [x] Distinguer les entrées `move a;` des blocs `move { … }` et
  refuser une entrée nommée après une instruction ordinaire.
- [x] Reconnaître l'expression finale d'un bloc au parseur seul,
  indépendamment du type de retour de la fonction.
- [x] Reconnaître les instructions d'expression terminées par `;`
  dans les blocs au parseur seul.
- [x] Parser les places d'affectation combinant champs, indices et
  déréférencements, avec affectation simple ou composée.
- [x] Parser les chaînes de suffixes en lecture avec champs, indices
  et appels de méthode sur une expression composée.
- [x] Parser le suffixe `.new()` sur un receveur composé, avec
  initialisation vide, positionnelle ou par champs nommés.
- [x] Limiter le niveau racine aux déclarations et directives de capacité
  dans le parseur syntaxique du core et refuser les déclarations imbriquées.
- [x] Reconnaître les directives de région sur les corps de fonctions
  et les blocs de contrôle, dont les bras de `match`.
- [x] Reconnaître un `if` sans `else` avant la vérification des valeurs
  de branche, y compris après `else if`.
- [x] Parser le déréférencement d'expressions unaires et postfixées,
  en conservant la priorité par rapport aux opérateurs binaires.
- [x] Reconnaître les signatures et appels `extern "C"` avant
  la traduction du corps externe et le contrôle du contexte `unsafe`.
- [x] Appliquer le profil syntaxique du core indépendamment des
  heuristiques du prototype et refuser les anciennes flèches de transfert.
- [x] Reconnaître `()` comme expression primaire et vérifier
  les parenthèses d'un appel immédiat de closure.
- [x] Lire les conversions qualifiées et les variantes d'erreur avant
  le contrôle de l'arité et de l'existence du membre.
- [x] Exiger le receveur `self` en tête des signatures de méthode et
  vérifier les formes empruntées et par valeur.
- [x] Reconnaître les constructeurs d'enum avec ou sans champs,
  y compris comme sujet de `match`.
- [x] Reconnaître les tailles entières non signées des tableaux et
  pools avant les contrôles de bornes et de capacité.
- [x] Lire les entiers non signés de `async_pool_sizes` avant
  la vérification de leur capacité.
- [x] Conserver une taille de région décimale positive au parseur,
  même si elle dépasse la borne de représentation du compilateur.
- [x] Refuser les identifiants réservés en position de déclaration dans
  le parseur seul, avec `self` comme receveur et `_` dans les motifs.
- [x] Accepter une expression qualifiée dans `.new(...)`, exiger des
  noms simples pour ses champs et limiter les types parenthésés à `()`.
- [x] Parser les types d’emprunt dans `Pool<type>::new(taille)` et appliquer
  la syntaxe des identifiants aux variantes et champs des motifs d’enum.
- [x] Parser les alternatives de type dans les contrats, y compris les
  emprunts, avant les contrôles de noms distincts et de type du receveur.
- [x] Parser `runtime::spawn` et `runtime::spawn_blocking` avec exactement
  une expression, avant les contrôles de type et de contexte async.
- [x] Parser les captures nommées et les suspensions dans les blocs de
  `runtime::thread` avant les contrôles de contexte et de capture.
- [x] Parser les arguments des méthodes ordinaires avant les contrôles
  d’arité et consigner la syntaxe de plage de `try_slice` dans l’EBNF.
- [x] Appliquer la forme EBNF des constructeurs de mutex et écarter les
  constructions historiques préfixées du parseur seul.
- [x] Vérifier les segments des chemins qualifiés et refuser les formes
  historiques ou expérimentales de type hors de l’EBNF du core.
- [x] Conserver l’opérateur d’emprunt appliqué à une découpe avant le
  contrôle de mutabilité.
- [x] Appliquer la même production d’affectation aux noms simples et aux
  projections, avec contrôle des identifiants réservés.
- [x] Conserver les formes bloc finales sans point-virgule comme
  expressions de résultat dans le parseur seul.
- [x] Désambiguïser les accolades vides après une variante d’enum lorsque
  la production englobante attend un bloc.
- [x] Appliquer les contraintes lexicales aux chemins de valeurs et aux
  noms de champs, et écarter les anciens appels runtime du parseur seul.
- [x] Appliquer la production `chemin_valeur` aux motifs de `match`, y
  compris aux chemins intégrés et à leurs identifiants.
- [x] Parser le type complet après `as` avant le contrôle des conversions.
- [x] Reconnaître les déclarations externes et async de `main` avant la
  vérification du point d’entrée.
- [x] Refuser deux directives de région consécutives sur le même bloc et
  vérifier les annotations sur les blocs terminaux.
- [x] Refuser la liaison de paire et `type feature` dans les blocs du
  core, et distinguer l’import `move` de la closure `move`.
- [x] Exiger un séparateur `::` contigu, y compris dans les types
  génériques imbriqués dont la fermeture touche `=`.
- [x] Exposer la vérification syntaxique du core par `check --syntax-only`.
- [x] Conserver le nom `i32` dans l’arbre syntaxique et appliquer la
  liste des clés de HashMap prévue par l’EBNF.
- [x] Conserver les types écrits dans les signatures avant l’abaissement
  des allocations, emprunts et handles.
- [x] Empêcher la reprise par les productions d’instruction historiques
  après le refus d’un nom réservé en position d’expression.
- [x] Distinguer la construction d’une variante d’un appel de méthode ou
  d’un suffixe `.await` qui suit un nom d’enum.
- [x] Reconnaître un `if` à bloc vide suivi d’un opérateur ou d’un suffixe,
  même si la condition se termine par une variante d’enum.
- [x] Expliciter `self` comme valeur et base d’affectation dans l’EBNF,
  et identifier les productions de SelectGroup dont l’intégration est reportée.
- [x] Aligner le programme de démonstration `examples/main.crb` sur
  la syntaxe du core et rejouer son témoin existant.
- [x] Migrer `examples/conditional_returns.crb` vers `A<i32>` et vérifier
  le retour par branche, le relais et la réutilisation du slot.
- [x] Migrer les exemples de retour d’un objet contenant un emprunt vers
  `A<View>` et vérifier leurs deux issues de compilation.
- [x] Distinguer le suffixe de plage `try_slice(..)` d’un appel de méthode
  ordinaire portant le même nom.
- [x] Rejouer les 57 témoins qui appellent directement `parse_syntax`
  et expliciter les suffixes contextuels dans l’EBNF.
- [x] Distinguer les fermetures génériques de `==`, `>=` et `>>` quand les
  opérateurs suivent directement un type cible de conversion.
- [x] Reconnaître l’appel immédiat d’une closure avec la paire de
  parenthèses prévue par `appel_closure`.
- [x] Distinguer le constructeur `Pool<T>::new(taille)` des usages ordinaires
  du nom `pool` dans les expressions, y compris les comparaisons imbriquées.
- [x] Vérifier les échappements reconnus par le parseur actuel et relever
  la liste normative manquante dans TX1.
- [x] Fixer les échappements JSON dans TX1 et l’EBNF, puis vérifier
  les octets décodés et le refus des formes invalides.
- [x] Désambiguïser les accolades après un nom de structure en condition,
  pour les blocs vides et les blocs contenant des instructions.
- [x] Conserver l’erreur syntaxique interne d’une expression, y compris
  d’une forme bloc, sans relire la même forme comme instruction.
- [x] Mettre à jour le témoin de thread natif selon N4 et RT7, avec et sans
  dépendance empruntée.
- [x] Rejouer ensemble les six suites de syntaxe et d’intégration du core
  et vérifier les cinq exemples du core via `check --syntax-only`.
- [x] Réaligner le receveur de la déclaration historique `type feature`
  sur TF1 et rejouer l’assertion de refus qui échouait.
- [x] Conserver `copy(...)` comme appel au parseur seul et vérifier
  l’absence d’enregistrement des types d’un témoin async.
- [x] Diagnostiquer les octets source UTF-8 invalides dans `check --syntax-only`.
- [x] Rejouer au parseur seul les programmes complets acceptés par la
  suite d’intégration et vérifier le refus du scheduler expérimental.
- [x] Consigner les correspondances entre familles EBNF et points
  d’entrée du parseur, avec le rejeu des 61 témoins syntaxiques.
- [x] Migrer les exemples de champ emprunté et vérifier le refus du
  `drop` placé avant le dernier usage du champ.
- [x] Migrer le témoin de `match` non exhaustif et vérifier son acceptation
  syntaxique ainsi que le refus d’exhaustivité.
- [x] Migrer le témoin de remplacement entre pools avec un résultat nommé
  et consigner le refus de l’affectation directe d’un résultat d’appel.
- [x] Aligner les exemples et les extraits README de retours directs
  d’emprunt sur `.vref()` et `.mut_vref()`.
- [x] Vérifier au parseur et à l’exécution les six exemples du core
  dédiés au contrôle de flux et aux sorties de bloc.
- [x] Aligner les exemples de `drop` et de déplacement sous emprunt sur
  `A<i32>` et vérifier les refus du vérificateur.
- [x] Migrer les exemples de type de pool incompatible et de retour
  d’allocation depuis un pool local.
- [x] Migrer l’exemple d’ordre des arguments vers le passage par valeur
  de `A<i32>` et vérifier l’ordre inverse avec le même type d’appel.
- [x] Migrer l’exemple de champ emprunté mutable vers `A<Writer>` et
  vérifier l’écriture avant et après le dernier usage de l’emprunt.
- [x] Migrer l’exemple de deux provenances vers `A<i32>` et vérifier
  l’identité et le réemploi pour chacune des deux branches.
- [x] Migrer les quatre témoins de portée et de déplacement qui
  utilisaient les anciennes flèches ou `allocator()`.
- [x] Relever et corriger les écarts recensés entre productions EBNF et
  parseur sur les formes validées du core. La revue et les témoins sont
  consignés dans [le rapport](cycles/CORE_COMPOSITION_CYCLE.md).

Pour la concurrence, le noyau utilise le runtime intégré. Le remplacement
du runtime et ses interfaces publiques sont reportés après la validation
des invariants du runtime intégré.
La première `HashMap` fait l'objet des règles HM1–HM6. Les autres extensions
d'API des structures de données sont reportées. Les cas qui utilisent une API
existante peuvent servir à vérifier un invariant du noyau.

## Revue des représentations

- [x] Reconstruire les quatre témoins de portée et de déplacement et
  cartographier les tokens des formes de closure jusqu’au point d’arrêt.
- [x] Mettre à jour les identités de liaison, les points de scope, les
  liens d’appel, de provenance et de capture dans le modèle.
- [x] Consigner le transfert d’une référence partagée sous `move` et
  conserver le point du déplacement dans l’état de sa liaison source.
- [x] Cartographier les témoins de retours, jonctions, boucles,
  affectations, emprunts et projections examinés lors de la reprise.
- [x] Parcourir le corpus extrait du dépôt et construire un graphe par
  programme ou fragment reconnu, avec le lien de chaque token vers
  son scope et ses nœuds.
- [x] Consigner les projections, contrôles, opérations, annotations et
  faits indéterminés dans la définition des représentations.
- [x] Construire la chaîne lexeur, parseur et arbre statique en Rust.
- [x] Comparer la projection Rust aux 2 766 occurrences du corpus.
  Le rapport conserve les écarts de représentation et de parsing.
- [x] Raccorder le vérificateur Rust et l’émission C pour le
  sous-ensemble scalaire synchrone et les emprunts locaux.
- [x] Construire le graphe de contrôle et suivre le dernier usage
  des emprunts locaux. Stabiliser les états aux reprises de
  `while` et `loop` et raccorder `break` et `continue` au C.
- [x] Raccorder les réemprunts scalaires, les paramètres et retours
  de références scalaires et les boucles à résultat scalaire ou
  emprunté. Conserver les provenances possibles et les parents.
- [ ] Étendre le vérificateur Rust à la totalité de N1–N8,
  notamment les contrats d’effets des agrégats, le stockage
  propriétaire et l’async.
- [ ] Raccorder ces représentations à l’analyse sémantique dans un lot
  distinct. Les données déjà disponibles restent utilisables même si
  une capture ou une provenance n’a pas encore de mode résolu.

[Revue token par token](cycles/CORE_COMPOSITION_CYCLE.md#revue-token-par-token-des-représentations).

## Vérification sémantique du core

Les identifiants N1–N8 renvoient à la [grille des règles du core](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture). Les cases ouvertes portent sur les garanties à appliquer. Les exemples servent de témoins, et un refus de compilation doit être confirmé contre la règle avant correction.

- [ ] **N4 — Durée de vie des cibles et des pools.** Prouver sur chaque chemin
  qu’une cible capturée survit aux usages de la branche, y compris quand la
  preuve de fin dépend d’une attente à travers un handle. Exercer les captures
  et retours à dépendances des closures ainsi que les handles transmis.
- [ ] **N5 — Compatibilité des accès.** Suivre la zone réservée et les
  réemprunts jusqu’à leur dernier usage. Exercer les captures mutables non
  scalaires des closures, les réemprunts depuis une entrée mutable de HashMap
  et les accès sous un verrou acquis en async. Rejouer le témoin
  `match &*view` avec cette règle.
- [ ] **N6 — Chemins, provenance et ordre d’évaluation.** Conserver les
  faits propres à chaque chemin jusqu’au point d’usage, notamment à travers
  les lancements et attentes. Pour le remplacement, vérifier que la partie
  droite est évaluée avant la destruction de l’ancienne valeur.
  Témoin de régression : `data = make(&mut first, view);`.
- [ ] **N8 — Conservation des obligations aux frontières.** Propager dans
  les contrats les provenances, emprunts et effets de nettoyage nécessaires
  aux appelants. Exercer les corps généraux annotés `branch`, le passage de
  handles à dépendances, les retours d’`AsyncHandle`, les retours à
  dépendances des gabarits de closure inutilisés et les effets d’appel
  sur les entrées de HashMap.
  [Rapport](cycles/CORE_COMPOSITION_CYCLE.md) ·
  [Contrats async](ASYNC_MULTITHREAD_RULES.md#4-runtime-scheduler-et-point-dentrée)

Avancement côté compilateur pour les quatre règles. Validation non exécutée.

- **N6 et N8.** La jonction conserve les obligations différées des
  valeurs imbriquées et des receveurs remplacés via la même fusion
  que celle des liaisons conservées. Cette fusion sert aussi aux
  résultats de `match` et de boucle et aux charges extraites dont
  plusieurs représentations sont possibles. Le point fixe des
  boucles compare également les provenances et variantes de
  résultat différé, les destinations et le contenu des écritures
  différées ainsi que l’exactitude des effets.
  Les projections récursives conservent leur provenance aux
  jonctions. La comparaison des boucles lit leur table de pools
  par type à l’intérieur de chaque origine.
  L’instanciation d’un contrat de résultat préserve les champs
  finaux qu’il décrit et récupère les autres projections depuis
  les arguments.
- **N4 et N8.** Après une attente, les effets gardés sont appliqués
  à leur charge respective. Le résultat de l’attente affine les
  dépendances quand une seule écriture exacte vise une charge unique.
- **N6 et N8.** Un relais synchrone qui restitue un unique handle
  sans ajouter d’écriture conserve l’exactitude de ses effets
  différés. Les pools et la preuve d’autonomie d’un relais sont
  propagés à partir de ses arguments.
- **N4 et N8.** Le lancement synchrone reprend toutes les obligations
  différées de la tâche inactive dans son handle d’exécution.
- **N6 et N8.** Les pools concrets d’un `AsyncHandle` autonome
  retourné par une tâche sont propagés jusqu’aux attentes et au
  suivi des abandons. Pour un handle autonome restitué depuis un
  paramètre, la création directe substitue les pools de l’argument.
  Les appels synchrones qui relaient la tâche et les sorties de
  boucle async conservent les pools déjà résolus.
  L’inférence des fabriques publie aussi les pools des handles
  que la tâche créée peut restituer.
  Le transport via un `join()` synchrone reste ouvert.
- **N4, N5 et N8.** Une tâche attendue dans un contexte async peut restituer
  un `AsyncHandle` dont les emprunts proviennent de paramètres
  empruntés. Le handle reçu maintient les réservations des arguments
  jusqu’à sa propre attente. Pour un lancement suivi de `.await`,
  le bras `Ok` reprend les réservations et `LaunchFailed` les libère.
  Un handle retourné peut lui-même produire un emprunt scalaire
  de provenance paramétrique. Les jonctions et les relais purs
  propagent la projection de cet emprunt. Le contrat et
  l’abaissement transportent les écritures ordinaires de champs
  jusqu’à l’attente du handle intérieur. Le bras `Ok` affine
  les champs écrits par tous les handles possibles. Les
  écritures gardées disposent d’un contrat paramétrique pour
  les cibles intermédiaires et finales. L’abaissement les
  transporte jusqu’à l’attente du handle intérieur et affine
  l’état après `Ok` quand chaque chemin garantit l’écriture.
  Une tâche qui attend puis retransmet ce handle conserve
  les cibles intermédiaires et finales ainsi que les écritures
  garanties sur tous les chemins. Les remplacements de champs
  propriétaires transportent aussi leurs provenances de stockage.
  Le succès affine la provenance du champ quand le remplacement
  est garanti. Pour les structures, enums et tables construits dans
  l’abaissement async, le graphe distingue le stockage de base des
  liens de stockage des champs ou entrées. Un remplacement retire
  l’ancienne provenance si aucun de ces liens ne la retient.
  Les jonctions et reprises de boucle conservent les provenances
  possibles. Pour un vecteur d’allocations, le contrat d’un handle
  retourné propage les pools des éléments qu’il peut installer jusqu’à
  l’attente intérieure. Ce suivi est agrégé. La précision par position
  pour les vecteurs de valeurs inline reste ouverte.
  Les effets HashMap d’un handle retourné suivent les chemins
  de mutation jusqu’à son attente. Les clés constantes restent
  distinctes. Une clé dynamique conserve les dépendances possibles.
  Le contrat de terminaison relaie les mutations d’une table injectée
  produites par cette attente. Il conserve aussi le chemin sans mutation
  en cas d’échec de lancement. Le suivi précis de l’entrelacement avec
  les mutations directes et le raffinement par bras restent ouverts.
- **N4 et N8.** Le contrôle de destination traverse les valeurs
  portées par les écritures différées et leurs descendants. Pour
  une écriture gardée, il vérifie aussi la charge protégée et les
  dépendances transitives des cibles installées.
- **N4 et N5.** À la sortie d’un bloc async, le contrôle vérifie
  que les réservations survivantes ne visent pas un scalaire ou
  un tableau local de ce bloc.
- **N4 et N5.** La destruction synchrone d’une cible vérifie
  les dépendances des tâches vivantes. Le contrôle d’abandon
  consulte les cibles et pools retenus. Un scalaire numérique
  emprunté reste aussi protégé contre un `drop` explicite.
- **N4, N6 et N8.** Le remplacement d’un receveur à une jonction
  vérifie les dépendances transitives, y compris les effets différés
  du résultat. Les résultats de `if` conservent ces obligations
  dans la même représentation que ceux de `match` et de boucle.
- **N5 et N8.** Les destinations d’écritures différées ordinaires
  participent au contrôle des accès tant que la tâche ou son
  handle est vivant, même après la dernière mention de sa liaison.
  La vérification d’un appel les compare aussi aux graphes des
  autres arguments, notamment aux dépendances des autres handles.
  Un appel synchrone depuis une tâche peut relayer un handle à
  écriture gardée si le contrat restitue ce seul handle sans
  l’attendre et que les autres arguments sont des scalaires.

- [x] Backend Rust, V3. La déclaration et le passage par valeur déplacent
  un primitif. `copy(x)` conserve la liaison primitive et refuse un tableau.
  Ces quatre formes ont été rejouées avec `check`.

Le contrôle de destination vérifie aussi les pools du résultat différé
et les instances associées aux verrous que ce résultat peut porter.
À la fermeture d’un scope, les pools encore requis sont calculés en
parcourant les liens de possession des allocations vivantes. Ce parcours
sert aussi au contrôle de destination des transferts et des mises à jour
différées. Les pools des valeurs que ces mises à jour peuvent installer
restent requis tant que le handle porte l’effet.
La fermeture d’un bloc suit aussi les liens d’emprunt des groupes
survivants et vérifie la durée de vie de la racine d’une projection.
Le contrôle de destination applique la même vérification aux cibles
directes et aux projections transportées par une mise à jour différée.
La fermeture d’un bloc et les transferts utilisent le même parcours
des cibles retenues, y compris celles d’un descripteur imbriqué.
Pour N5, la validité d’une réservation projetée est lue sur sa racine.
Une capture exclusive reste exclusive si son origine ne suffit pas à
établir la dérogation de lecture partagée.
Pour N5 et N8, le contrôle des arguments d’un appel qui transmet un
handle à écriture gardée utilise ces mêmes liens de stockage et les
verrous portés par le handle et son résultat.

- **N4.** Les dépendances des initialiseurs de champs passent par le contrôle
  de durée de vie de l’agrégat. Les paramètres AsyncHandle autonomes
  admettent aussi un résultat tableau scalaire. Un appel synchrone peut
  recevoir un handle à effets gardés si son contrat décrit l’attente
  ou le relais. Les autres handles, emprunts et valeurs propriétaires
  doivent rester disjoints des instances gardées et de leurs charges.
  Un pool peut aussi être passé si son contrat préserve les stockages
  réservés. Les transferts contrôlent aussi la durée
  de vie des cibles et des pools des écritures différées. Le transfert
  d’un handle autonome vers une tâche inactive efface la copie source et
  comptabilise l’abandon possible si la frame est détruite avant le démarrage.
  L’attente directe d’un appel async peut transférer plusieurs handles à
  dépendances si le receveur les attend dans sa séquence d’ouverture et
  si la préparation des arguments suivants se termine immédiatement.
  Les calculs scalaires sans appel font partie de cette préparation.
  Cette séquence peut traverser des blocs, des `yield` et des liaisons
  littérales. Elle peut se terminer par un `match` direct de l’attente.
  Ce trajet conserve les réservations jusqu’à la fin. Il couvre les
  résultats scalaires, tableaux scalaires ou `Void` du receveur et les mises à jour
  différées sur les handles capturés, y compris celles sur un mutex
  local. Le receveur peut utiliser ou retourner l’emprunt numérique
  rendu par un handle. Dans le second cas, l’appelant conserve la cible
  au-delà de l’attente extérieure. Si la charge du handle est copiée,
  le receveur peut aussi retourner une allocation ou un autre
  `AsyncHandle` dont l’autonomie est vérifiée.
  Les autres trajets de handles à dépendances restent ouverts.
- **N5.** Le compilateur reconnaît `match &*vue` et suit le réemprunt d’une
  référence nominale stockée dans une entrée de HashMap. Les écritures
  directes détectées via une capture mutable nominale de closure utilisent
  le réemprunt mutable d’un champ. Une seconde acquisition en async est
  refusée si la première garde retient la même instance. Le déplacement
  de la garde transmet sa réservation. Pour les closures, l’inférence
  du receveur mutable suit aussi les alias locaux et les projections
  vers une écriture ou un appel mutable. Les résultats de blocs, `if`,
  `match` et `break` transportent aussi la provenance de capture.
  Les réaffectations d’alias sont fusionnées à la sortie des branches
  et des blocs. Les reprises de boucle propagent les origines jusqu’à
  stabilisation. Les sorties reprennent les origines présentes au
  `break` ou à l’arrêt du `while`. La valeur portée par un `break`
  est analysée avec les origines stabilisées, y compris celles
  propagées par une itération précédente. Une expression terminale
  de bloc utilise les origines fusionnées après les branches qui
  l’atteignent, y compris dans un bloc annoté pour le stockage.
  Les appels à une closure capturée utilisent le mode de son
  receveur. Les méthodes résolues sur les alias utilisent aussi
  les modes de leurs paramètres explicites.
  Les alias de capture suivent aussi les réemprunts explicites et les
  projections de références dans les tableaux, avec le type de l’élément.
  Les captures propriétaires numériques utilisent cette analyse pour
  choisir le réemprunt mutable du champ en cas d’écriture détectée.
  Le choix du receveur mutable tient aussi compte des signatures
  d’emprunt mutable de tableau et des opérations de tableau qui
  réservent ou modifient la projection capturée.
  Avant l’inférence des contrats, un retour emprunté est considéré
  comme un alias possible si l’appel reçoit un argument emprunté
  issu d’une capture. Le choix du receveur utilise cette approximation.
  Une tâche peut recevoir localement le résultat propriétaire d’une
  méthode synchrone annotée `lock`. Le compilateur conserve la
  réservation jusqu’à la destruction de la liaison et vérifie la
  réacquisition sur la même instance. Le déplacement vers une autre
  liaison locale ou vers un bloc parent conserve la réservation et
  exige que l’instance survive au nouveau receveur. Une fonction synchrone
  appelée depuis la tâche peut consommer ce résultat ou le restituer
  directement. Le compilateur suit la réservation et vérifie les effets
  de copie. Les contrats indirects des fonctions synchrones s’appliquent
  aussi aux appels depuis une tâche. Ils décrivent les acquisitions,
  les instances distinctes et les réservations transportées par un
  résultat propriétaire direct. Un résultat portant un verrou peut
  être transféré à une tâche enfant qui le consomme localement et
  retourne un scalaire ou `Void`. La réservation suit la tâche jusqu’au
  nettoyage ou à l’attente. Si l’enfant retourne directement le
  paramètre propriétaire, la réservation suit le résultat de l’attente.
  Le même suivi couvre un appel de retour synchrone dont le contrat
  restitue l’argument sans copie ni effet de verrou supplémentaire.
  Un retour via une tâche descendante attendue directement peut aussi
  transmettre la réservation si le contrat de provenance suit les
  paramètres transférés. Une tâche peut aussi retourner une valeur qui
  maintient un verrou nouvellement acquis sur une instance empruntée
  à un paramètre. Le contrat transmet cette provenance aux appelants
  directs et aux fabriques dont la capture d’origine est déterminée.
  Un handle public conserve cette capture de résultat quand son type
  efface la tâche concrète. Le relais via un handle lancé dans l’enfant
  reste ouvert.
  Une référence numérique mutable transférée dans une closure peut être
  réempruntée en écriture. Le contrat conserve la réservation du champ
  et la provenance de sa cible si le réemprunt est retourné.
- **N6.** L’affectation dont la partie droite est un résultat propriétaire
  passe par le remplacement après évaluation, y compris pour un appel,
  une méthode ou une expression de contrôle et un receveur ancêtre.
  Le remplacement relit la liaison dans son scope après l’évaluation
  et détruit l’ancienne allocation seulement si elle y est encore détenue.
  Les jonctions exigent une allocation vivante sur chaque chemin qui
  continue. Elles fusionnent les provenances par position quand les
  chemins donnent une disposition compatible.
  La convergence des boucles tient compte des obligations de verrou
  et de stockage transportées, y compris dans une valeur imbriquée.
  Une attente possible
  déclarée par un contrat propage les effets gardés en conservant les deux
  issues. Les résultats de `join` propagent aussi l’état gardé jusque dans
  les bras qui distinguent la réussite de l’échec du lancement, y compris
  quand la charge est une vue empruntée à une capture. Après `.await`, les
  mises à jour ordinaires des champs empruntés conservent aussi leurs états
  distincts jusqu’au `match`. Le même suivi existe après `join` lorsque
  le contrat de la branche détermine les changements. Le suivi synchrone
  inclut les champs propriétaires et leurs pools. En async, le `match`
  affine les pools par champ lorsque la provenance initiale du champ est
  suivie. Après `join`, le résultat permet aussi de retrouver les positions
  et les provenances des éléments d’un vecteur lorsque le contrat les
  détermine. En async, un emprunt mutable conserve les positions déjà
  connues si les contrats de terminaison et de suspension établissent
  que la tâche ne modifie pas les éléments. Une attente directe
  reconstruit aussi les positions après des retraits exacts sans ajout
  ni remplacement. Après une attente faillible, le `match` distingue
  les positions initiales et celles après retrait. Les ajouts et
  remplacements exacts reconstruisent les positions si le contrat
  identifie les valeurs et leurs dépendances. Une valeur issue d’une
  case suivie reprend les dépendances de cette case, y compris pour un
  dernier élément calculé par le contrat. Les mutations à provenance
  indéterminée restent ouvertes. Pour un vecteur créé dans la tâche,
  les positions exactes reconstruisent aussi les emprunts et les
  pools de ses éléments, en conservant le pool du vecteur lui-même.
- **N8.** L’inférence des contrats de branche suit les alias locaux, les
  résultats de match, les reprises de boucle et les handles fournis par
  les `break` d’une expression de boucle. Elle rattache aussi le
  lancement à un paramètre de tâche concrète déplacé dans un bloc
  enfant, ou à une tâche inactive fournie par un `if`, un
  `match` ou un `break`. L’inférence résout aussi les fabriques
  synchrones de tâches et les auxiliaires de lancement sans
  annotation redondante. Un relais qui retourne un paramètre
  de handle préserve l’origine de l’argument correspondant.
  La forme `join=result.await` vérifie aussi les fonctions
  async qui lancent puis retournent un `AsyncHandle`, y compris
  via l’attente directe d’une tâche inactive ou le bras `Ok`
  d’une attente de tâche lancée. Les captures de handles résolues
  à la création de la tâche survivent au lancement et à l’attente.
  Les relais synchrones de tâches et de handles conservent aussi
  la provenance de leur résultat différé.
  Les paramètres de closure
  conservent leur mode d’emprunt. Un gabarit inutilisé peut représenter le
  résultat partagé d’une closure par une capture symbolique et
  inclut tous les paramètres de même type parmi les provenances
  possibles. Si le mode de passage permet d’invoquer la closure
  avec un receveur mutable, le gabarit représente aussi le
  réemprunt d’une capture numérique ou nominale mutable.
  Les contrats d’insertion HashMap peuvent
  reporter des cibles nominales, référencer un paramètre de clé et suivre
  les sorties anticipées. Un appel relais peut fournir une clé constante.
  Seuls les arguments dont le contrat utilise la provenance doivent
  remonter à un paramètre du relais. Une tâche attendue directement peut retourner
  un `AsyncHandle` autonome à résultat scalaire, tableau scalaire ou `Void`.
  L’attente d’une tâche lancée séparément peut aussi livrer ce handle
  dans `Ok`, en async ou via `join` en contexte synchrone. Le receveur
  synchrone peut le transférer à une tâche async. La signature publique
  `Handle<AsyncHandle<R>>` conserve le type du handle intérieur à travers
  un relais. Les handles à dépendances et les autres effets aux frontières
  restent ouverts.

L’emprunt `.vref()` directement dans un champ est un témoin de construction
typée et de durée de vie (N1 et N4). Les opérations HashMap en async restent
des cas d’intégration à exercer sous N4, N5, N6 et N8 selon l’opération.
Un emprunt partagé de HashMap à valeurs scalaires ou références scalaires
partagées peut maintenant être capturé, transmis à une autre tâche ou
passé à une fonction de lecture synchrone. Une tâche peut aussi faire
un `match` direct sur `get` ou `get_mut` pour lire ou modifier une valeur
numérique. La vue réserve la table dans le bras `Some`. Une table à
valeurs scalaires peut être construite localement ou capturée en mutable.
`insert` et `remove` renvoient l’ancienne valeur scalaire. Les résultats
de ces quatre opérations peuvent être reçus dans une liaison avant le
`match`. Une recherche nommée réserve la table dès son évaluation.
Le résultat scalaire de `try_insert` peut aussi être traité dans un
`match` direct ou nommé. Les bras `Ok(Some)`, `Ok(None)` et `Err`
distinguent l’ancienne valeur, l’absence d’ancienne valeur et la valeur
refusée. `get` sur une table de références partagées scalaires est
raccordé au `match` async. Le bras `Some` peut lire la cible avec `**`.
Il peut aussi copier la référence avec `*` pour les types d’emprunt
déjà pris en charge. Pour une table de `A<T>` numériques, `get` lit
la cible et `get_mut` permet de modifier son contenu. Ces accès
conservent la provenance de l’allocation stockée. Une table locale à
la tâche accepte aussi l’insertion, le remplacement et l’extraction
d’allocations numériques. Le compilateur conserve les pools d’origine
des résultats et raccorde leur nettoyage. Pour une clé connue,
`remove` retire la dépendance propre à l’entrée du graphe de la table
et la conserve dans le résultat. Le `match` de `try_insert` distingue
la mise à jour en `Ok` de la table intacte en `Err`, tant qu’une
mutation ultérieure n’a pas rendu l’effet obsolète. Les clés dynamiques
gardent des provenances conservatrices.
Les tables locales à références partagées scalaires suivent aussi les
emprunts par entrée pour `insert`, `try_insert` et `remove`.
Le `match` transfère au receveur les dépendances de la référence extraite.
Une fonction synchrone appelée par la tâche peut insérer des références
dans une table locale reçue par emprunt mutable. Le compilateur applique
les chemins de son contrat à la table. Un appelant synchrone peut aussi
récupérer au `join` l’effet d’une insertion directe de référence
dans une table capturée par emprunt mutable. Le contrat suit les
branches et les suspensions `yield` du corps pris en charge.
Une tâche appelante applique aussi ces effets sur sa table locale au
terme d’un `.await` direct ou d’un `execution.await`. Pour un handle
lancé, le `match` distingue le succès de `LaunchFailed`. Une tâche
intermédiaire peut relayer sa table injectée à une fonction synchrone
ou à une tâche enfant attendue directement. Les contrats remappent
les paramètres de bout en bout. Le relais via un handle lancé
couvre le `match` direct, le handle nommé et le résultat d’attente
nommé, avec des `yield` possibles entre ces étapes. Les chemins
`Ok` et `LaunchFailed` publient des effets distincts. Les handles relayés par des expressions
plus générales et les mutations d’entrées propriétaires restent ouverts.
Les contrats de mutation des tables de références couvrent aussi
`remove(&clé)` en instruction. Si la clé est connue à l’appel, l’effet
de terminaison retire la dépendance correspondante de la table.
Une tâche peut aussi insérer un paramètre `A<T>` numérique transféré,
ou retirer et détruire en instruction une entrée numérique propriétaire
d’une table empruntée. Le contrat publie ces effets dans le graphe des
allocations au `join` ou au `.await`, avec contrôle du pool de l’entrée.
Le `match` de `try_insert` sur une table empruntée publie l’insertion
pour `Ok` et préserve les dépendances antérieures pour `Err`. Les valeurs
extraites peuvent être nettoyées dans les bras. Le retour interprocédural
des valeurs extraites reste ouvert.
La revue n’a relevé aucun chantier autonome pour N1, N2, N3 ou N7.
Cette observation ne vaut pas validation exhaustive de ces règles.

- [x] **Directives source et contrats de type de fonction.** Deux-points
  après `directive`, gabarits `K/M/G`, spécialisation de `#(type: T<R> with {...})`
  sur les types nominaux et sur les Futures du runtime intégré. Les tests
  ciblés couvrent aussi les deux formes de `lock` et les tranches descendantes.
  [Rapport](cycles/CORE_ANNOTATIONS_CYCLE.md)
- [x] **Retour d'enum depuis un pool.** Test migré en `A<E>` et validé
  sous UBSan. La suite générale a terminé. Ses 145 tests en échec échouent
  aussi sur le compilateur avant ce correctif.
  [Rapport](cycles/ENUM_CORE_VALIDATION_CYCLE.md)
- [x] **Marqueur `lock` (MT10).** Contrats synchrones et passage en argument
  par emprunt ou transfert direct. Capture async propriétaire, nettoyage d'une
  tâche non lancée, attente par `join()`, restitution directe et `LaunchFailed`.
- [x] **HashMap V1.** HM1–HM6 raccordées aux opérations source du périmètre
  exercé. Prêts sur la table, remplacement et extraction, dépendances des clés
  connues, stabilité des entrées et échec transactionnel.
- [x] **Retours d'emprunts numériques depuis async.** Retours partagés et
  mutables de types larges, par `.await` direct et via les handles.
  Provenance, cible locale et réservations exercées dans le lot ciblé.
- [x] **Charges de mutex avec dépendances.** Structures représentées
  contenant un emprunt et une allocation possédée, réemprunts de garde,
  partage du mutex, mutation de la cible empruntée sous garde et nettoyage.
- [x] Propager les changements de provenance lors du remplacement d'un
  champ emprunté ou possédé par la garde d'un mutex local sans autre emprunt.
  Couverture sync et async, en affectation directe et via un auxiliaire sync.
- [x] Propager le remplacement d'un champ `&i32` par une tâche Void au
  contrat et au `join()` synchrone. Succès et `LaunchFailed` injecté,
  avec vérification des dépendances de chaque bras.
  [Rapport](SAFETY.md#effets-de-dépendance-des-tâches-sous-garde)
- [x] Appliquer le même effet à `execution.await`. Vérifier le succès,
  `LaunchFailed` et les réservations du mutex et de ses cibles.
  [Rapport](SAFETY.md#effets-de-dépendance-après-executionawait)
- [x] **Placement anticipé sur la datastack.** Corriger le refus d'un retour
  de valeur locale lorsqu'un `if` de lecture précède ou suit sa création.
  Les prochains changements de placement sont limités aux cas valides
  reproduits qui échouent encore.
- [x] Rejouer les régressions de ce lot sous UBSan. 24 méthodes ciblées
  à `-O0` et 190 à `-O2` passent, ainsi que les compléments de placement
  et de retours d'emprunts. [Rapport](SAFETY.md#cycle-des-retours-async-et-charges-gardées)

## Alignement et validation du core

- [x] Trier les 145 tests en échec de la passe générale par premier blocage.
  [Inventaire par test](CORE_FAILURE_TRIAGE.md)
- [x] Corriger les coordonnées de projection des emprunts de tableau
  retournés en async. Valider `.await`, `join()`, la réservation et
  `LaunchFailed`.
- [x] Raccorder le résultat `bool` à travers `match h.await` et typer les
  branches booléennes d'un `if` avec suspension.
- [x] Refuser une annotation scalaire `i32` sur une valeur `A<i32>`.
- [x] Appliquer le type de l'élément au littéral affecté à une case de
  tableau `i32` dans une fonction async.
  [Rapport des quatre corrections](cycles/CORE_INTEGRATION_FOLLOWUP_CYCLE.md)
- [ ] Migrer les fixtures historiques portant des invariants actuels,
  corriger les oracles, puis rejouer les variantes et les cas mixtes.
- [x] Accepter les annotations d’emprunt dans `let` et typer un littéral
  affecté via `mut_vref()`. Vérifier le mode, le type et la durée de vie
  de l’emprunt. [Rapport](SAFETY.md#annotations-demprunt-et-littéraux-à-travers-mut_vref)
- [x] Aligner treize exemples du noyau sur les déplacements par valeur et
  les primitifs cibles. Exercer `i64` et `f64` sans annotation et ajouter
  les variantes modernes des deux fixtures d'agrégats async. Les fixtures
  d'origine conservent leur syntaxe pour les tests du profil historique.
- [x] Distinguer le runtime intégré dans la grammaire et les points d'entrée
  du compilateur. `--experimental-scheduler` active les entrées du prototype
  historique. Le remplacement public du runtime reste reporté.
- [x] Rejouer `test_async_owned_struct_returns` et
  `test_async_owned_struct_sync_calls` après correction des signatures de
  fixtures vers `A<T>`. Les 26 tests passent à `-O0`.
- [x] Rejouer les cas du noyau après intégration et vérifier leur traçabilité.
  UBSan et les oracles natifs passent sur 29 tests ciblés à `-O0`,
  170 tests à `-O2` et 137 tests du profil historique.
  [Matrice](VERIFICATION_MATRIX.md#clôture-du-lot-dintégration-du-noyau) ·
  [Rapport](SAFETY.md#clôture-du-lot-dintégration-du-noyau)
- [ ] Reprendre ASan dans un environnement où le témoin termine. Sur cette
  machine le témoin minimal compile et dépasse le délai de cinq secondes.

## Intégré et exercé

Le [rapport du cycle noyau](SAFETY.md#cycle-de-validation-du-noyau-mémoire--8-novembre-2026)
sépare les résultats du profil courant de ceux du profil historique avec reset.

- [x] Relier N1–N8 aux règles retenues et à des cas admis et refusés.
- [x] Exécuter les dix programmes C ciblés et vérifier les dix-neuf variantes
  invalides aux deux points d'entrée.
- [x] Corriger le suivi du receveur masqué dans un bloc enfant et vérifier
  les chemins qui atteignent son usage extérieur.
- [x] Rejouer les suites de stockage, suspension, thread natif et réveils.
- [x] Exercer la reprise, les réveils et le nettoyage du runtime intégré.
  Les passes de 70 méthodes à `-O0` et 124 à `-O2`, plus le test
  de chaîne `.await` aux deux niveaux, passent sous UBSan.
  [Rapport du runtime intégré](SAFETY.md#cycle-du-runtime-intégré--9-novembre-2026)
- [x] Rejouer les régressions de contrats, de contrôle de flux et d'usage
  des receveurs. Les quatre passes finales totalisent 208 méthodes réussies.
- [x] Intégrer et exercer les déplacements par valeur et les blocs `move`
  dans le périmètre du noyau. Voir le [rapport des déplacements](SAFETY.md#cycle-des-déplacements-par-valeur).
- [x] Définir les primitifs numériques et logiques du noyau cible dans le
  [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau).
- [x] Exercer les primitifs numériques, leur typage contextuel et les
  vérifications arithmétiques dans le profil `--numeric-core`.
- [x] Exercer les conversions exactes, la sélection d'une case et les
  affectations composées sur variables et tableaux fixes, y compris à
  travers `.await`, ainsi que le réemploi des slots des pools numériques.
- [x] Raccorder les champs numériques, les allocations et conversions async
  et les affectations composées sur champs et déréférencements dans le
  [périmètre testé](SAFETY.md#cycle-dintégration-du-noyau--9-novembre-2026).
- [x] Raccorder les emprunts directs des champs numériques larges, leurs
  retours synchrones et les paramètres empruntés des tâches.
- [x] Écrire la [grammaire EBNF du noyau](../CORE_GRAMMAR.ebnf) avec les formes
  async, puis vérifier une sélection de syntaxes admises et refusées.
- [x] Consigner et vérifier dans la grammaire les littéraux flottants et
  les deux formes de capture des threads natifs.
- [x] Intégrer les littéraux flottants au profil numérique.
- [x] Intégrer et exercer les formes modernes de capture de thread natif.
- [x] Arbitrer les constructeurs publics des mutex synchrones et asynchrones.
- [x] Raccorder et vérifier les nouvelles formes source dans l'EBNF du noyau.
- [x] Raccorder les constructeurs de mutex à charge scalaire, la destruction
  des gardes et le réemprunt async de `i32`.
- [x] Raccorder les mutex à charge structurelle composée de scalaires et
  les réemprunts des gardes numériques larges.
- [x] Réserver dans le parent le résultat local d'un `if` dont l'autre
  branche quitte la fonction.
- [x] Valider ce lot sur 19 méthodes à `-O0`, puis 219 méthodes à `-O2`
  et les compléments de placement et d'emprunts. Le rapport conserve
  aussi les échecs des deux suites historiques d'agrégats async.
- [x] Raccorder la frontière C scalaire et le build avec `--c-source`.
- [x] Rejouer la passe d'intégration et la régression du noyau. 13 méthodes
  ciblées à `-O0` et 213 à `-O2` passent, avec UBSan pour l'oracle C.

État historique après le lot [champs propriétaires dans Vector<T>](cycles/INLINE_VECTOR_OWNED_CYCLE.md).
19 méthodes ciblées réussies ; régression de 236 méthodes avec quatre fixtures
historiques corrigées et rejouées, complément régions de 35 méthodes réussi.
Cette synthèse regroupe les chantiers ; les preuves et limites détaillées restent
incluses dans [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) et les rapports.
« En place » signifie implémenté et testé dans un périmètre consigné, pas que
toutes les compositions sont couvertes. L'objectif global reste ouvert.

## État par chantier

| Chantier | Déjà en place | Travail encore ouvert |
| --- | --- | --- |
| Compilation et cœur | CLI, vérification, génération C, main synchrone, binaire ; contrôle de flux, fonctions, expressions | Généralisation des types/signatures dans les compositions restantes |
| Transferts et destruction | Déplacements par valeur et blocs `move`, réception, drop, nettoyage par scope, return/break/continue | Les fixtures de compatibilité exercent encore les flèches historiques |
| Emprunts et contrats | Dernière utilisation, exclusivité, provenances multiples, contrats inférés et vérification des appels | Dépendances des agrégats/collections complexes et certaines interactions async |
| Tableaux fixes | Tableaux imbriqués, références et lignes référencées, copies explicites, écritures et retours | Voir le périmètre et les écarts de FIXED_ARRAYS_VALIDATION.md ; pas une promesse pour tout type d'élément |
| Structures, enums, méthodes | Construction complète, défauts, méthodes, copies, champs empruntés et propriétaires, plusieurs graphes récursifs | Retours nominaux T/A<T> raccordés ; compositions générales avec collections et async restantes |
| UTF-8 et conversions | str, char, String, vues/découpes, mutations UTF-8 vérifiées, as/try_from, résultats faillibles | Formes et types non encore raccordés, interactions générales avec les collections |
| Vecteurs | Int/u8 et vecteurs de références dans le périmètre testé ; handles Int et plusieurs autres charges | Graphes de handles et structures en ligne à champs représentés, y compris propriétaires, raccordés dans les lots consignés ; autres champs/opérations et intégration générale restants |
| Résultats de vecteurs typés | Push/remove, pop Option<A<T>>, replace et try_push synchrones ; captures, push/remove/pop et replace locaux dans les états async ; options et échanges typés à travers paramètres, retours et join testés | Dépendances locales des charges raccordées et testées ; retours synchrones de conteneurs raccordés ; async et compositions générales restants |
| Stockage | Data stack implicite, pools typés, slots libres, adresses stables et régions dans le prototype historique | Modèle cible à deux data stacks et curseurs à sens unique consigné. Placement, récupération de région après nettoyage des threads et mesures de performance à intégrer. |
| Type features et directives | Forme historique à une méthode, contrats de type locaux à une fonction avec plusieurs méthodes, résolution statique, directives source à deux-points | Contrats de type avec un paramètre associé dans le périmètre exercé |
| Async et Select | Frames typées et pools d'états, yield/await, captures et transferts, contrats de suspension, résultats, nettoyage des perdantes | Signatures/captures générales, nouvelles charges de collections, certains effets de champs et graphes complexes |
| Runtime et threads | Runtime intégré, `spawn`, `spawn_blocking`, thread natif, handles, retours empruntés numériques larges, contexte de poll interne, reprise, réveils et nettoyage dans les cas exécutés | Le remplacement du runtime est reporté. |
| Mutex | Constructeurs scalaires, structures à dépendances, remplacement sous garde locale et propagation d'un champ partagé `&i32` après `join()` et `execution.await` | Accès concurrents pendant un remplacement et autres projections ou types pour cet effet |
| Frontière C | Signatures scalaires et Void, bloc unsafe lexical, contrôles de type et de finitude, build avec plusieurs sources C | Autres ABI et types hors de cette frontière |
| Validation | Tests acceptés/refusés, C natif et UBSan, régressions, matrice et rapports par lot | Rejeu ASan et audit indépendant |

## Lots récents terminés dans leur périmètre

- [x] Champs propriétaires des structures en ligne : push/remove, destruction
  des cases, contrats et async — INLINE_VECTOR_OWNED_CYCLE.md.
  16 exécutions ciblées et 14 invalides ; régression de 236 méthodes avec
  correction/rejeu des anciennes signatures Node/A<Node>, complément de 35.

- [x] Références nominales dans les structures en ligne : cibles entières et
  intérieures, copies partagées, réemprunts mutables, contrats et async —
  INLINE_VECTOR_NOMINAL_CYCLE.md. 11 exécutions ciblées, 20 invalides ;
  121 méthodes de régression O2/UBSan réussies.

- [x] Champs &Int et &mut Int des structures en ligne : push/copy/remove,
  contrats synchrones, cibles réservées, captures et résultats async —
  INLINE_VECTOR_BORROWS_CYCLE.md. 20 exécutions ciblées et 32 invalides ;
  régressions finales de 194 et 85 méthodes réussies.

- [x] Transferts nommés vers Vector<T> à feuilles Int : scopes, emprunts,
  relais synchrones, captures async et exigences de stockage inférées —
  INLINE_VECTOR_MOVES_CYCLE.md. 15 exécutions ciblées, 19 invalides aux deux
  entrées ; 126 méthodes de régression O2/UBSan réussies.

- [x] Extraction de structures en ligne — INLINE_VECTOR_REMOVE_CYCLE.md :
  remove, drop direct, réceptions parent/if/break, retours synchrones et type feature ;
  huit méthodes ciblées réussies, 185 méthodes de régression O2/UBSan réussies.

- [x] Premier périmètre de structures directement en ligne dans Vector<T> — INLINE_STRUCT_VECTORS_CYCLE.md :
  insertion/copie des structures à feuilles Int, sorties de blocs et retours synchrones ;
  huit méthodes ciblées réussies ; régression de 373 méthodes, une fixture
  préexistante corrigée, complément de 30 méthodes réussi. Généralisation encore ouverte.

- [x] Résultats propriétaires à profondeur variable — RECURSIVE_OWNED_JOIN_CYCLE.md.
- [x] Opérations synchrones sur des vecteurs de handles typés — TYPED_HANDLE_VECTORS_CYCLE.md.
- [x] Résultats typés replace/try_push synchrones — TYPED_VECTOR_EXCHANGES_CYCLE.md.
- [x] Contrats synchrones Option<A<T>>, y compris None typé — TYPED_VECTOR_OPTIONS_CYCLE.md.
- [x] Retours nominaux T/A<T> explicites et implicites, contrats et relais — STRICT_STRUCTURE_RETURNS_CYCLE.md.
- [x] Suivi de mise à jour d’un champ quand le nom du porteur est masqué — même cycle.
- [x] Captures, pools locaux, push/remove/pop et replace locaux de vecteurs typés en async — TYPED_ASYNC_HANDLE_VECTORS_CYCLE.md.
- [x] Options async typées, enveloppes imbriquées, captures et handles publics — TYPED_ASYNC_OPTIONS_CYCLE.md ; huit méthodes ciblées, 119 en régression.

- [x] Échanges async typés replace/try_push, enveloppes, captures, handles publics et nettoyage Select — TYPED_ASYNC_EXCHANGES_CYCLE.md ; neuf méthodes ciblées, 135 en régression.

- [x] Graphes des éléments de vecteurs locaux, extractions et retour de l’objet extrait — VECTOR_PAYLOAD_GRAPHS_CYCLE.md ; onze méthodes ciblées et régression consignée.

- [x] Contrats des éléments de vecteurs empruntants/propriétaires — VECTOR_PAYLOAD_CONTRACTS_CYCLE.md ; dix méthodes ciblées, 145 en régression O2/UBSan.

- [x] Options des éléments empruntants/propriétaires, retours et relais — VECTOR_PAYLOAD_OPTIONS_CYCLE.md ; sept méthodes ciblées, 152 en régression O2/UBSan.

- [x] Graphes des charges de replace/try_push, variantes, relais et capacités mutables — VECTOR_PAYLOAD_EXCHANGES_CYCLE.md ; sept méthodes ciblées, 159 en régression O2/UBSan.

- [x] Retours de vecteurs complexes, fabriques, relais et transformations — VECTOR_PAYLOAD_CONTAINERS_CYCLE.md ; neuf méthodes ciblées, 168 en régression O2/UBSan.

- [x] Graphes des vecteurs async, captures et opérations locales — ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md ; douze méthodes ciblées, régression de 264 et complément de 14 consignés.

- [x] Contrats d’insertion/extraction depuis async, graphes des descendants et pont C — ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md ; six méthodes ciblées et 270 en régression O2/UBSan.

- [x] Retours async de vecteurs, await/join, fabriques et transferts successifs — ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md ; dix méthodes ciblées et 280 en régression O2/UBSan.

- [x] Contrats publics runtime::Handle retournant des vecteurs et relais de handles — ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md ; quatre nouvelles méthodes ciblées et 284 en régression O2/UBSan.

- [x] Relais synchrones des Result contenant un vecteur async — ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md ; cinq nouvelles méthodes ciblées et 289 en régression O2/UBSan.

- [x] Captures et réceptions imbriquées de Result de vecteurs — ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md ; sept nouvelles méthodes ciblées et 296 en régression O2/UBSan.

- [x] Structures en ligne à feuilles Int dans les tâches async : création, captures, copy/remove et retours par await/join ; contrats publics Handle et relais Result — ASYNC_INLINE_VECTORS_CYCLE.md.

- [x] `match (-> résultat)` pour les Result de join : scalaires, Void, allocations,
  emprunts et valeurs locales ; échanges replace/try_push préservés —
  CONSUMING_JOIN_MATCH_CYCLE.md. 223 méthodes de régression couvertes après reprise ENOSPC.

- [x] Pop des structures en ligne, Option<T> distinct d’Option<A<T>>, champs,
  fonctions, await/join et handles publics — INLINE_VECTOR_POP_CYCLE.md.
  20 méthodes ciblées ; régression initiale de 361 puis rejeu corrigé de 173.

## Écarts hors du lot courant du core

- [ ] Éléments de vecteurs de handles contenant des champs empruntés ou
  propriétaires : opérations locales, contrats synchrones d’insertion/extraction
  et options/échanges Result raccordés dans les périmètres des rapports ci-dessus.
  Retours synchrones de conteneurs raccordés dans le périmètre du cycle dédié.
  Références nominales, consommateurs généraux et intégration async restent à compléter.
  Captures et opérations locales async raccordées dans le périmètre du cycle dédié.
  Appels synchrones depuis async raccordés et testés dans le périmètre
  ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. Retours async de conteneurs entiers
  raccordés dans ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md.
  Contrats publics de handles raccordés dans ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md.
  Relais synchrones du Result raccordés dans ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md.
  Capture/restitution du Result, réceptions imbriquées et captures successives
  raccordées dans ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md.
  Les trois cas minimaux de référence &Point et de consommation du Result par une
  tâche sont aussi exécutés avec succès en C O0/UBSan : complément consigné dans
  INLINE_STRUCT_VECTORS_CYCLE.md. Cela ne clôt pas les compositions générales.
- [ ] Vecteurs de valeurs structurées directement en ligne (VE1), distincts
  des vecteurs de handles : premier raccordement des feuilles Int et copies
  explicites dans INLINE_STRUCT_VECTORS_CYCLE.md. Autres extractions/remplacements,
  tranches et intégration générale async restent ouverts.
  Transfert nommé vers Vector<T> raccordé et testé dans INLINE_VECTOR_MOVES_CYCLE.md,
  avec propagation des exigences locales dans les contrats sync/async.
  Champs &Int et &mut Int, imbriqués inclus, raccordés dans
  INLINE_VECTOR_BORROWS_CYCLE.md : insertion/extraction, copies partagées,
  contrats et captures/résultats async. Références nominales représentées
  raccordées dans INLINE_VECTOR_NOMINAL_CYCLE.md : cibles entières et
  sous-structures, copie/extraction, contrats, captures et join.
  Précision des positions après appels et branches encore conservatrice.
  Champs propriétaires et nettoyage des descendants raccordés dans
  INLINE_VECTOR_OWNED_CYCLE.md : insertion/extraction, contrats et captures/join
  du périmètre testé. Graphes/types non représentés encore ouverts.
  Pop et Option<T> raccordés dans INLINE_VECTOR_POP_CYCLE.md, avec champs,
  fonctions, await/join et handles publics dans le périmètre exécuté.
  Replace local synchrone raccordé dans le checkpoint INLINE_VECTOR_REPLACE_CYCLE.md :
  sept méthodes ciblées, 142 en régression. Retours synchrones et paramètres
  Result<T,T> raccordés dans INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md :
  huit méthodes ciblées réussies, 17 exécutions C et six variantes invalides.
  Régression finale : 171 méthodes O2/UBSan réussies, 46 empreintes inchangées.
  L'intégration async reste ouverte, avec la fixture refusée
  validation/inline-vector-replace-async.crb.
  Try_push, tranches et push_new restent à raccorder.
  Remove des structures à feuilles Int est raccordé dans INLINE_VECTOR_REMOVE_CYCLE.md,
  avec 185 méthodes de régression réussies dans ce lot.
  Création, captures et extraction async des feuilles Int : ciblé réussi dans
  ASYNC_INLINE_VECTORS_CYCLE.md ; 226 méthodes de régression réussies.
  Le fichier historique open-inline-struct-vector.crb utilisait aussi une copie
  implicite interdite ; la fixture valide corrigée est inline-struct-vector.crb.
- [ ] Compositions async supplémentaires des types, captures, graphes de
  champs et résultats. Les rapports indiquent le périmètre de chaque famille.
- [ ] Vérification de complétude du projet, règle par règle, sur l'ensemble
  des sept brouillons et des règles consignées.

Cette liste d'écarts est un inventaire de pilotage des travaux connus. Elle ne
remplace pas l'audit de complétude ; il ne faut pas en déduire un pourcentage
fiable ou un nombre exhaustif de cas restants.

Les appels directs d’une `fn` synchrone depuis une `async fn` sont exclus
du core. Les anciens lots qui les mentionnent décrivent le prototype Python.

## Décisions ouvertes et éléments reportés


- Intégration de `SelectGroup` reportée.

- Remplacement du runtime dans `main` et interface publique de
  `runtime::Future` pour les runtimes personnalisés. Le compilateur
  contient encore le prototype `set_scheduler` et ses callbacks.
- Enrichissement des API de collections.
- Traits à plusieurs méthodes et relations entre types : reportés.
- Options d'ordonnancement de Select : reportées.

Voir [les points reportés du design](../design-buffer/points-ouverts.md).

Les itérateurs et `mut()` restent hors du prototype selon les décisions
consignées. Une perdante de Select conservant un handle lancé non attendu doit
être refusée ; ce refus retenu n'est pas une fonctionnalité manquante.

## Correspondance avec les sept brouillons

| Brouillon | Chantiers concernés / état |
| --- | --- |
| 01 — Résultats propriétaires | Usage explicite et destruction en place ; extension des résultats typés et compositions toujours partielle |
| 02 — Marqueurs de transfert | Déplacements par valeur, formes `move` et retour avec nouveau receveur intégrés dans le périmètre du noyau. Les flèches restent disponibles pour le code historique. [Brouillon 02](../design-buffer/02-marqueur-transfert.md) |
| 03 — Dépilement | Nettoyages et stockage local en place ; placement anticipé général incomplet |
| 04 — Async, runtime et Select | Runtime intégré et retours empruntés larges exercés dans les cas consignés. Compositions générales ouvertes et remplacement du runtime reporté. |
| 05 — Data stack et pools | Stockage, pools typés et retours nominaux T/A<T> en place ; placement général encore à compléter |
| 06 — Type features | Résolution statique historique à une méthode et contrats de fonction à plusieurs méthodes dans le périmètre testé |
| 07 — Conversions, copies et vues | Opérations retenues en place ; couverture des compositions et types partielle |
