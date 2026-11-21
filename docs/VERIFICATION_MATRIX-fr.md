## Permission de mutation — validation ciblée

MA1–MA6 remplace l’unicité implicite de `&mut`. Corboc sépare permissions,
effets/protection et dépendances. Neuf exécutions UBSan fatales et dix refus
attendus couvrent alias, verrou commun, fins de branche et nettoyage. Le cas
natif à trois threads passe sur macOS ARM64/x86-64, Linux x86-64 et Windows
x86-64 sous Wine. Windows ARM64 est compilé seulement. Les anciens verdicts
ci-dessous décrivent leurs cycles d’origine. Voir le rapport
`corboc/docs/MUTABLE_ACCESS_CYCLE.md` pour le périmètre et les limites.

[English](VERIFICATION_MATRIX.md)

# Matrice règles → vérification

[Checklist globale des chantiers](IMPLEMENTATION_CHECKLIST.md).

## Compositions du core

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| S5b, S5, N4–N6 | Propagation de `Result` et d'`Option`, résolution des surcharges par type source exact, `.await?`, nettoyage et transfert des ressources. Deux programmes générés en C sous UBSan à `-O0` et `-O2`, un paquet exécuté et quatorze refus statiques. | P · Compilateur Rust. S5b reste à intégrer au compilateur auto-hébergé. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#postfix-propagation-with-question-mark). |
| N4–N6, AS1–AS4, RT6–RT8, G2–G12, handles et états async en région | Dix témoins C sous UBSan à `-O0` et `-O2`, neuf refus ciblés. | P · Handles natifs conservés, captures scalaires ou emprunts de scalaires, Futures à `yield` au niveau du corps. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-et-contextes-async-en-région). |
| RT8, G2–G12, état régional d’un thread natif Rust | Cinq témoins C avec pthread sous UBSan à `-O0` et `-O2`, dont un échec de lancement injecté. Quatre refus ciblés. | P · Attente immédiate, captures scalaires nommées et datastacks isolées par worker. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#état-régional-des-threads-natifs). |
| G2–G12, HM1–HM5, VE1–VE2, régions des collections Rust | Sept témoins C sous UBSan à `-O0` et `-O2`, quatre refus ciblés et un dépassement de région. | P · Tables à valeurs primitives et vecteurs à références ou allocations. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#collections-à-dépendances-et-régions). |
| G2–G12, datastack à régions Rust | Sept témoins C, deux dépassements contrôlés et trois refus d’annotation. | P · `Vector<T>` à éléments fixes sans dépendances et `String` en pool dans le backend synchrone. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-régions-dans-le-backend-rust). |
| G2, G6, G10–G11, dimensionnement de la datastack classique | Dix témoins C instrumentés sous UBSan à `-O0` et `-O2`, six refus d’annotation. | P · Taille explicite, borne issue du plan post-AST et défaut. Appels récursifs accessibles traités conservativement. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dimensionnement-de-la-datastack-classique). |
| N4–N6, E6–E7 et G1, provenances par position | Huit nouveaux témoins C sous UBSan à `-O0` et `-O2` et six refus ciblés. | P · Contrats synchrones, champs et cases, réemprunts et motifs d’agrégats. Indices dynamiques et récursion non résolue traités conservativement. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#provenances-par-position-et-match-emprunté). |
| N4–N6, A1–A4, E6–E7, G1 et G10 dans le backend Rust | Quatorze témoins C sous UBSan à `-O0` et `-O2` et dix refus statiques. | P · Provenances agrégées conservatrices et transfert de la responsabilité de nettoyage d’un `A<T>`. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#dépendances-des-agrégats-et-transferts-de-pool). |
| G1, G2, G10 et placement des types fixes Rust | Huit nouveaux témoins C sous UBSan à `-O0` et `-O2`, huit refus statiques et quatre contrôles d’exécution ciblés. | P · Agrégats sans emprunts internes et pools locaux. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#extension-du-placement-des-types-fixes). |
| G1, placement fixe dans le compilateur Rust | Quatre témoins C sous UBSan et inspection des réservations émises. | P · Structures synchrones à champs scalaires et stockage automatique C. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#placement-fixe-dans-le-compilateur-rust). |
| G1, G2, G10–G12, datastack classique dans le compilateur Rust | Sept témoins C sous UBSan à `-O0` et `-O2`, plus deux contrôles à capacité réduite. | P · Types fixes actuellement abaissés par le backend synchrone. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#datastack-à-curseur-dans-le-backend-rust). |
| Représentations de scope, liaison, appel et capture | Aucun. | Projection syntaxique de 2 766 programmes et fragments sur 82 807 tokens. [Périmètre et limites](cycles/CORE_COMPOSITION_CYCLE.md#parcours-du-corpus-sans-arrêt-darbitrage). |
| Frontend Rust | Comparaison des représentations, sans programme exécuté. | 2 758 occurrences communes, 2 690 projections entièrement concordantes. [Périmètre et écarts](cycles/CORE_COMPOSITION_CYCLE.md#frontend-rust-et-comparaison-du-corpus). |
| Vérificateur Rust et C, N1–N8 | Quatre témoins C sous UBSan, six refus ciblés. | P · Sous-ensemble scalaire synchrone et emprunts locaux lexicaux. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#vérificateur-rust-et-génération-c-du-sous-ensemble-scalaire). |
| Vérificateur Rust, N5–N6 | Six témoins C sous UBSan, cinq refus ciblés. | P · Dernier usage de références locales et reprise des boucles scalaires. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#graphe-de-contrôle-dernier-usage-et-boucles-dans-le-rust). |
| Vérificateur Rust, N4–N6 et N8 | Huit témoins C sous UBSan, huit refus ciblés. | P · Réemprunts scalaires, paramètres, retours et boucles à résultat. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#réemprunts-contrats-de-références-et-boucles-à-résultat-en-rust). |
| N4, N5, N6, N8 | Aucun cas exécuté pour les derniers changements du compilateur. | Validation reportée à la demande de l’utilisateur. Avancement et limites dans le [rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md#implémentation-partielle-de-n4-n5-n6-et-n8). |
| N2, N4–N6 | Références scalaires capturées, transfert de référence mutable, appel de closure après `yield`, écriture avant et après `join`. | P · Périmètre scalaire. |
| N4, RT7–RT8 | Abandon d'un résultat de wrapper conditionnel, nettoyage et recyclage avant fermeture du contexte. | P · Captures et résultat scalaires. |
| HM1–HM6, N4 | Écritures HashMap propagées sur clés constantes, relais, alternatives conditionnelles et refus d'une cible trop courte. | P · Références scalaires partagées. |
| MT10 | Verrou relayé dans un champ propriétaire ou une option de vecteur, refus de reprise pendant la vie du ticket. | P · Trajets synchrones exercés. |
| RT4–RT5, RT7–RT8 | `spawn` et `thread` appelés en async, distinction locale avec `AsyncHandle` à travers déplacement, `if` et `break`, relais de wrappers annotés. | P · 8 tests à `-O0` et 24 à `-O2`. Passage d'`AsyncHandle` via une signature encore ouvert. |
| N2, N4–N6 | Une closure capture une référence partagée et appelle deux fois une fonction à contrat de type. Refus de la capture non Copy sans `move`. | P · Régression ciblée, témoin C sous UBSan. |
| N4, RT5, RT7 | Transfert d'un AsyncHandle autonome à un paramètre async, attente, LaunchFailed et destruction inactive. Abandon avec tableau numérique copié, refus avec tableau emprunté. | P · 10 tests à `-O0`, 66 à `-O2`. Handles à dépendances et retours ouverts. |
| AS7, RT7 | Abandons répétés dans des boucles sync et async, appels directs et via un auxiliaire sync, avec et sans capacité explicite. | P · 67 tests à `-O2`. Relais via des tâches async encore ouverts. |
| HM1–HM6, N4 | Lecture d'une entrée à référence scalaire via une table empruntée par une fonction. Mutations interdites jusqu'à la fin de l'emprunt. | P · 20 tests HashMap et lock à `-O2`, témoins natifs sous UBSan. |
| AS7, RT7 | Abandons relayés par une tâche async ou un wrapper branch appelé en async. | P · Test ciblé à `-O0` et 36 tests à `-O2`. Analyse conservative. |
| N1, N2, N4 | Signatures de closures avec structure empruntée en entrée ou structure à champs scalaires en résultat. Corps inutilisés vérifiés et retour exécuté en C. | P · 17 tests à `-O2`. Retours à dépendances encore ouverts. |
| N2, N4–N6 | Capture d'une référence mutable nominale et réemprunt en lecture dans la closure. Deux lectures, refus de l'ancienne liaison et de l'écriture, reprise après drop. | P · Témoin à `-O0` et 28 tests à `-O2`. |
| N1, N4–N6 | Emprunt retourné depuis le paramètre d'une closure, via une fonction. Dernière lecture et mutation après celle-ci. | P · 29 tests à `-O2`. Provenance d'une référence scalaire capturée encore ouverte. |
| N4–N6 | Référence scalaire partagée capturée et retournée, lecture après destruction de la closure, refus d'une écriture anticipée et d'une cible locale échappée. | P · 2 tests à `-O0` et 30 à `-O2`. Capture exclusive encore ouverte. |
| N4–N6 | Vue partagée retournée depuis une capture exclusive scalaire ou nominale. Refus d'écriture et protection du porteur nominal jusqu'à la dernière lecture. | P · Témoin à `-O0`, 31 tests à `-O2`. |
| N4–N6 | Réemprunt nominal retourné depuis une capture exclusive, puis lecture après destruction de la closure ou retour d'une fonction relais. | P · Témoin à `-O0`, 41 et 13 tests à `-O2`. |
| HM1–HM6, N4–N6 | Référence nominale partagée par entrée, lecture, retrait, indépendance des clés et refus d'une cible locale échappée. | P · Témoin à `-O0`, 39 tests à `-O2`. |
| HM1–HM6, N4–N6 | HashMap de références partagées vers des structures en ligne. Dépendance du champ projeté, champ frère modifiable, conservation après retrait. | P · 2 tests à `-O0`, 45 à `-O2`. |
| HM3–HM4, N2, N4–N6 | Référence nominale mutable transférée à une entrée puis restituée au retrait. Contrôle de l'ancienne liaison, de la cible et du champ frère. | P · Témoin à `-O0`, 38 tests à `-O2`. |
| EBNF, RT3, RT8 | Annotation branch nue, appel de méthode et await. Refus des formes mal écrites au parseur seul. | P · 2 tests syntaxiques, 10 régressions core. Un témoin sémantique natif préexistant échoue. |
| EBNF, RT3 | Annotations de type libres et structurelles empilées, avec ou sans `with`, sur la signature de spawn. | P · Syntaxe validée. 5 tests d'annotations et 10 régressions du core passent. |
| EBNF, chemins de types | Noms qualifiés dans une signature de closure, de HashMap et d'AsyncHandle, et refus des chemins incomplets. | P · 7 tests ciblés. Résolution des noms hors de cette passe. |
| EBNF, G6, AS7 | Séparateur des directives du core, tailles K/M/G et nom de pool qualifié. | P · 16 tests ciblés. |
| EBNF, listes de bras | `match` enum et Option avec séparateurs obligatoires, virgule finale facultative et refus de la liste vide. | P · 42 tests ciblés. |
| EBNF, motifs de match | Arbre syntaxique des motifs imbriqués, de l'unité, du joker et des champs. Refus des motifs mal formés. | P · 17 tests ciblés. |
| EBNF, types imbriqués et closures | Arguments génériques empruntés et séparateurs des listes de closures. | P · 34 tests ciblés. |
| EBNF, types de tranches | Tranches partagées et mutables avec élément numérique ou nominal, et refus d'une tranche sans emprunt. | P · 35 tests ciblés. |
| EBNF, types et littéraux | Syntaxe des signatures AsyncHandle et des entiers annotés u8 avant contrôles de typage. | P · 18 tests ciblés. |
| EBNF, déclarations et lock | Impl qualifié, formes lock, enum non vide et refus de syntaxes mal formées. | P · 25 tests ciblés et deux tests syntaxiques rejoués. |
| EBNF, chemins de valeurs | Appel qualifié, valeur qualifiée et appel qualifié suivi de .await. Refus des chemins mal formés. | P · 21 tests ciblés et témoin syntaxique rejoué. |
| EBNF, littéraux numériques | Décimaux, plage, comparaison et conservation d'un entier hors bornes au parseur seul. | P · 22 tests ciblés. |
| EBNF, en-têtes move | Entrées nommées en tête de bloc, bloc de capture avec valeur et refus de l'entrée après une instruction. | P · 11 tests ciblés. |
| EBNF, expression finale de bloc | Expressions finales en blocs imbriqués et fonctions, avant contrôle du retour. | P · 23 tests ciblés. |
| EBNF, instructions d'expression | Expressions numériques, parenthésées et nominales avec point-virgule dans un bloc. | P · 35 tests ciblés. |
| EBNF, places | Champs, indices et déréférencements combinés dans une affectation, avec refus des places mal formées. | P · 35 tests ciblés. |
| EBNF, suffixes | Champs, indices et appels de méthode enchaînés sur une expression. | P · 35 tests ciblés. |
| EBNF, initialisation de pool | Suffixe .new sur appel ou champ, valeurs nommées ou positionnelles et refus des formes mixtes. | P · 34 tests ciblés. |
| EBNF, programme | Déclarations et directive de capacité au niveau racine. Refus des instructions racine et des déclarations imbriquées. | P · 32 tests ciblés. |
| EBNF, G6, blocs | Directive de région sur un corps, une branche if ou un bras de match. Refus hors d'un bloc autorisé. | P · 34 tests ciblés. |
| EBNF, conditionnelle | Branche else facultative au parseur seul, y compris après else if. | P · 25 tests ciblés. |
| EBNF, unaire | Déréférencement d'une expression parenthésée ou postfixée, priorité et refus d'opérandes mal formés. | P · 40 tests ciblés. |
| EBNF, extern C | Signature externe et appel ordinaire avant la vérification du contexte unsafe. | P · 17 tests ciblés. |
| EBNF, profil core | Syntaxe du core avec str et sans type numérique explicite. Refus des anciennes flèches de transfert. | P · 48 tests ciblés et témoin rejoué. |
| EBNF, expressions primaires | Unité et appel immédiat de closure parenthésée, avec refus des formes mal écrites. | P · 50 tests ciblés. |
| EBNF, chemins builtin | Conversions et variantes d'erreur qualifiées avant contrôles de membre et d'arité. | P · 26 tests ciblés. |
| EBNF, receveur | Formes empruntées et par valeur, refus d'un receveur absent ou mal placé. | P · 25 tests ciblés. |
| EBNF, construction enum | Variante avec ou sans champs et désambiguïsation du bloc de match. | P · 34 tests ciblés et témoin syntaxique rejoué. |
| EBNF, tailles | Taille entière non signée dans un type tableau, une répétition et un pool, avant contrôles de représentation. | P · 35 tests ciblés. |
| EBNF, AS7 | Entiers non signés des directives de capacité avant contrôle de représentation. | P · 18 tests ciblés. |
| EBNF, G6 | Taille de région positive au-delà de la représentation et refus de zéro au parseur. | P · 19 tests ciblés. |
| EBNF, identifiants | Refus des noms réservés en position de déclaration et acceptation de `self` comme receveur et de `_` dans un motif. | P · 36 tests ciblés. |
| EBNF, initialisation et unité | Expression qualifiée dans `.new(...)`, refus des champs qualifiés ou réservés et de la syntaxe de paire de tranches en position de type. | P · 36 tests ciblés. |
| EBNF, pool et motifs | `Pool<&mut i64>::new(4)` reconnu au parseur, type incomplet refusé ; identifiants réservés refusés dans les motifs de variantes, `_` reconnu comme motif de champ. | P · 39 tests ciblés. |
| EBNF, contrats de type et de branche | Alternatives empruntées reconnues, liste de méthodes vide et identifiants réservés refusés. Distinction des noms et type du receveur vérifiés sur le parcours de compilation. | P · 39 tests ciblés, dont un témoin de la séparation des parcours. |
| EBNF, lancement | Une expression exigée pour `spawn` et `spawn_blocking`, y compris en contexte synchrone au stade syntaxique. | P · 41 tests ciblés. La suite élargie signale deux assertions liées à l’attente d’un thread autonome, détaillées dans le rapport. |
| EBNF, RT8 | Identifiants des captures nommées, analyse de `yield` et `.await` indépendante du contexte. | P · 42 tests ciblés, dont refus des suspensions dans un bloc de thread lors de la compilation. |
| EBNF, suffixes, TX4 | Arguments d’appels ordinaires conservés avant le contrôle d’arité, plage de `try_slice` décrite dans l’EBNF. | P · 41 tests ciblés. |
| EBNF, constructeurs intégrés | Mutex avec une expression sans virgule, HashMap avec clé admissible et refus de `new(source) Int(...)` au parseur seul. | P · 42 tests ciblés. |
| EBNF, chemins et types | Segments ordinaires de chemins qualifiés, types intégrés reconnus dans leurs positions et refus de `A` seul, `Execution<T>` et `runtime::Future`. | P · 44 tests ciblés. |
| EBNF, opérateurs unaires | `&mut text[1..3]` conservé au parseur seul, indice vide refusé et diagnostic de mutabilité conservé en compilation. | P · 44 tests ciblés. |
| EBNF, affectation | Cible simple, projection depuis `self`, opérateurs composés et refus d’identifiants réservés dans les cibles. | P · 45 tests ciblés. |
| EBNF, résultat de bloc | Bloc simple, capture `move`, `unsafe`, `if`, `match` et `loop` reconnus comme résultat en fin de bloc. | P · 46 tests ciblés. |
| EBNF, construction enum et bloc | Accolades vides reconnues comme bloc de `if` ou `while` lorsqu’un bloc est requis, et conservées comme initialisation lorsqu’un autre bloc suit. | P · 47 tests ciblés. |
| EBNF, chemins de valeurs | `self.champ` et chemins intégrés reconnus, noms réservés en position de valeur ou de champ et appels runtime hors core refusés. | P · 48 tests ciblés. |
| EBNF, chemins de motifs | Motifs qualifiés ordinaires et intégrés reconnus, segments réservés et chemins runtime incomplets refusés. | P · 49 tests ciblés. |
| EBNF, conversions | Type emprunté complet après `as`, priorité des conversions successives et refus des types mal formés. | P · 61 tests ciblés. |
| EBNF, point d’entrée | Déclarations externe et async de `main` reconnues syntaxiquement, forme externe avec corps refusée, contrôle de `main` externe conservé en compilation. | P · 78 tests, dont la suite d’intégration du core. |
| EBNF, G6 | Une directive de région par bloc, annotations de blocs imbriqués et terminaux conservées. | P · 57 tests, dont la suite des annotations de croissance. |
| EBNF, liaisons et captures | Liaison de paire et `type feature` historiques refusés au parseur seul, import nommé suivi d’une closure `move` reconnu. | P · 58 tests ciblés. Une assertion historique échoue dans la suite élargie. |
| EBNF, terminaux | `::` contigu dans un type imbriqué, fermeture `>>` suivie de `=`, séparateur scindé par espace, saut de ligne ou commentaire refusé. | P · 73 tests ciblés. |
| EBNF, CLI | `check --syntax-only` accepte `yield;` en corps synchrone, refuse `yield` sans point-virgule et ne se combine pas avec `emit-c`. | P · 4 appels CLI du témoin, 2 appels sur `let_mutability.crust` et 50 tests ciblés. |
| EBNF, primitifs et clés | `i32` conservé dans les signatures ordinaires et externes, annotations et types imbriqués. Clé `Int` historique refusée au parseur seul. | P · 74 tests ciblés. |
| EBNF, signatures | `A<i32>`, `bool`, `&[u8]` et `runtime::AsyncHandle<i64>` conservés avant l’abaissement et l’enregistrement des types de compilation. | P · 76 tests ciblés. |
| EBNF, instructions | Appels `bool()` et `runtime()` et valeurs terminales `bool` et `_` refusés même lorsque le parseur revient à la lecture d’une instruction. | P · 63 tests ciblés. |
| EBNF, constructions et suffixes | Appel et `.await` reconnus lorsque la liaison porte le même nom qu’un enum déclaré. | P · 62 tests ciblés. |
| EBNF, bloc vide composé | Opérateur et suffixe rattachés au `if` lorsque l’interprétation des accolades comme initialisation laisse le `if` sans bloc. | P · 64 tests ciblés. |
| EBNF, receveur et SL1 | `self` documenté comme valeur et base d’affectation, appel nu `self()` refusé. Productions de SelectGroup identifiées comme reportées. | P · 54 tests ciblés sur le parseur et les déplacements. |
| EBNF, démonstration | Exemple public avec `Pool<Message>`, `memory.new`, retour `A<Message>` et `match` sur emprunt. | P · 3 appels CLI et 55 tests ciblés, dont la trace de destruction et de récupération existante. |
| EBNF, retours conditionnels | Exemple migré vers `A<i32>` avec retours par valeur et `drop`. | P · syntaxe, vérification et exécution par CLI. Oracle sur quatre adresses, deux résultats et quatre événements de nettoyage. |
| EBNF, retours avec emprunt | Deux exemples migrés vers `A<View>` et `data.vref()`. | P · deux analyses syntaxiques réussies, exécution valide `View.Item(42)` et refus du retour d’une cible locale. |
| EBNF, suffixe `try_slice` | Plage, appel ordinaire sans argument et appel ordinaire à deux arguments distingués au parseur seul. | P · 54 tests ciblés. |
| EBNF, régression du parseur | Rejeu transversal des témoins appelant directement `parse_syntax` dans les cinq suites concernées. | P · 57 réussites. |
| EBNF, fermetures génériques | `A<i32>==other`, `A<i32>>=other`, `A<i32>>>2` et trois niveaux génériques reconnus dans leur contexte. `>>>` et `>>=` isolés sont refusés. | P · 78 tests ciblés. |
| EBNF, appel immédiat de closure | `(move \|\| {42})()` accepté, regroupement sans appel accepté, appel d’un regroupement imbriqué ou d’un nom parenthésé refusé. | P · 54 tests ciblés. |
| EBNF, nom `pool` | Constructeur à type imbriqué ou de closure, appel ordinaire `pool()`, méthode, comparaison avec décalage et comparaison parenthésée distingués. | P · 71 tests ciblés. |
| EBNF, TX1 | Échappements JSON des littéraux texte, normalisés dans TX1. | P · 11 formes acceptées avec octets vérifiés et 7 refus confirmés. |
| EBNF, N1 et N3 | Signatures de closure `fn`, `&fn`, `&mut fn` et liaison reçue `mut f`. | P · 35 tests ciblés. Les assertions syntaxiques distinguent le mode du paramètre et l’emprunt du résultat. |
| EBNF, construction de structure | Nom partagé par une structure et une liaison en condition. Bloc vide, bloc d’instructions et initialisation avec champ distingués. | P · 65 tests ciblés. |
| EBNF, diagnostics d’expression | Un `match` vide sous 20 `if` conserve son diagnostic et chaque bloc n’est lu qu’une fois. `1 + ;` signale le point-virgule reçu à la place de l’opérande. | P · témoin instrumenté de 21 lectures et 67 tests ciblés. |
| N4, RT7–RT8 | Témoin modernisé : abandon du handle autonome accepté, capture empruntée refusée à la sortie ou à l’abandon explicite sans attente. | P · 70 tests ciblés, contrôle et génération C sur les quatre variantes. |
| EBNF, régression d’intégration | Rejeu conjoint du numérique, des contrats, des déplacements, des directives, des threads et de l’intégration. | P · 124 méthodes réussies et 5 exemples acceptés via `check --syntax-only`. |
| TF1, régression historique | `type feature` refuse `fn a(self);` et conserve les modes de receveur documentés. | P · 92 méthodes réussies, dont la suite complète des contrats de type. |
| EBNF, appel et types async | `copy([1, 2])` conservé comme appel. Aucun enregistrement de Vector ni de Result dans le témoin async du parseur seul. | P · 71 tests ciblés et un témoin instrumenté. |
| EBNF, CLI, TX1 | Source UTF-8 valide acceptée, octet invalide localisé et refusé sans exception Python affichée. | P · 4 appels CLI, dont deux sur l’exemple principal. |
| EBNF, programmes d’intégration | Programmes compilés par la suite `test_core_integration` relus au parseur seul. | P · 30 tests réussis, 42 programmes acceptés au parseur et 2 refus attendus du scheduler expérimental. |
| EBNF, revue des productions | Correspondances entre productions, méthodes du parseur et témoins dans le rapport de cycle. | P · 61 tests syntaxiques réussis. Échappements et SelectGroup signalés à part. |
| EBNF, champs empruntés | Exemples en `i32`, `pool.new`, `.vref()` et `drop`. | P · deux analyses syntaxiques réussies, sortie `42`, refus du `drop` avant le dernier usage. Limites du vérificateur dans le rapport. |
| EBNF, exhaustivité du match | Programme du core incomplet et variante avec bras manquant ajouté. | P · 4 appels CLI : les deux passent au parseur, seul le programme exhaustif passe la vérification. |
| EBNF, N6 | Remplacement entre pools avec résultat nommé, puis par `second.new(...)`. | P · syntaxe, compilation, sortie `10`, `20`, `30` et trace vérifiées. Affectation directe d’un résultat d’appel acceptée par le parseur, refusée ensuite. |
| EBNF, retours d’emprunt | Retours partagés et mutables avec emprunt explicite du contenu de `A<i32>`. | P · 2 analyses CLI, 2 exécutions avec identité d’adresse vérifiée et 2 extraits README analysés et vérifiés. |
| EBNF, contrôle de flux | `conditionals`, `if_expression`, `loop`, `continue`, `while` et `scope_exit`. | P · 6 analyses syntaxiques et 6 exécutions réussies. |
| EBNF, drop et déplacement | Quatre exemples du core avec emprunt du contenu par `.vref()`, destruction et réutilisation de slot. | P · 4 analyses syntaxiques, 2 exécutions réussies et 2 refus sémantiques attendus. |
| EBNF, P8 et provenance | Construction d’un `Message` dans un `Pool<i32>`, retour d’une allocation issue d’un pool local. | P · les deux passent au parseur, puis sont refusés avec les diagnostics attendus. |
| EBNF, ordre des arguments | Lecture avant transfert et allocation passée directement en argument. | P · exécution avec valeurs et destructions vérifiées, ordre inversé accepté au parseur et refusé au vérificateur. |
| EBNF, champ emprunté mutable | Retour `A<Writer>`, capture de `.mut_vref()` et accès à la cible. | P · analyse syntaxique et exécution réussies, écriture avant le dernier usage refusée par le vérificateur. |
| EBNF, provenance conditionnelle | Deux pools, retour par valeur depuis l’un des deux et réemploi du slot de l’autre. | P · 2 analyses syntaxiques et 2 exécutions avec oracle d’adresses et de valeurs. |
| EBNF, N3–N4 | Déplacement dans un bloc, nouveau receveur, consommation en argument et retour depuis un pool local. | P · 4 analyses syntaxiques réussies et 4 refus de vérification attendus. |
| EBNF, types nommés et appels qualifiés | Le parseur partage les arguments de type et conserve les comparaisons avec `<`. | P · Test Rust de structure AST et refus syntaxiques, 3 110 occurrences reconnues avant et après, huit suites de validation Rust réussies. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#régression-du-parseur-sur-le-corpus). |
| README examples | Four Din programs per language version compile and run. The Rust vector example runs with an assertion. | P · Corpus rebuilt, 34 documentation snippets accepted. [Report](cycles/CORE_COMPOSITION_CYCLE.md#documentation-layout-and-readme-examples). |
| EBNF, inventaire des exemples | Les 46 fichiers `.crust` d’`examples` relus au parseur seul. | P · 31 acceptés, 14 refus historiques et un refus de l’ancien `runtime::select`. |

[Rapport et limites](cycles/CORE_COMPOSITION_CYCLE.md)

## Écarts reproduits en syntaxe du noyau

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N4–N6, N8, E6 | Retour de `&mut i32` projeté depuis un tableau par une tâche puis récupéré par `join()`, ainsi que projections de rangées de références. | Écart reproduit · Exception Python aux deux entrées du compilateur pour le témoin minimal. |
| N1, AS4 | `bool` renvoyé par `join()`, par `match h.await`, puis par un `if` combinant un résultat attendu et un booléen. | Écart reproduit · Le premier témoin passe en C. Les deux autres révèlent un champ C absent et un refus de typage. |
| N1, V1 | Liaison `i32` initialisée avec un `A<i32>`. | Écart reproduit · Acceptée aux deux entrées et encore déréférençable dans le programme généré. |
| N1, E4 | Écriture async dans une case `i32` avec un littéral, puis avec une variable annotée. | Écart reproduit · Littéral rejeté. Le témoin annoté produit `12` en C sous UBSan. |

[Tri des échecs et témoins](CORE_FAILURE_TRIAGE.md)

## Retour d'une allocation d'enum dans le core

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N1, N2, N6–N7, B4a, B4c, L1–L3, P9 | Construction de deux variantes avec `Pool<E>.new`, retour `A<E>`, passage des deux arguments par valeur, trace de destruction, refus du mauvais type de pool. | P · Cas migré et module `test_arguments` exécutés sous UBSan. |

[Rapport et journaux](cycles/ENUM_CORE_VALIDATION_CYCLE.md)

## Contrats de verrou et HashMap depuis le code source

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| MT10, N2, N4, N6–N7 | Réacquisition selon l'ordre de destruction d'un argument, relais synchrone, capture par transfert, tâche abandonnée avant lancement, succès et `LaunchFailed` de `join()`, conflit pendant l'attente. | P · Tests de compilation et d'exécution sous UBSan. Le transport testé restitue un résultat propriétaire direct. L'implémentation fournit le verrou réel. |
| HM1–HM2, HM4–HM5 | Comparaison au dictionnaire de référence, remplacement, extraction, réindexage, stabilité des adresses, réemploi des emplacements et capacité épuisée sans modification. | P · Tests depuis Crust et sondes natives sous UBSan. Le test de l'échec injecte une capacité réduite dans le C généré. |
| HM3, HM6 | Prêts partagés ou exclusifs sur la table, libération au dernier usage, prêt de clé limité à la recherche, valeurs nominales, pools distincts et remplacement d'une référence stockée. | P · Les clés connues isolent les dépendances par entrée. Une clé indéterminée conserve une union prudente. Le passage de tables à charge dépendante par contrat reste à intégrer. |
| HM6, N4–N6, N8 — backend Rust | Les clés connues isolent leurs dépendances. Un contrat de remplacement synchrone transmet la nouvelle provenance à l'appelant. | P · 21 programmes et 13 refus dans la suite collections. Clés dynamiques et effets conditionnels traités par union. Effets différés locaux exercés sur thread/join et spawn_blocking/await, y compris LaunchFailed. Contrats d’attente synchrones et async et fabrique native exercés. Récursion synchrone de remplacement exercée. 42 programmes et 21 refus dans la suite tâches. Voir le lot dédié aux handles ci-dessous. |
| N4–N6, AS3–AS4, RT5–RT8 — handles imbriqués et récursifs | Attentes récursives et relais sync et async, retour depuis un worker, récursion mutuelle et type enum récursif via un handle. Échec de lancement injecté et accès prématuré refusé. | P · 53 programmes C sous UBSan à `-O0` et `-O2`, 24 refus. Limites dans le [rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-imbriqués-et-récursifs-dans-le-backend-rust). |
| N4–N6, AS3–AS4, RT5–RT8 — handles en collection et contrats récursifs | Extraction depuis pools et vecteurs, décalage des chemins après `remove`, suspension async et relais récursif qui attend ou restitue. Refus d’abandonner le vecteur dépendant. | P · Deux tests Rust, huit suites C. 60 programmes de la suite tâches sous UBSan à `-O0` et `-O2` et 25 refus. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#handles-en-collection-et-contrats-des-cycles-récursifs). |
| N4–N6, RT5 — vidage des vecteurs de handles | Indice dynamique sur une case unique, vidage de longueur inconnue par `pop()` et `join()`, refus de l’accès après une sortie anticipée. | P · Deux témoins ciblés sous UBSan à `-O0` et `-O2`, un refus statique et un arrêt d’exécution sur indice hors borne. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#déduction-de-la-case-unique-et-vidage-dun-vecteur-de-handles). |

[Rapport et journaux](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) ·
[Cycle initial des sondes natives et du marqueur](cycles/CORE_LOCK_HASHMAP_CYCLE.md)

## Annotations d’emprunt et littéraux à travers mut_vref

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N1, N3–N5, H1, brouillon 07 | `let vue: &i32 = nombre.vref()`, écriture de `20` via `mut_vref()`, annotation mutable ou inférence. Refus pour le mauvais mode, le mauvais type, un `drop` prématuré ou un littéral hors bornes. | P · Exécutions natives sous UBSan et refus aux deux entrées source. Une annotation d’emprunt direct async est aussi exercée après `yield`. |

[Rapport et journaux](SAFETY.md#annotations-demprunt-et-littéraux-à-travers-mut_vref)

## Effets de dépendance après execution.await

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N4–N5, AS8, MT9 | Mutex local et cibles réservés à la capture, puis pendant l'attente. Refus de détruire l'une des cibles ou le mutex, de le faire lire par un autre appel et de retenir une cible trop courte. | P · Champ partagé `&i32` écrit par une tâche Void, accès au mutex réservé jusqu'à la fin de l'attente. |
| N4–N5, RT5–RT6 | Match direct et résultat nommé immuable. Sorties `2` en succès et `1` sur la première soumission enfant échouée. Destruction unique et refus de détruire la cible encore stockée ou de réutiliser un statut périmé. | P · Exécutions natives sous UBSan et refus aux deux entrées source. |

[Rapport et journaux](SAFETY.md#effets-de-dépendance-après-executionawait)

## Effets de dépendance des tâches sous garde

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N4–N5, AS8, MT9 | Une tâche remplace un `&i32` sous garde. Le contrat nomme le champ et la cible, et l'appelant contrôle sa durée de vie. Cible trop courte, destruction avant join et lecture concurrente refusées. | P · Mutex possédé localement par l'appelant synchrone, réservé jusqu'au join. |
| N4–N5, RT5–RT6 | Succès et échec de soumission injecté. Destruction de l'ancienne ou de la nouvelle cible selon le bras, lecture du champ restant, refus des destructions inverses. Une écriture conditionnelle ou un statut ignoré conserve les provenances possibles. | P · Tâche Void, champ partagé `&i32`, match direct ou sur un résultat nommé immuable. |

[Rapport et journaux](SAFETY.md#effets-de-dépendance-des-tâches-sous-garde)

## Clôture du lot d'intégration du noyau

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N3–N5, N7, MT9 | Remplacer `&i32` et `A<Item>` sous garde sync/async en affectation ou via auxiliaire sync. Réutiliser l'ancien slot et observer une seule destruction du nouveau champ. Refuser le drop avant la prochaine lecture ainsi qu'une cible ou un pool trop court. | P · Mutex local sans autre emprunt. Changement de provenance d'un mutex partagé ou par une tâche enfant refusé. |
| RT3, RT4–RT8 | Vérifier le refus par défaut et le succès sur option pour `check`, `effects`, `emit-c`, `build` et `run`. Exercer le lancement et le réveil intégrés dans les suites de régression. | P · Scheduler personnalisé hors grammaire cible et exposé uniquement en mode expérimental. |
| Brouillons 02 et 07, N2–N4, AS2, AS8, RT7 | Exemples sans flèches de transfert. Défauts `i64` et `f64` sans annotation. Retour et consommation de `A<Holder>` via une tâche avec réemploi du slot. Rejeu séparé des assertions historiques. | P · Compatibilité historique conservée pour les scénarios qui exercent cette syntaxe ou `reset()`. |

[Rapport et journaux](SAFETY.md#clôture-du-lot-dintégration-du-noyau)

## Retours async, charges gardées et placement local

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| N3–N5, AS4, AS11–AS12, RT5, MT6 | `&mut u64` par `.await` direct, `.await` sur handle et `join()`, y compris retour par auxiliaire. Projection d'un champ `&f64`. Refus d'accès avant la fin de l'emprunt et refus d'une cible locale. | P · Pointeurs C typés et provenance conservée dans les cas exécutés. |
| N4–N5, MT1, MT7–MT9 | Charge à emprunt et champ propriétaire par mutex sync/async. Deux tâches mutent la cible d'un champ emprunté mutable sous le même verrou. Refus de détruire la cible ou la garde trop tôt, puis destruction unique et réemploi de l'allocation possédée. | P · Structures représentées. Le changement de provenance d'un champ de dépendance sous garde reste ouvert. |
| L7, brouillon 03 | Retour d'une structure locale avec un `if` de lecture avant ou après sa création. Le C construit la valeur dans la réservation parent et récupère le temporaire avant le résultat. | P · Deux refus valides reproduits et corrigés. |

[Rapport et journaux](SAFETY.md#cycle-des-retours-async-et-charges-gardées)

## Runtime intégré du noyau

| Règles | Invariant et cas exécutés | Statut et limites |
| --- | --- | --- |
| RT2, AS4, AS8–AS9 | Reprise exclusive et état stable. Réveils concurrents pendant un poll, absence de second poll actif, reprise sur un autre thread avec conservation d'un emprunt local. | P · Modèle indépendant de disponibilité et exécutions C synchronisées. |
| RT2, AS4, MT9, SL1 | Réveil utile après `Pending`. Un mutex attendu derrière deux `.await` directs reçoit le ticket de la tâche racine. Réveil pendant un poll, sélection imbriquée, attente d'un handle, tickets tardifs et réemploi d'une entrée. | P · Chaînes exercées et modèles FIFO et Select, sans preuve générale d'équité. |
| AS10, AS14, RT5–RT8, MT7, SL1–SL2 | À la complétion, les enfants directs sont libérés. L'état racine et la capture propriétaire restent vivants jusqu'au `join`. Extraction, destruction unique, réemploi du slot et deuxième attente refusée. Rejeu des échecs de lancement et du nettoyage des perdantes. | P · Assertions sur le runtime C et refus source pour les obligations d'attente. |

[Rapport et journaux](SAFETY.md#cycle-du-runtime-intégré--9-novembre-2026)

## Dernier lot du noyau

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| RT3, RT8 | Deux installations dans des branches exclusives, installation après un lancement natif via une fonction, après une autre installation ou sur une reprise de boucle. | P · Vérificateur et compilation vérifient les chemins, et le runtime garde son contrôle. L'effet des fonctions auxiliaires est résumé de façon conservative. |
| N3–N5, AS2, AS8, brouillon 07 | Emprunt mutable d'un champ `u64` après un `u8`, retour emprunté d'un auxiliaire sync, mutation par appel sync après `yield`, prêt d'un scalaire local à une tâche. Rejet d'un accès à la cible avant le join. | P · Les champs du profil numérique ont un pas aligné. Les retours d'emprunts larges depuis une fonction async restent ouverts. |
| MT9 | Une structure à champs scalaires est transférée à un `AsyncMutex`, empruntée par sa garde et mutée par un enfant suspendable. La charge est détruite une fois. Réemprunt de `i64` et refus de détruire la garde pendant un emprunt. | P · Charges scalaires et structures à champs scalaires. Les charges qui contiennent des références ou des allocations et les compositions plus générales restent ouvertes. |
| L7, brouillons 03 et 05 | Réservation parent pour un `if` dont seule la branche qui continue fournit une valeur. Rejeu de la branche qui fait `return` et vérification du nettoyage dans les deux cas. | P · Le plan reste limité aux constructeurs et chemins identifiés par le compilateur. |

[Rapport du lot](SAFETY.md#dernier-lot-du-noyau--9-novembre-2026)

## Intégration du noyau

| Règles | Cas exécutés | Statut et limites |
| --- | --- | --- |
| Brouillon 07, N2/N4, AS2/AS8 | Défaut `i64`, champs mixtes, alignement de `i32` après `u8`, réservation d'une place composée, conversion exacte traversant `yield` et `.await`, pool `u64` local et allocation capturée. | P · Profil historique toujours disponible. Emprunts directs des champs larges et signatures async générales ouverts. |
| Brouillon 02, RT8 | `move a;` et `move { ... }` dans un thread natif. L'original scalaire reste accessible. L'original propriétaire ne l'est plus. | P · Comparaison de sortie C et refus aux deux entrées. |
| RT2–RT5 | Installation dans `main`, signatures des callbacks, consommation de la Future, démarrage d'un poller, réveil à `yield` et `LaunchFailed` observé au join. | P · File C fournie. Poll public et file écrite en Crust ouverts. |
| MT9 | Verrou sync repris après sortie de portée, refus du drop avec une garde, refus d'une garde sync sur suspension, deux incréments concurrents, réemprunt async de `i32`. | P · Constructeurs scalaires et emprunts dans le périmètre testé. |
| FFI1–FFI6 | Types scalaires, plusieurs sources C, appel après suspension, symbole absent, rejet de NaN et des infinis, conservation de `-0`, appel hors unsafe et usage après drop refusés. | P · Backend C et ABI natifs de cette exécution. |

[Rapport du cycle](SAFETY.md#cycle-dintégration-du-noyau--9-novembre-2026)

## Grammaire du noyau cible

| Règles | Cas vérifiés | Limites |
| --- | --- | --- |
| S1, S4–S6, brouillons 02 et 07 | Blocs, `move` en tête, capture par valeur, primitifs retenus, expressions, branches et boucles. Les anciennes flèches de transfert sont rejetées par la grammaire cible. | Vérification de la syntaxe sur une sélection de sources. Typage et sécurité mémoire suivis séparément. |
| AS1, AS3–AS4, AS7, RT4–RT8, SL1 | `async fn`, `yield;`, suffixe `.await`, deux formes de lancement, thread natif, `join()`, `runtime::select` et directive de capacité. Les deux formes modernes de captures de thread sont reconnues. | Les captures modernes de thread sont vérifiées syntaxiquement. Le contexte sync/async et les obligations d'attente relèvent du vérificateur. |
| Brouillon 07, littéraux flottants | Les formes `1.5`, `1.` et `.5` et l'annotation `f32` sont reconnues. `1..3` reste un intervalle. La notation exponentielle et les suffixes de type sont rejetés. | Typage et exécutions dans le cycle numérique ci-dessous. |
| F4, brouillon 07, logique | Quatre cas de syntaxe distinguent `!`, `!=` et les conditions de `if` ou `while`. [Journal](../validation/core-grammar-boolean.log) | La grammaire reconnaît `if 7 {}`. L'exigence de `bool` relève du typage cible. |
| Brouillon 07, opérations bit à bit | Cinq cas de syntaxe exercent `&`, `\|`, `^`, `~` et la distinction entre emprunt et ET binaire. [Journal](../validation/core-grammar-bitwise.log) | Le typage et la largeur sont exercés dans le cycle numérique. |
| Brouillon 07, décalages | Cinq cas de syntaxe distinguent `<<`, `>>`, les comparaisons et les fermetures de types imbriqués. [Journal](../validation/core-grammar-shifts.log) | Les contrôles statiques et dynamiques sont exercés dans le cycle numérique. |
| Brouillon 07, affectations composées | Six cas reconnaissent les cinq opérateurs sur des emplacements et rejettent un opérateur séparé ou une cible littérale. [Journal](../validation/core-grammar-compound-assignment.log) | L'évaluation unique et l'ordre sont exercés pour les variables et tableaux fixes dans le cycle numérique. |
| RT3, MT9, FFI1–FFI5, brouillon 07 | 53 cas de syntaxe rejoués, 15 cas nouveaux pour `set_scheduler`, `Future`, `TaskId`, les mutex, l'erreur numérique et les appels C. Aucun écart. [Journal](../validation/core-grammar-interfaces.log) | La portée de `unsafe`, le site d'installation et le contrat du scheduler relèvent du vérificateur. `--c-source` relève de la CLI. |

[Grammaire](../CORE_GRAMMAR.ebnf) · [Rapport et journaux](SAFETY.md#cycle-de-la-grammaire-du-noyau)

## Noyau numérique

| Règles | Cas vérifiés | Statut et limites |
| --- | --- | --- |
| 07 · Primitifs, littéraux et contexte | Bornes des littéraux et du signe, mêmes familles et largeurs, paramètres, retours, tableau homogène et résultats de `if`, `match` et `break`. | P · Profil numérique. Champs nominaux et compatibilité détaillés dans le cycle d'intégration. |
| 07 · F4/F5, arithmétique et logique | Débordement, diviseur nul, quotient et reste signés à la borne, arrondi pair, résultat flottant nul exact, sous-flux, court-circuit, opérations binaires et décalage signé. | P · Diagnostics des constantes et contrôles du C natif sous UBSan dans les cas exercés. |
| 07 · Conversions, indices et longueurs | `as` vérifié sur le type source, `try_from` exact sur la valeur, indices contrôlés avant conversion, `len()` de tableau et de tranche typée en `u64`. | P · Conversions synchrones, tableaux fixes et conversions async dans le périmètre du cycle d'intégration. |
| 07 · Affectations composées, N4–N5, AS8 | Évaluation unique du lieu, bornes avant la droite, lecture et mutation disjointe, mutation recouvrante refusée, reprise après `.await`. | P · Variables, cases de tableaux fixes, champs numériques et déréférencements représentés. |
| N2/N7, AS2/AS8, RT7 | Adresse et type conservés à travers un transfert de `A<u64>`, mutations et réemploi de slot. Valeurs `f32` et `bool` sur `yield`, `.await` et join. | P · Pools numériques synchrones. Les contrats et captures d'allocations numériques async restent à généraliser. |

[Sources et exécutions](SAFETY.md#cycle-du-noyau-numérique)

## Déplacements par valeur et captures

| Règles | Invariant vérifié | Exécutions et limites |
| --- | --- | --- |
| Brouillon 02, N2–N3, H1 | Liaison, argument, retour et drop déplacent l'accès en conservant l'identité et un seul nettoyage. | Adresse identique avant et après appel, slot réemployé, anciens noms refusés aux deux entrées. |
| Brouillon 02, N4–N6, F3/F4 | Le bloc capture à l'entrée. Un scalaire copié reste indépendant. Un emprunt ou un pool trop court empêche le déplacement. | Import nommé et capture lexicale, portée du masquage, receveur visible, retour de branche et de boucle, préparation des arguments de gauche à droite. |
| AS2/AS8/AS11, RT5/RT7 | Les transferts d'une tâche et de son résultat préservent le nettoyage et l'attente. | Capture propriétaire et copie scalaire à travers `yield`, spawn et join. Migration générale des autres captures ouverte. |

Statut P. Le [rapport](SAFETY.md#cycle-des-déplacements-par-valeur) distingue
les passes réussies et les échecs historiques retrouvés.

## Noyau mémoire N1–N8

Les repères renvoient à la [grille du noyau](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture).
La passe [test_core_memory](../tests/test_core_memory.py) couvre dix programmes
exécutés en C et dix-neuf variantes invalides contrôlées par `verify_program`
et `compile_source` avec leurs paramètres par défaut. Le détail des passes et
de leurs limites figure dans le [rapport du cycle](SAFETY.md).

| Repère et règles liées | Cas de la passe ciblée | Complément de couverture |
| --- | --- | --- |
| N1 · V1–V5, ST1–ST5, H1 | Construction complète acceptée. Champ manquant, mauvais type de champ et confusion entre valeur locale et pool refusés. | Constructions imbriquées, enums, signatures et exigences de stockage. |
| N2 · T1–T6, H1, L2/L6 | Un aller-retour en fonction garde l'adresse et une seule destruction. L'ancien nom est refusé. | Transferts d'états, captures et nettoyage des perdantes de Select. |
| N3 · U1, T1, ST17–ST18 | Copie explicite indépendante. Affectation implicite et résultats inutilisés refusés. Un receveur masqué dans un bloc peut être lu après ce bloc, si le chemin y parvient. | Les méthodes et leur syntaxe propre restent suivies par les entrées ME1–ME4. |
| N4 · D1–D4, A2/A3 | Retour d'une structure empruntant le parent accepté. Cible locale à l'enfant et pool trop court refusés. | Exigences de stockage à travers plusieurs appels et captures. |
| N5 · B1–B5, ST6 | Champs disjoints et mutation après dernier usage acceptés. Même champ, accès prématuré et drop avant dernier usage refusés. | Emprunts renvoyés par appel, await et join. |
| N6 · S4–S5, T9–T10, F3–F4 | Branche divergente et chemins break/continue. Le même cas sans sortie anticipée est refusé. | Provenances alternatives et arguments évalués en présence d'emprunts. Remplacement d'un receveur externe également rejoué dans le profil historique. |
| N7 · L1–L7, A4 | Nouvelle allocation construite avant drop de l'ancienne, puis destruction à la fin du scope. Réemploi de slot avec le cas N2. Reset refusé dans le profil courant. | Inspection du C et traces de destruction. Modèles de stockage et de nettoyage dans leurs périmètres respectifs. |
| N8 · B4–B5, ST8/ST12, AS11–AS15, MT3/MT5/MT6 | Relais d'un emprunt mutable via deux contrats. Accès avant son dernier usage et retour d'une cible locale refusés. | Contrats vérifiés sans relire les corps dans les cas testés, y compris stockage, captures et résultats de join. |

Statut P pour les huit repères. Les cas exécutés se recoupent avec les entrées
par règle ci-dessous. Les résultats sous compatibilité reset restent distincts.
Après correction du suivi de masquage, les quatre passes finales totalisent
208 méthodes réussies. Le détail des profils et configurations est dans le
[manifeste](../validation/core-memory-final.json). ASan reste non concluant.

Extension synchrone validée dans son périmètre : [contrats de replace en ligne](cycles/INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md).
Huit méthodes ciblées O0/UBSan : 17 exécutions C et six variantes invalides aux
deux entrées. Premier passage O2/UBSan : 169 méthodes réussies. Après le complément
des paramètres Result<T,T>, **171 méthodes passent en 160,035 s**, avec les 46
empreintes inchangées. Le passage interrompu sans bilan n'est pas compté comme
une réussite. Journal final : validation/inline-vector-replace-contract-replay-regression.log.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, T6, ST17/ST18 | Porteur local distinct de la case ; champs séparés par bras | Retours frais/nommés, entrant paramètre, relais et branches ; C conservé | P — synchrones exercés, async ouvert |
| B1–B5, U1, L1/L6 | Champs empruntés/propriétaires conservés après transfert du Result | Paramètres Result, drop du vector, nettoyage unique, slots réemployés, mutations prématurées refusées | P — graphes exercés, pas de preuve générale |
| H1, F2–F4 | Stockage déclaré T/A<T> et flèches explicites respectés | Signatures de paramètres/retour, mauvais stockage et retour sans flèche refusés | P — régression O2/UBSan réussie dans ce périmètre |

Checkpoint en cours : [replace des structures en ligne](cycles/INLINE_VECTOR_REPLACE_CYCLE.md).
Sept méthodes ciblées O0/UBSan : 13 exécutions C et huit variantes invalides
aux deux entrées. Régression O2/UBSan : **142 méthodes, 111,163 s, code 0**,
43 empreintes inchangées. Le complément synchrone figure ci-dessus ; async reste ouvert.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST17/ST18 | Replace local rend l’ancien T ou restitue l’entrant ; A<T> reste distinct | Succès, indices invalides, annotations, Empty, C conservé | P — checkpoint local ; contrat raccordé dans le complément ci-dessus |
| B1–B5, T4/T5/T6 | Les graphes de champs sont transmis au résultat ou à la case | Lecture après drop du vector, emprunt entrant actif refusé, mutation prématurée refusée | P — champs représentés ; positions inconnues conservatrices |
| U1, L1/L6, VE2 | Nettoyage unique des champs propriétaires et réemploi des slots | Deux descendants, deux branches, drop direct et fonction consommante | P — pas de preuve générale ; reset retiré |
| F2–F4 | Ordre indice puis entrant et transfert explicite | Deux fonctions avec trace 1 puis 2, ancien nom/flèches refusés | P — refus initial du retour corrigé dans le complément ci-dessus |


Dernier lot terminé dans son périmètre : [pop des structures en ligne](cycles/INLINE_VECTOR_POP_CYCLE.md).
20 méthodes ciblées O0/UBSan : 27 exécutions C et 16 variantes invalides aux deux
entrées. Premier passage O2/UBSan : **361 méthodes, 349 succès, 12 échecs**.
Les deux causes sont corrigées ; rejeu des modules concernés, du ciblé et de
Select : **173 méthodes, 155,584 s, code 0**. Empreintes inchangées pendant
chacun des passages. Aucun passage unique de 361 méthodes vert revendiqué.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST17/ST18 | Pop d’une case locale rend Option<T>, distinct d’Option<A<T>> | Some/None, annotations, relais, refus T/A<T>, boucle et Empty | P — structures représentées ; autres opérations ouvertes |
| B1–B5, T4/T5/T6 | Les champs empruntés/propriétaires restent liés à leurs cibles et sources | Lecture après drop du vector, mutation prématurée refusée, champ mutable, descendant nettoyé une fois | P — union conservatrice après certains appels/branches |
| AS2/AS8/AS11–AS13, F2–F4 | Les contrats, captures, wrappers et handles publics transmettent le graphe du résultat | Await direct et lancé, join, relais Result, emprunt public, contrôles aux deux entrées | P — familles exercées ; sources des options vides distinguées par leur type vérifié |
| U1, L1/L6 | Un résultat propriétaire est consommé explicitement et nettoyé une seule fois | Drop direct, refus Some(_), usage après drop refusé, traces et réemploi | P — UBSan O0/O2, pas de preuve générale ni audit indépendant supposé |

Le cas local replace reproduit après ce lot est raccordé dans le checkpoint ci-dessus.
Le refus initial du retour par contrat est corrigé dans le complément ci-dessus.

Lot précédent terminé dans son périmètre : [champs propriétaires dans Vector<T>](cycles/INLINE_VECTOR_OWNED_CYCLE.md).
19 méthodes ciblées O0/UBSan : 16 exécutions C, 14 variantes invalides aux deux
entrées. Régression O2/UBSan : 236 méthodes, 232 succès et quatre fixtures
historiques défaillantes, reproduites avant ce lot. Signatures Node/A<Node>
corrigées ; leurs cinq méthodes rejouées passent. Complément régions :
**35 méthodes, 26,861 s, code 0**. Aucun passage global vert unique revendiqué.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, ST15/ST17 | La case possède ses champs A<T> ; remove restitue le nettoyage, copy est refusée | Traces de destruction unique, vector vide/non vide, deux pools, slots réutilisés | P — push/remove et layouts représentés ; autres opérations ouvertes |
| T4/T5/T6, B1–B5 | Pools descendants et cibles empruntées survivent au receveur | Scopes enfants, contrats, descendant empruntant, refus mutation et pool trop court | P — défaut async du contrat corrigé, journal négatif conservé |
| AS2/AS8/AS11–AS13, L1/L6 | Les états/captures transmettent les champs sans déplacer les objets pointés | Yield, join, capture inactive, C inspecté | P — cas ciblés, suivi conservateur des sources après extractions |
| G1–G12, GR1/GR2 | Le descripteur enrichi conserve le fonctionnement du stockage | 35 méthodes de régions et deux curseurs | P — exécutions UBSan, pas de preuve générale |

Le refus initial de pop est conservé dans validation/inline-vector-pop-baseline.log ;
le cycle pop ci-dessus raccorde ce cas. Les autres opérations restent ouvertes.


Lot précédent terminé : [références nominales dans Vector<T>](cycles/INLINE_VECTOR_NOMINAL_CYCLE.md).
Ciblé O0/UBSan : **11 méthodes, 11 exécutions C, 20 variantes refusées** aux
deux entrées. Régression O2/UBSan : **121 méthodes, 79,234 s, code 0**,
empreintes inchangées. Aucun changement normatif.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, ST7/ST17/ST18 | Les descripteurs des cibles entières/intérieures sont conservés par copy/remove | Lectures après drop des porteurs/vector, champs imbriqués, C conservé | P — références nominales représentées ; pas toutes les récursions |
| B1–B5, ST11/ST12 | Exclusivité et dernier usage portent sur la cible et la capacité | Mutations/drop prématurés refusés, copie mutable refusée, champ distinct accepté | P — cas énumérés sync/async |
| T4/T5/T6, F2–F4, AS2/AS8/AS11–AS13 | Les contrats et captures conservent la durée de vie des références | Insertion injectée, relais remove, copies via fonction, yield et join | P — cibles trop courtes refusées, pas de généralisation à tous les graphes |

Lot précédent terminé : [champs empruntés dans Vector<T>](cycles/INLINE_VECTOR_BORROWS_CYCLE.md).
19 méthodes ciblées : 20 exécutions C et 32 variantes refusées aux deux entrées.
Régressions finales O2/UBSan : **194 méthodes, 151,310 s**, puis complément
**85 méthodes, 95,054 s**, codes 0 et empreintes inchangées.
Le rapport conserve les défauts intermédiaires et la fixture Select préexistante corrigée.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, T1/T4/T5 | Le stockage inline conserve les emprunts, sans retenir le slot du porteur consommé | Push nommé/frais, copy/remove, scope enfant, C conservé | P — Int/&Int/&mut Int imbriqués ; propriétaires et références nominales ouverts |
| B1–B5, ST17/ST18 | Copies partagées et extraction mutable gardent les cibles réservées | Drop/mutation refusés avant dernier usage ; libération séparée de deux cases | P — union conservatrice après appels et certaines branches |
| F2–F4, T6 | Contrats d’insertion/extraction et retour transmettent les champs | Relais, construction fraîche injectée, copies via fonction | P — signatures testées, pas de preuve de complétude |
| AS2/AS8/AS11–AS13, L1/L6 | Capture, join et nettoyage préservent les cibles et le réemploi | Sync/async, yield, drop du vector avant lecture du résultat, pool réutilisé | P — UBSan O0/O2 ; audit indépendant non supposé |


Lot précédent terminé dans son périmètre : [transferts nommés vers Vector<T>](cycles/INLINE_VECTOR_MOVES_CYCLE.md).
Sept méthodes ciblées : 15 exécutions C, 19 invalides aux deux entrées.
Régression finale O2/UBSan : **126 méthodes, 77,073 s, code 0** ;
44 empreintes inchangées. Le rapport conserve le premier passage dont un test
échouait sur le diagnostic, malgré le refus correct du programme.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1/VE2, H1, T1 | Transfert explicite d’une valeur locale ; T reste distinct de A<T> | Push nommé, ancien nom/refus, erreurs de type directes et via contrats | P — structures à feuilles Int, imbriquées ou vides |
| B1–B5, T4/T5 | Dernière utilisation des emprunts et passage des scopes préservés | Emprunt avant/après push, entrée enfant explicite, relais avec réemprunt | P — vector réservé en entier |
| AS2/AS8, F2–F4 | Capture et relais conservent le stockage requis | Exigences locales des contrats inspectées, capture avec yield, pont C synchrone | P — signatures du lot, sans généralisation aux champs empruntés/propriétaires |
| L1/L6, VE3 | Nettoyage de la valeur consommée, extraction indépendante et réemploi | Boucles de transfert entre vectors, pool réutilisé, C conservé | P — runtime inchangé, UBSan O0/O2 ; pas de preuve générale |

Lot précédent terminé dans son périmètre : [match consommant des résultats de join](cycles/CONSUMING_JOIN_MATCH_CYCLE.md).
Sept nouvelles méthodes : 12 exécutions C, dont trois échecs de lancement
injectés, sept invalides aux deux entrées. Ciblé O0 final avec un test existant :
8 méthodes réussies. Régression O2/UBSan : **216 succès avant ENOSPC**, puis
**7 méthodes rejouées avec succès** (11,103 s, code 0), soit les 223 méthodes
sélectionnées. Les 31 empreintes sont inchangées ; le rapport conserve l’arrêt
initial code 120 et la reprise, sans les présenter comme un seul passage vert.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2, AS11, MT7 | Le match consommant résout le type réel du Result | Fixtures Int et A<Vector<Point>>, Handle public et relais, maintenant exécutées | P — écart de notation précédent corrigé dans les formes testées |
| U1, H1, L6 | L’ancien propriétaire est invalidé et les motifs propriétaires ne peuvent être ignorés | Reprise/drop du Result refusés, motifs `_`, destruction et réemploi du slot | P — branches de succès et échec, runtime inchangé |
| B1–B5, AS13/AS15 | Le payload emprunté garde sa cible réservée | Mutation/drop avant dernier usage refusés ; mutation ensuite acceptée | P — référence Int et graphes existants de la régression |
| T1/T6, ST18 | Une valeur locale extraite ou construite reste locale | Retour Point alternatif dans Err, lancement réussi/échoué, A<Point> refusé | P — placement des constructeurs frais, pas promotion du stockage existant |
| VE3/VE4, F2 | Replace/try_push conservent les deux provenances et le cas unitaire | Contrats synchrones/async, références mutables, wildcards, régressions existantes | P — familles sélectionnées ; ne clôt pas Vector<T> général |

Lot précédent dans son périmètre : [structures en ligne dans les vecteurs async](cycles/ASYNC_INLINE_VECTORS_CYCLE.md).
Huit méthodes ciblées O0/UBSan : 14 exécutions C réussies, huit invalides aux
deux entrées. Régression O2/UBSan : **226 méthodes, 215,753 s, code 0** ;
31 empreintes de compilateur/test inchangées pendant l’exécution.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, ST17/ST18, AS8/AS9 | Cases Point en ligne, copies/extractions indépendantes malgré yield | Pools locaux/injectés, deux fronts et région, copy/remove puis drop du vector | P — Point à feuilles Int et Empty ; autres champs ouverts |
| AS2/AS10–AS15, B1–B5 | Capture protège le receveur jusqu’à l’attente ; nettoyage et réemploi | Emprunt mutable, transfert, drop inactif, refus lecture/drop avant join | P — cas énumérés, sans preuve générale d’ordonnancement |
| T1/T6, H1–H3, AS11 | Le résultat local et le résultat en pool gardent leur catégorie et leur durée de vie | Point retourné par await/join ; A<Vector<Point>> par Handle public et relais Result | P — signature A<Point> et pool trop court refusés |
| B4a, AS4 | Le receveur reste réservé pendant l’évaluation suspendable de l’indice | remove(index().await), résultat lu après yield | P — emprunt du vector entier |
| F2 | Match consommant explicite d’un Result de join | Deux fixtures minimales et consuming-join-match-baseline.log | Écart historique corrigé dans CONSUMING_JOIN_MATCH_CYCLE.md ; cette ligne conserve le constat initial |

Lot précédent dans son périmètre : [extraction de structures en ligne](cycles/INLINE_VECTOR_REMOVE_CYCLE.md).
Huit méthodes ciblées O0/UBSan réussies : 15 exécutions C (13 succès, deux arrêts
de bornes attendus), huit invalides aux deux entrées. Régression O2/UBSan :
**185 méthodes, 116,345 s, code 0**, empreintes inchangées.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE4, ST17/ST18 | Extraction de T indépendant, ordre et longueur préservés | Retrait puis copie du reste, destruction du vecteur, deux fronts, structure vide | P — feuilles Int, sans champs empruntés/propriétaires |
| T1/T6, F2–F4 | Le résultat extrait survit à son scope producteur et au pool du vecteur | Bloc, if vrai/faux, break, fonction et relais | P — réservation dans le destinataire ; pas de promotion vers A<T> |
| B1–B5, ME1/ME2 | Le receveur reste protégé pendant les arguments et les prêts actifs | Dernier usage accepté, accès pendant argument et après drop refusés | P — emprunt du vecteur entier |
| TF1–TF5 | La méthode abstraite conserve le type Point extrait | Retirer.remove produit Point ; signature Int refusée | P — résolution statique et contrat synchrone |
| Inférence | Une opération source a une provenance stable entre les passes | Relais qui ne convergait pas, corrigé et exécuté | P — test déterministe, pas de preuve générale de terminaison |
| Suite | Généralisation de Vector<T> | Limites du rapport | Ouvert : autres champs/opérations et intégration async |

Lot précédent : [structures directement dans les vecteurs](cycles/INLINE_STRUCT_VECTORS_CYCLE.md).
Huit méthodes ciblées O0/UBSan réussies : 10 C natifs (8 succès, 2 arrêts de
bounds attendus), 7 invalides aux deux entrées. Régression O2 : 373 méthodes,
une erreur de fixture préexistante reproduite sur le snapshot initial ;
complément après correction : **30 méthodes, 16,386 s, code 0**. Aucun échec
inexpliqué dans cette sélection ; détails et limites dans le rapport.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| VE1/VE2, H1 | Cases de type Point contenant ses champs, distinctes de A<Point> | Insertion de constructions/copies, layout C, rejet de A<Point> | P — structures à feuilles Int, imbriquées ou vides |
| ST17/ST18, T1/T6, F2–F4 | Copie explicite indépendante, reçue dans le parent/appelant | Copie après drop, fin du pool enfant, retour et relais | P — stockage anticipé du résultat local |
| B1–B5, D1–D3 | Pas de mutation pendant le prêt encore utilisé, ni lecture après drop | Sept invalides aux deux entrées, dernier usage accepté | P — emprunt du vecteur entier ; emprunts des cases à raccorder |
| GR1/GR2, G9/G12 | Taille/alignement corrects sur deux fronts et en région | Croissance de deux vecteurs, réemploi, structure vide | P — chemins ciblés, sans optimisation anticipée des régions |
| VE4 | L’index est contrôlé avant lecture | Deux arrêts natifs pour -1 et longueur | P — UBSan fatal ; aucun index invalide lu |
| Suite VE1–VE6 | Généralisation des éléments et opérations | Limites dans le rapport | Ouvert : références, propriétaires, déplacements nommés, extraction, tranches, async |
| AS8–AS12, H1–H3, B1–B5 | Consommateur async de Result et éléments portant &Point | Trois fixtures antérieures, vector-supplemental-native.log : trois sorties 7 et nettoyage unique | P — trois exécutions O0/UBSan, sans généralisation à tous les graphes |

Lot précédent : [captures et réceptions imbriquées de Result de vecteurs](cycles/ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md).
Sept nouvelles méthodes ciblées : 9 C natifs dont un échec de lancement injecté,
9 invalides aux deux entrées. Régression O2/UBSan : **296 méthodes, 244,806 s, code 0**.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, H1–H3, VE1–VE4 | Captures et déballages successifs conservent les éléments et leurs prêts | Deux niveaux de tâches, réceptions imbriquées, descendant Inner | P — neuf exécutions C ciblées |
| F2–F4, T4 | Branches et sorties de boucle conservent le graphe du résultat | Match, if et break ; transfert descendant explicite dans les blocs | P — chemins ciblés, sans corrélation générale indice/branche |
| B1–B5/B4c, D1–D3 | Cible protégée après réception et pendant la capture inactive | Neuf invalides, dont accès mutable concurrent et drop prématuré | P — deux entrées du compilateur |
| AS10, nettoyage | Destruction unique et réemploi après capture inactive ou lancement refusé | Deux destructions Item avec réemploi, une sur échec, une Inner en succès | P — UBSan fatal, pas de nouvelle campagne de mutations |
| Régression / modèles | Contrats, collections, structures, async et Select | 296 méthodes, modèles existants et empreintes inchangées | P — pas de preuve générale |
| Suite VE1 (historique) | Stockage direct de valeurs structurées dans Vector<T> | open-inline-struct-vector.crust/.log : ancien refus « allocation Int » | Premier raccordement ci-dessus ; l’exemple valide corrigé exige copy(v[0]) selon ST17 |

Lot précédent : [relais des Result contenant un vecteur async](cycles/ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md).
Cinq nouvelles méthodes ciblées : 6 C natifs dont un échec de lancement injecté,
7 invalides aux deux entrées. Quatorze méthodes antérieures rejouées.
Régression O2/UBSan : **289 méthodes, 240,778 s, code 0**.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2–F4, H1–H3, VE1–VE4, AS12 | L’enveloppe Result conserve le type, les éléments et leurs prêts lors des relais | Relais direct et successif, cible mutable et descendant possédé | P — six exécutions C ciblées |
| B1–B5/B4c, D1–D3 | Cible encore empruntée protégée après transfert du Result | Drop prématuré, lecture/écriture mutables concurrentes refusés | P — sept invalides aux deux entrées, dont flèche manquante |
| AS10, nettoyage | La charge est détruite une seule fois lors de l’échec de lancement | Err injecté, une destruction Item ; cas vide ; une destruction Inner en succès | P — cas ciblés, sans nouvelle campagne de mutations |
| Régression / modèles | Contrats, graphes, stockage, async et Select conservés | 289 méthodes, empreintes inchangées et modèles existants rejoués | P — pas de preuve générale ni de nouveau modèle du Result |
| Suite | Capture du Result dans une autre tâche puis réception imbriquée | open-async-vector-result-capture.crust/.log | Éléments perdus à la réception ; correction à venir |

Lot précédent : [contrats publics de handles de vecteurs](cycles/ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md).
Quatre nouvelles méthodes ciblées O0 réussies : 4 C natifs, 6 invalides aux deux
entrées ; dix méthodes du lot précédent rejouées. Régression O2/UBSan :
**284 méthodes, 277,479 s, code 0**.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, F2–F4, H1–H3 | Un contrat public conserve les sources et prêts de son résultat | Fonction wait, relais de handle, réception nommée et extraction | P — quatre exécutions C ciblées |
| B1–B5/B4c, D1–D3 | Le résultat garde ses cibles réservées après attente | Six invalides aux deux entrées ; prêts partagés/mutables et descendant Inner | P — pas de preuve générale de composition |
| Vérificateur / C | Les deux chemins conservent les métadonnées [] | Contrats symboliques et génération du programme minimal | P — sources d’éléments vérifiées, invariant interne maintenu |
| Régression / modèles | Collections, contrats, structures, async et Select | 284 méthodes, modèles existants rejoués, compilateur inchangé | P — pas de nouveau modèle indépendant |
| Suite | Transfert du Result déjà reçu à une fonction relais | open-async-vector-result-relay.crust/.log | Refus interne reproduit aux deux entrées ; correction à venir |

Lot précédent : [retours async de vecteurs](cycles/ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md).
Dix méthodes ciblées O0 : 9 exécutions C et 9 invalides aux deux entrées.
Régression O2/UBSan : **280 méthodes, 236,594 s, code 0**.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, H1–H3, VE1–VE4 | Le vecteur retourné conserve ses éléments après nettoyage de l’état | Await, join, fabrique, deux transferts async, vide et A<Int> | P — neuf exécutions C ciblées |
| B1–B5/B4c, D1–D3 | Cibles et pools survivent au résultat ; exclusivité mutable | Neuf invalides, drop après join, lecture/écriture concurrente, pool court | P — graphes empruntants et descendants Inner |
| F2–F4, graphes | Réception et extraction restaurent le stockage et les prêts | Résultat nommé et graphe imbriqué dans l’analyse des contraintes | P — suivi conservatif par chemin [] |
| Régression / modèles | Suites collections, contrats, async, nettoyage et Select | 280 méthodes ; modèles existants rejoués | P — pas de nouveau modèle indépendant du graphe |
| Suite | Fonction recevant runtime::Handle<A<Vector<A<Item>>>> | open-async-vector-payload-handle-return.crust/.log | Écart reproduit aux deux entrées ; correction à venir |

Lot précédent : [contrats de vecteurs depuis async](cycles/ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md).
Six méthodes ciblées O0 réussies : 8 exécutions C, 11 invalides aux deux entrées.
Régression O2/UBSan : **270 méthodes, 269,141 s, code 0**.
Insertion et extraction par contrats, descendants possédés et pont C symbolique.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| F2–F4, VE1–VE4, AS8–AS12 | Les effets d’insertion sont publiés dans l’état async | Appels directs, relais et extraction par &mut ou transfert | P — huit exécutions C ciblées |
| B1–B5/B4c, D1–D3 | Cibles et pools survivent à la charge retournée | Onze invalides aux deux entrées, dont pool du descendant trop court | P — graphes Int et charges imbriquées exercés |
| H1–H3, nettoyage | Le pont garde le graphe symbolique sans lire une case absente | Vecteur vide, Some/None, descendant Inner et réemploi | P — pas de graphe d’emprunts ajouté au runtime |
| Régression / modèles | Contrats, structures, collections, async et Select conservés | 270 méthodes, modèles existants rejoués | P — pas de nouveau modèle indépendant des graphes |
| Suite | Retour async d’un conteneur entier | open-async-vector-payload-return.crust/.log, refus aux deux entrées | Écart d’implémentation restant |

Lot précédent : [graphes des vecteurs async](cycles/ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md).
Douze méthodes ciblées O0 réussies : 15 exécutions C, 18 invalides aux deux
entrées. Régression O2 de 264 méthodes : deux méthodes historiques à corriger,
puis complément de 14 méthodes réussi sur le compilateur inchangé. Le rapport
distingue ces exécutions d’une passe monolithique verte.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| AS2/AS5/AS8/AS9, H1–H3 | Les captures gardent les prêts et pools des éléments | Direct, fabrique, relais inactif, parent async et descendant possédé | P — graphes Int et charges testées |
| B1–B5/B4c, D1–D3 | Les cibles survivent à la capture et à l’extraction | 18 invalides, exclusivité mutable et pool trop court | P — chemins locaux joints de façon conservative |
| VE1–VE4, AS10 | Les résultats des opérations gardent leurs prêts jusqu’au nettoyage | Push/remove/pop/replace/try_push, réemploi, None et vecteur vide | P — 15 exécutions C ciblées |
| Régression | Captures, contrats, Select et modèles antérieurs | 264 méthodes + complément O2 de 14 ; échecs initiaux documentés | P — compilateur inchangé pendant ces deux passes |
| Écart suivant | Effets d’insertion par appel synchrone depuis async | open-async-vector-payload-sync-call.crust/.log | Défaut reproduit : drop anticipé accepté ; correction nécessaire |

Lot précédent : [retours de vecteurs complexes](cycles/VECTOR_PAYLOAD_CONTAINERS_CYCLE.md).
Neuf méthodes ciblées O0 réussies : 12 exécutions C, 18 invalides aux deux
entrées ; régression O2/UBSan : **168 méthodes, 164,706 s, code 0**. Fabriques, relais, branches, suppressions,
remplacements d’éléments et graphes empruntants/propriétaires.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE4, F2–F4 | Les retours conservent les graphes actifs des éléments | Fabriques, relais, branches, suppression et remplacement avant retour | P — 12 exécutions C, graphes joints par provenance |
| B1–B5/B4c, D1–D3 | Les pools et cibles survivent ; les prêts mutables restent exclusifs | 18 invalides refusés aux deux entrées | P — références Int et descendants possédés exercés |
| Nettoyage et stockage | Les éléments extraits se détruisent une fois et les slots sont réutilisables | Traces Item/Inner, réemploi de capacité 1 | P — configurations ciblées |
| Régression / modèles | Contrats, options, échanges, async et stockage antérieurs | 168 méthodes ; modèles existants de durées de vie et de stockage | P — pas de modèle indépendant nouveau des conteneurs |
| Suite | Capture async d’un vecteur empruntant | open-async-vector-payload-graph.crust/.log | Écart explicite restant |

Lot précédent : [graphes des échanges de vecteurs](cycles/VECTOR_PAYLOAD_EXCHANGES_CYCLE.md).
Sept méthodes ciblées O0, 6,890 s, code 0 : **14 exécutions C et 18 invalides
aux deux entrées**. Régression O2/UBSan : **159 méthodes, 158,585 s, code 0**.
Aucun changement normatif ; métadonnées des variantes et capacités déplacées
raccordées aux contrats et à leurs contrôles.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1, VE3–VE4, B4c | Chaque variante conserve sa charge et ses dépendances | Replace index valide/invalide, try_push disponible/plein, retours et relais | P — charges Int empruntées et descendants exercés |
| B1–B5, D1–D3 | Cibles et pools survivants, exclusivité préservée | Drop prématuré, pool court, lecture/écriture concurrente et seconde capture mutable refusés | P — identité de capacité conservée lors du déplacement |
| U1, F2–F4, L1/L6 | Usage explicite et destruction selon la variante effective | Drop direct, Ok(())/Err(Item), traces Item/Inner et réemploi | P — 14 exécutions C ; pas de preuve générale |
| Régression et modèles | Contrats, options, résultats async et stockage antérieurs conservés | 159 méthodes ; modèles de durées de vie et stockage rejoués | P — pas de modèle indépendant nouveau des échanges |
| Suite | Retours de vecteurs entiers contenant des emprunts | open-vector-payload-container-contract.crust/.log : refus explicite aux deux entrées | Écart d’implémentation ; intégration générale encore ouverte |

Lot précédent : [options des éléments empruntants](cycles/VECTOR_PAYLOAD_OPTIONS_CYCLE.md).
Sept méthodes ciblées O0, 5,724 s, code 0 : **13 exécutions C et 13 invalides
aux deux entrées**. Régression O2/UBSan : **152 méthodes, 150,976 s, code 0**.
Les refus incorrects du cas None imbriqué ont été corrigés sans modification normative.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE3, B4c | L’option conserve les dépendances de sa charge à travers un appel | Some/None, retour et relais, consommateur avec fallback | P — références Int et descendants testés |
| B1–B5, D1–D3 | Cibles et pools survivent aux résultats transférés | Drop prématuré, capture mutable et pool trop court refusés | P — 13 programmes invalides aux deux entrées |
| U1, F2–F4, L1/L6 | Consommation explicite et nettoyage unique selon la variante | Flèche/usage/double consommation, traces Item/Inner ; None en match instruction/expression | P — pas de dépendances fictives pour None établi |
| Régression et modèles | Options simples, contrats, async et stockage préservés | 152 méthodes ; modèles existants à huit et quatre combinaisons | P — pas de nouveau modèle indépendant d’options |
| Suite | Result d’éléments empruntants, vecteurs entiers et async | open-vector-payload-exchange-contract.crust/.log : refus explicite aux deux entrées | Écarts d’implémentation ; objectif global actif |

Lot précédent : [contrats des éléments de vecteurs](cycles/VECTOR_PAYLOAD_CONTRACTS_CYCLE.md).
Dix méthodes ciblées : 15 exécutions C, 22 invalides aux deux entrées et deux
vérifications isolées sans corps de fonctions. Après correction de deux refus
incorrects de variantes : 19 méthodes O0, 19,768 s, code 0 ; régression finale
O2/UBSan : **145 méthodes, 144,001 s, code 0**. Aucun changement normatif.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE4 | Provenances et graphes des éléments conservés dans les appels | Insertion fraîche/transférée, extraction, relais, remplacement | P — contrats synchrones directs |
| B1–B5, D1–D3 | Les cibles et pools des descendants survivent au receveur | Emprunts partagés/mutables, descendants propriétaires, insertions conditionnelles ; 22 invalides | P — unions conservatrices des chemins [] |
| B4c, F2–F4 | Appelant vérifié à partir des seuls contrats | Vérificateur isolé sans corps ni tables d’inférence ; admission et refus | P — cas d’insertion/extraction exercés |
| L1/L6 | Nettoyage unique et réemploi | Traces Item/Inner, pools de capacité 1, C11/UBSan | P — scénarios exécutés |
| Régression et modèles | Contrats et variantes précédents préservés | 145 méthodes ; modèles existants à huit et quatre combinaisons | P — pas de modèle indépendant nouveau des vecteurs |
| Suite | Options, Result, vecteurs entiers et async avec charges complexes | open-vector-payload-option-contract.crust/.log | Écarts d’implémentation, objectif global actif |

Lot précédent : [graphes des éléments de vecteurs locaux](cycles/VECTOR_PAYLOAD_GRAPHS_CYCLE.md).
Ciblé final O0/UBSan : onze méthodes, 7,029 s, code 0 ; 20 exécutions C,
28 programmes invalides aux deux entrées. Régression O2 : 135 méthodes,
113,766 s, code 1, sept sous-cas historiques en échec, reproduits avant le lot.
Après correction de leurs annotations T/A<T> : quinze méthodes, 10,713 s,
code 0 sur le même compilateur. Preuve combinée, pas un passage monolithique vert.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE4, H1 | Les éléments déplacés conservent leurs champs et responsabilités | Push/remove/pop, replace valide/invalide, try_push réussi, remplacement par emprunt de case | P — vecteurs locaux synchrones, charges exercées |
| B1–B5, D1–D3 | Un porteur conserve ses cibles et les pools de ses descendants | Références partagées/mutables, deux niveaux propriétaires, transferts trop courts refusés | P — 28 invalides aux deux entrées ; pas de preuve générale |
| F2–F4, B4c | Les jonctions et contrats ne perdent pas les dépendances de l’objet extrait | If/loop, réemploi en boucle, constructeur et relais d’un objet extrait | P — contrats du conteneur complexe encore ouverts |
| L1/L6, VE2–VE3 | Nettoyage unique et réemploi des slots | Traces Item/Inner et pools de capacité 1 ; drop direct des extractions | P — C11/UBSan O0/O2, preuves combinées du rapport |
| Régression et modèles | Conservations des contrats, graphes propriétaires et stockage | 135 méthodes puis complément de quinze ; modèles à huit et quatre combinaisons rejoués | P — sept annotations historiques corrigées, prédictions des modèles inchangées |
| Suite | Paramètres/résultats Vector<A<Item>> avec champs empruntés | open-vector-payload-contract.crust/.log : valide selon les règles, refus explicite actuel | Écart d’implémentation ; objectif global actif |

Lot précédent : [échanges async typés](cycles/TYPED_ASYNC_EXCHANGES_CYCLE.md).
Ciblé O0/UBSan : neuf méthodes, 12,541 s, code 0. 26 exécutions C dont cinq
LaunchFailed injectés ; quinze programmes invalides aux deux entrées.
Régression finale O2/UBSan : 135 méthodes, 183,427 s, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1, VE1–VE4, AS8/AS12, MT6 | Type et provenance de chaque charge conservés dans les enveloppes | Index valide/invalide, deux pools, profondeurs 1/3, captures et relais sync/async/publics | P — Point et charges grandissantes testés |
| B4c, AS12 | Les contrats de stockage et de variantes suivent await | Pertes de charge et de variantes corrigées ; contrats internes maintenus | P — dépendances transitives encore ouvertes |
| VE2–VE4, AS10/AS14, SL1–SL2 | Ok(()) ne détruit pas l’élément accepté ; Err nettoie le rejeté | Région 1 MiB pleine/non pleine, drop inactif, perdante Select, cinq LaunchFailed | P — cas déterministes exercés |
| U1, B1–B5, D1, AS13 | Transferts explicites, types exacts, sources survivantes | Quinze invalides aux deux entrées ; réemploi des deux pools après nettoyage | P — pas une preuve générale |
| Régression | Options, échanges Int, enveloppes, stockage et handles précédents | 135 méthodes O2/UBSan ; modèles de stockage et permissions rejoués | P — sélection consignée, pas de preuve générale |
| Suite | Éléments de vecteur à champs empruntés/propriétaires | open-vector-handle-borrowed-fields.crust/.log : refus explicite aux deux entrées | Incomplet ; objectif global actif |



Lot précédent : [options d’allocations typées en async](cycles/TYPED_ASYNC_OPTIONS_CYCLE.md).
Ciblé O0/UBSan : huit méthodes, 11,610 s, code 0. 26 exécutions C dont huit
échecs de lancement injectés ; 17 invalides aux deux entrées. Régression O2 :
119 méthodes, 163,268 s, code 0. Aucun changement normatif.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1, VE1–VE3, AS8/AS12, MT6 | Le type et la provenance survivent aux enveloppes et aux attentes | Option<A<Point>> ; profondeurs 1/3 ; handles publics et relais ; String et vecteurs numériques | P — types et profondeurs exercés |
| B4c, AS10/AS12 | Les contrats suivent les sources du résultat et les variantes possibles | Défauts d’enveloppe Int et de variantes corrigés ; cas et C avant/après conservés | P — charges sans dépendances transitives |
| AS10/AS14, L1/L6 | Nettoyage unique dans Some/None, drop inactif et échec de lancement | Huit injections LaunchFailed ; traces Point et réemploi des pools de capacité 1 | P — chemins déterministes testés |
| U1, B1–B5, D1, AS13 | Transfert explicite, types stricts et pool survivant | Mauvais types même sur None, double usage, source trop courte, accès avant join et résultat ignoré refusés | P — 17 programmes invalides, deux entrées |
| Régression | Les enveloppes Int, les résultats propriétaires et les contrats précédents restent applicables | 119 méthodes O2/UBSan, dont le modèle de rétention imbriquée (sept admis, cinq refus) | P — sélection consignée, pas une preuve générale |
| Suite | Signatures async des échanges replace/try_push typés | Ancien refus levé dans TYPED_ASYNC_EXCHANGES_CYCLE.md | Implémenté dans le périmètre de ce lot ; objectif global actif |


Lot précédent : [vecteurs de handles typés dans les états async](cycles/TYPED_ASYNC_HANDLE_VECTORS_CYCLE.md).
Neuf méthodes ciblées : seize programmes natifs et dix-sept invalides contrôlés
aux deux entrées. O0/UBSan : 7,286 s, code 0. Régression finale O2/UBSan :
84 méthodes, 80,216 s, code 0. Aucun changement normatif.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE3, H1, AS2/AS8 | Le conteneur conserve le type de ses cases et leurs pools pendant une suspension | Captures partagées/mutables/transférées ; push/remove, longueur, relais synchrones | P — Point, String et vecteurs numériques exercés |
| VE2, L1/L6, AS10/AS14 | Détruire le vecteur détruit les éléments restants une seule fois | Défaut de constructeur corrigé ; réemploi des deux pools ; drop de tâche inactive | P — charges sans dépendances transitives |
| F2–F4, U1 | Option/Result local conserve son type et sa responsabilité après yield | Some/None, annotations, replace valide/invalide ; refus de Vector<A<Point>> recevant A<Int> | P — signature async de ces résultats encore ouverte |
| B1–B5, D1 | Les captures et sources restent protégées jusqu'à l'attente | Réutilisation prématurée et double usage après transfert refusés aux deux entrées | P — cas exécutés |
| Limite de charge | Les champs empruntés/propriétaires nécessitent des métadonnées supplémentaires | Refus explicite sur paramètres async et pools locaux | Incomplet ; aucune nouvelle restriction normative |
| Régressions | Parcours Int et typés synchrones précédents conservés | 84 méthodes, options et échanges, relais, sorties et nettoyage | P — sélection documentée |
| Suite | Retour de Option<A<Point>> depuis une tâche, join et paramètres typés | Ancien refus levé dans TYPED_ASYNC_OPTIONS_CYCLE.md | Ouvert ; objectif global inchangé |

Lot précédent : [retours nominaux T/A<T>](cycles/STRICT_STRUCTURE_RETURNS_CYCLE.md).
Six nouvelles méthodes : neuf programmes natifs et quatorze invalides aux deux
entrées. Ciblé final : 21 méthodes, 18,702 s, code 0 (O0/UBSan et quatre
Foundation à leur configuration O2 historique). Régression étendue O2 :
276 méthodes, 233,082 s, code 1 ; 270 réussissent et six anciens snippets restent
chargés avant leur migration. Le complément réexécute les deux suites migrées :
14 méthodes, 11,973 s, code 0. Les six échecs sont tous clôturés dans ce
complément ; les 276 méthodes distinctes ont une preuve de succès sur le code
final. Il s'agit de résultats combinés, pas d'une passe monolithique verte.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| V1, T6, H1, brouillon 05 | Un retour nominal T reste local ; A<T> reste dans son pool | Fabriques, relais, retour explicite/final implicite ; retour de charge de replace sous Point refusé aux deux entrées | P — retours nominaux, pas redéfinition des primitives historiques |
| B4c–B4e, F3 | Exigences de stockage transmises par contrat | Paramètres symboliques, helpers de copie, fonctions non appelées, branches, async/join | P — scénarios exécutés |
| B1–B5, D1, L1/L6 | Le transfert respecte les derniers usages et le nettoyage | Emprunt avant transfert accepté, usage après refusé ; drop et réemploi des slots | P — pas une preuve générale |
| ST11–ST14, B4c | Le masquage d'un nom ne change pas le porteur d'un emprunt préexistant | Défaut reproduit sur snapshot initial ; valeurs 1/3 et drop des deux cibles contrôlés après correction | P — mise à jour du porteur local par identité |
| Restitution et détachement | Les règles déjà étendues ne doivent pas rester refusées par d'anciens tests | Trois oracles obsolètes migrés ; identité, destructions et réemploi exécutés ; cible partagée encore protégée | P — reset seulement dans le profil legacy des tests historiques |
| Régressions | Retours, copies, vecteurs typés, tâches, Select, champs et enveloppes | 276 méthodes distinctes avec preuve combinée de succès ; logs et manifeste dans le rapport | P — sélection documentée, pas toute la suite |
| Suite | Options/résultats typés async et charges complexes | open-typed-async-vector-option.crust/.log : signature async Option<A<Point>> refusée aux deux entrées | Ouvert ; objectif global actif |

Lot précédent : [contrats synchrones Option<A<T>>](cycles/TYPED_VECTOR_OPTIONS_CYCLE.md).
Huit méthodes ciblées, 21 exécutions natives et onze invalides aux deux entrées.
O0/UBSan : huit méthodes, 7,113 s, code 0. Régression O2/UBSan : 87 méthodes,
100,393 s, code 0 (trois méthodes Foundation avec leur configuration native).

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| VE3, H1, types | Some et None conservent le type T de Option<A<T>> | Annotations, arguments, relais ; mauvais type refusé même sur None | P — Point, String, vecteurs numériques, synchrone |
| F3, U1 | Résultat reçu/transféré/consommé explicitement | If, loop/break, paramètres, drop direct et nommé ; onze invalides aux deux entrées | P — cas exécutés |
| Durée de vie et nettoyage | L'option possède seulement sa charge, sans retenir inutilement le vecteur vidé | Résultat survivant au vecteur ; pool de charge trop court refusé ; réemploi après Some/None | P — charges sans dépendances transitives |
| B1–B5 | Pop respecte la dernière utilisation des emprunts de cases | Emprunt utilisé avant pop admis, usage restant après refusé | P — case littérale Point |
| Régressions | L'absence de charge reste respectée dans les options et enveloppes historiques | 87 méthodes O2/UBSan, options vides, branches, boucles et états async existants | P — nouvelles enveloppes async typées non raccordées |
| Suite | Distinction des retours T/A<T>, charges complexes et async typé | Écarts listés dans la checklist globale et rapports | Ouvert ; aucune clôture globale |

Lot précédent : [résultats typés de replace/try_push](cycles/TYPED_VECTOR_EXCHANGES_CYCLE.md).
Neuf méthodes ciblées, 30 exécutions natives et neuf invalides aux deux entrées.
O0/UBSan : neuf méthodes, 11,012 s, code 0. Régression O2/UBSan : 78 méthodes,
86,134 s, code 0. Un écart de typage de retour T/A<T> reste explicitement ouvert.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| VE3–VE4, H1 | Le résultat porte le handle et la source correspondant à sa variante | replace succès/indice invalide ; try_push succès/région de 1 Mio pleine | P — Point ; charges String et vecteurs numériques pour replace |
| F3–F4, contrats | Type de charge et provenances des bras conservés | Fonctions, relais, consommation injectée, if et loop/break ; retour du bras durable | P — synchrone, neuf méthodes ciblées |
| U1, F2, L6 | Transfert explicite, usage et destruction du seul contenu possédé | 30 exécutions natives, traces et réemploi ; neuf programmes invalides aux deux entrées | P — pas une preuve générale |
| V1/T6, H1 | T local et A<T> ne sont pas interchangeables | Annotation locale de la charge refusée ; retour A<Point> explicite vérifié | P — signature historique Point encore trop permissive, voir ligne suivante |
| Écart de signature | Le type public du retour doit conserver la distinction T/A<T> | open-plain-structure-return-from-handle-result.crust/.log : A<Point> accepté sous retour Point | Historique : corrigé dans STRICT_STRUCTURE_RETURNS_CYCLE.md ; fixture et log initiaux conservés |
| Régressions | Les résultats et enveloppes historiques conservent leurs comportements | 78 méthodes O2/UBSan, erreurs runtime injectées existantes | P — enveloppes async A<Int> seulement |
| Suite | Contrat de pop typé | open-typed-vector-option-contract.crust/.log : Option<A<Point>> refusé aux deux entrées | Historique : contrat synchrone raccordé dans TYPED_VECTOR_OPTIONS_CYCLE.md |
| Suite dépendances/async | Charges complexes et enveloppes runtime typées | Pas couvert par ce lot ; signatures async nouvellement typées refusées explicitement | Ouvert |

Lot précédent : [vecteurs de handles typés](cycles/TYPED_HANDLE_VECTORS_CYCLE.md).
Sept méthodes ciblées, neuf exécutions natives et neuf invalides aux deux entrées.
O0/UBSan : sept méthodes, 3,782 s, code 0. État final : régression de 59 méthodes,
45,216 s, code 0 ; O2/UBSan pour le harness async et cinq tests Foundation avec
leur configuration native historique.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H3, VE1–VE3 | Type de cible et source conservés dans les cases et extractions | Point, String, Vector<Int/u8>, remove, pop local, nettoyage et réemploi | P — neuf programmes natifs ; pas tous les T |
| VE2, F3, stockage | Le pool de chaque cible survit aux receveurs | Deux pools, bloc producteur, paramètres et relais explicite ; local T refusé pour A<T> | P — opérations synchrones testées |
| B1–B5, H2 | Emprunt de case typé, remplacement exclusif et nettoyage unique | Comparaison, remplacement via &mut A<Point>, extraction pendant prêt refusée | P — case littérale, structure à champ Int |
| U1, F4 | Transferts explicites et consommation unique | Neuf programmes invalides aux deux entrées | P — cas énumérés |
| Régressions | Conservation des comportements A<Int> et des exigences de stockage | 59 méthodes, sorties natives et modèles existants | P — pas d'audit indépendant ni de preuve générale |
| Suite VE3–VE4 | replace/try_push restitue un handle du type des cases | open-typed-vector-exchange.crust/.log : refus explicite aux deux entrées | Historique : raccordé dans TYPED_VECTOR_EXCHANGES_CYCLE.md pour les cas synchrones testés |
| Suite dépendances | Les champs des cibles transportent leurs durées de vie | Cibles propriétaires/empruntées explicitement non raccordées | Ouvert ; async et enveloppes typées restent aussi à intégrer |

Lot précédent : [résultats propriétaires à profondeur variable](cycles/RECURSIVE_OWNED_JOIN_CYCLE.md).
Sept méthodes nouvelles : 19 exécutions natives et huit invalides aux deux
entrées. Une méthode historique actualisée ajoute huit exécutions natives et
trois refus via verify_program. Ciblé O0/UBSan : huit méthodes, 10,001 s,
code 0. Régression O2/UBSan : 186 méthodes, 231,142 s, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT6, H1–H2, AS10 | Chaque attente ajoute une enveloppe ; chaque extraction en retire une | A<Int> à trois/cinq niveaux, échec de chaque lancement, destruction unique et réemploi | P — profondeurs exécutées |
| Types et stockage, AS12–AS13 | Type de charge et distinction T/A<T> conservés | Int, String, vecteurs numériques, View local ; mauvais stockage et pool trop court refusés | P — types testés, pas toutes les charges possibles |
| B1–B5, AS12 | Les dépendances du résultat survivent aux attentes et extractions | View avec &Int, drop prématuré de la cible refusé ; régressions de graphes propriétaires/empruntés | P — cas exécutés |
| U1, F3–F4, RT7 | Consommation et attentes explicites | Helpers, handle public, fabriques, if/loop ; huit invalides nouveaux et trois historiques | P — les trois historiques sont vérifiés seulement par verify_program |
| AS8–AS14, SL1–SL2 | Captures et temporaires suspendus restent nettoyables | Capture active/inactive et perdant Select, destruction unique | P — scénarios ciblés |
| Attente nommée | Le type est déterminé avant consommation de l'instance | TypeError préexistant reproduit sur sauvegarde, corrigé et gardé en régression | P — instance nommée et fabrique |
| Régressions | Les autres enveloppes et effets gardent leurs comportements testés | 186 méthodes, UBSan fatal, modèles existants Select/réveil | P — audit indépendant distinct, aucune preuve générale |
| Suite | VE1–VE3 : vecteur homogène de handles d'autres types | open-vector-allocated-structure.crust/.log : Vector<A<Point>> refusé aux deux entrées | Historique : constructeur raccordé dans TYPED_HANDLE_VECTORS_CYCLE.md, famille encore partielle |

Lot précédent : [enveloppes runtime imbriquées d'Option<A<Int>>](cycles/ASYNC_NESTED_OPTION_JOIN_CYCLE.md).
Sept méthodes ciblées : 25 exécutions natives et sept invalides aux deux entrées.
O0/UBSan : 9,689 s, code 0. Régression O2/UBSan : 142 méthodes en 135,869 s,
code 0. Aucun changement normatif ; description récursive commune aux familles
optionnelles et aux résultats de replace/try_push.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3 | Chaque attente ajoute un Result ; Option reste une charge distincte | Some/None avec 2/3/5 enveloppes, extraction sync/async, fabrique | P — Option<A<Int>>, profondeurs exécutées |
| AS10/AS14, RT6 | Seul Some est détruit ; LaunchFailed nettoie ses captures | Injection à chacun des trois niveaux, avec/sans élément ; traces et réemploi | P — chemins exercés |
| AS12–AS13, H1–H2 | Le résultat conserve le pool de l'élément sans retenir le vecteur | Résultat hors du bloc du vecteur accepté ; source locale trop courte refusée | P — frontière de scope testée |
| U1, F3–F4, MT1 | Transferts explicites, consommation unique et réservation avant attente | Helper de handle public, relais, if/loop ; sept programmes invalides | P — cas ciblés |
| AS8–AS14, SL1–SL2 | Nettoyage conditionnel des captures et arguments suspendus | Capture active/inactive, argument préparé et perdant Select | P — Some/None exécutés |
| Description commune et régressions | Le registre partagé conserve les comportements des autres feuilles | 142 méthodes, dont enveloppes de replace/try_push et modèles Select/réveil | P — UBSan fatal ; pas d'audit approfondi ni de preuve générale |
| Suite | Imbrications supplémentaires des résultats d'allocations simples | open-async-nested-owned-join.crust/.log : refus de profondeur aux deux entrées | Ouvert ; objectif global non clôturé |

Lot précédent : [enveloppes runtime imbriquées de replace/try_push](cycles/ASYNC_NESTED_EXCHANGE_JOIN_CYCLE.md).
Huit méthodes ciblées : 21 exécutions natives et six invalides aux deux entrées.
O0/UBSan : 8,848 s, code 0. Régression O2/UBSan : 135 méthodes en 121,391 s,
code 0. Description récursive ; deux, trois et cinq enveloppes exécutées.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3–VE4 | Chaque attente ajoute un Result distinct ; seul le contenu présent est possédé | Profondeurs 2/3/5, succès/refus de replace ; try_push avec région disponible/pleine | P — deux feuilles A<Int>, pas de preuve pour toute profondeur |
| RT6, AS10/AS14 | Un lancement échoué nettoie ses captures et ne crée pas de résultat métier | Injection à chacun des trois niveaux, destruction unique de l'entrant | P — chemins injectés |
| AS12–AS13, H1–H2 | Provenances par bras conservées à travers les enveloppes | Extraction après disparition du pool entrant ; source de l'ancienne allocation trop courte refusée | P — pools distincts, adresses cibles non déplacées par la représentation |
| U1, F3–F4 | Transferts et consommation explicites dans les helpers et jonctions | Handle public, relais, if/loop ; usage absent, double consommation, motif ignorant et transfert absent refusés | P — cas ciblés |
| AS8–AS14, SL1–SL2 | Nettoyage conditionnel après suspension ou destruction inactive | Capture exécutée/inactive, argument préparé et perdant Select ; réemploi | P — traces testées |
| Contrats et émission C | Les types enregistrés après import sont reconnus à toutes les étapes | Défaut de table figée corrigé ; profondeurs successives dans un même processus | P — signatures et C des programmes exécutés |
| Régressions | Comportements existants exercés après généralisation | 135 méthodes, modèles Select et réveils, UBSan fatal | P — audit approfondi distinct, aucune preuve générale |
| Suite | Enveloppes d'Option<A<Int>> et d'autres charges | open-async-nested-option-join.crust/.log : refus de profondeur reproduit aux deux entrées | Ouvert ; ce lot ne clôt pas l'objectif global |

Lot précédent : [résultats de replace/try_push enveloppés par spawn/join](cycles/ASYNC_EXCHANGE_JOIN_CYCLE.md).
Onze méthodes ciblées : 33 exécutions natives et sept invalides aux deux entrées.
O0/UBSan : 15,461 s, code 0. Régression O2/UBSan : 127 méthodes en 127,747 s,
code 0. Les erreurs intermédiaires et la correction du ciblage d'une injection
de soumission sont conservées dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT6, VE3–VE4, U1 | Erreur de lancement distincte du résultat de l'opération | Join et await de handle ; succès, erreur interne et soumission échouée | P — enveloppes portant A<Int> |
| H1–H2, AS10–AS13 | La provenance accompagne chaque bras possédé | Handle public, helpers, capture, retour async et fabrique ; pools distincts, source courte refusée | P — cas exécutés |
| F3, transferts | Les jonctions conservent le résultat et ses obligations | Bloc, if et loop ; transfert absent, résultat inutilisé, double consommation et motif ignorant une charge refusés | P — provenance perdue à if corrigée |
| AS14, SL1–SL2, F4 | Nettoyage limité à la charge effectivement possédée | Drop, tâche inactive, argument préparé puis await, perdant Select ; try_push plein/non plein | P — destruction unique et réemploi testés |
| Contrats et pont C | Les identités entrantes restent dans le résumé du relais | Défaut de provenance corrigé, fonctions exécutées via le pont | P — pas de modification des invariants normatifs |
| Régressions | Les modes antérieurs restent exercés | 127 méthodes, contrats publics, modèles Select et réveils | P — audit approfondi distinct, pas de preuve générale |
| Suite reproduite | Lancer une tâche retournant déjà cette enveloppe ajoute un Result | open-async-nested-exchange-join.crust/.log, refus explicite aux deux entrées | Imbrications supplémentaires à généraliser |

Lot précédent : [captures et retours async des résultats de replace/try_push](cycles/ASYNC_HANDLE_EXCHANGE_RESULTS_CYCLE.md).
Dix méthodes ciblées : 28 exécutions natives et sept invalides aux deux entrées.
O0/UBSan : 13,515 s, code 0. Régression O2/UBSan : 109 méthodes en 105,405 s,
code 0. Un double nettoyage de capture inactive a été détecté et corrigé.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3–VE4, U1, AS2–AS5 | Capture et retour déplacent l'enveloppe avec le contenu possédé par sa variante | Succès/erreur, captures, retours directs/nommés ; flèche et double consommation vérifiées | P — A<Int>, await d'une instance inactive |
| AS10–AS13, contrats | Les sources du résultat survivent, indépendamment du vecteur | Fabrique, relais async, helper synchrone, pools distincts ; source courte refusée | P — provenances par bras |
| AS14, RT6 | Le nettoyage d'un état inactif ou non lancé ne détruit que ses captures possédées | Destruction inactive et échec de soumission ; réemploi ; UBSan a détecté le double nettoyage de try_push | P — défaut corrigé, reproduction conservée |
| F4, AS8–AS10, SL1–SL2 | Une capture préparée reste nettoyable pendant l'await de l'argument suivant | Continuation et perdant Select ; capacité disponible/atteinte ; destruction unique | P — chemins ciblés |
| B1–B5 | La tâche conserve la réservation jusqu'à son attente | Accès au vecteur avant await refusé | P — cas exécutés |
| Régressions | Contrats, options, captures et nettoyage existants préservés | 109 méthodes ; modèle existant de poll/nettoyage de Select | P — pas de nouveau modèle ou d'audit approfondi |
| Suite reproduite | Enveloppe extérieure de spawn/join de ces résultats | open-async-handle-exchange-join.crust/.log refusé explicitement aux deux entrées | Non raccordée ; restriction d'implémentation, pas normative |

Lot précédent : [résultats de replace/try_push dans les appels depuis async](cycles/ASYNC_HANDLE_EXCHANGE_CALLS_CYCLE.md).
Huit méthodes ciblées : dix-neuf exécutions natives et cinq invalides aux deux
entrées. O0/UBSan : 7,466 s, code 0. Régression : 131 méthodes en
87,844 s, code 0. Async et trois tests Foundation en O2/UBSan ; tableaux fixes
avec leurs paramètres par défaut, sans optimisation/sanitizer explicites.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3–VE4, U1 | Le transfert du résultat conserve le contenu possédé par chaque variante | Succès/erreur, retour et relais ; flèche, type, usage et double consommation vérifiés | P — helpers synchrones, A<Int> |
| F4, AS8–AS10 | L'argument préparé reste vivant pendant l'évaluation du suivant | Arguments nommés, imbriqués, directs, blocs et await ; drop/consommateur Void | P — cas exécutés |
| SL1–SL2 | Le perdant détruit uniquement le contenu encore à sa charge | Select avec replace et try_push, capacité disponible/atteinte ; destruction unique et réemploi | P — chemins exercés |
| AS12–AS13, contrats | La provenance reste distincte par bras | Ancienne allocation conservée après destruction du pool entrant ; source courte refusée | P — deux pools, relais testés |
| Régressions | Syntaxe commune, contrats et nettoyage existants préservés dans les cas couverts | 131 méthodes ; suites tableaux/Select et modèles existants | P — audit indépendant distinct, pas de preuve générale |
| Suite reproduite | Retour async de Result<A<Int>,A<Int>> via await | open-async-handle-exchange-result.crust/.log, refus aux deux entrées | Captures et retours de ces enveloppes non raccordés |

Lot précédent : [insertion faillible de handles dans async](cycles/ASYNC_HANDLE_VECTOR_TRY_PUSH_CYCLE.md).
Sept méthodes ciblées : quatorze exécutions natives et neuf invalides aux deux
entrées. O0/UBSan : 6,981 s, code 0. Régression O2/UBSan : 72 méthodes en
75,217 s, code 0, dont trois méthodes synchrones historiques. La limite de
région de 1 MiB est réellement atteinte dans les cas d’échec.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE4, U1 | Ok(()) ne possède rien ; Err conserve l’entrant | Succès, limite atteinte, match direct/nommé et continuation ; résultats inutilisés refusés | P — Vector<A<Int>>, enveloppe locale à async |
| Transferts et nettoyage | Une seule destination nettoie l’allocation | Déplacement, annotation, drop direct/nommé ; réemploi et destruction unique | P — chemins testés |
| B1–B5, AS8–AS12 | Le receveur reste réservé ; la source doit survivre à l’insertion | Prêt terminé admis, prêt actif et source courte refusés ; entrant obtenu via await | P — réservation du vecteur entier |
| SL1–SL2 | La destruction d’un perdant respecte le statut de l’insertion | Select suspendu après try_push, vecteur vide ou plein | P — contenu inséré conservé, rejet nettoyé |
| Régressions | Les opérations locales déjà raccordées restent exercées | 72 méthodes et modèle existant de poll/nettoyage de Select | P — audit approfondi distinct, pas de preuve générale |
| Suite reproduite | Passage du résultat de replace par helper synchrone appelé depuis async | open-async-handle-exchange-call.crust/.log refusé aux deux entrées | Signature non raccordée ; enveloppe de try_push également à compléter |

Lot précédent : [remplacement de handles de vecteur dans async](cycles/ASYNC_HANDLE_VECTOR_REPLACE_CYCLE.md).
Sept méthodes ciblées : quatorze exécutions natives et sept invalides aux deux
entrées. O0/UBSan : 5,466 s avant ajout du drop direct. Régression finale O2/UBSan :
72 méthodes en 77,334 s, code 0, incluant les deux cas de drop direct et trois
méthodes synchrones historiques. Aucune modification normative.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | Le résultat possède l’ancien ou l’entrant refusé | Succès/indice invalide ; résultat nommé, déplacé et détruit directement ; destruction unique et réemploi | P — Vector<A<Int>>, résultat local à async |
| B1–B5, ordre d’évaluation | Le receveur est réservé pendant les arguments | Dernier usage avant/après, receveur partagé refusé ; indice puis entrant produits par await | P — cas ciblés |
| AS8–AS12, provenance | Les sources de chaque charge restent connues | Ancien retourné via tâche/fabrique après destruction du vecteur et du pool entrant ; pool trop court refusé | P — union conservative si position inconnue |
| SL1–SL2, nettoyage | Le perdant détruit l’ancien, le vecteur conserve le nouveau | Select suspendu après replace, destruction unique et réemploi | P — chemin déterministe exercé |
| Régressions liées | Les opérations et contrats déjà raccordés restent exercés | 72 méthodes ; modèle existant de poll/nettoyage de Select | P — pas de preuve générale, audit approfondi différé |
| Suite reproduite | try_push de handle dans async | open-async-handle-vector-try-push.crust/.log refusé aux deux entrées | Non raccordé, comme les signatures async de l’enveloppe de replace |

Lot précédent : [Option propriétaire dans l’enveloppe d’un handle](cycles/ASYNC_OPTION_JOIN_CYCLE.md).
Sept méthodes ciblées : dix-neuf exécutions natives et cinq invalides aux deux
entrées. O0/UBSan : 8,415 s, code 0. Régression O2/UBSan : 83 méthodes en
152,442 s, code 0, avant déplacement de la définition C. Validation finale :
onze méthodes ciblées/runtime en 11,856 s, code 0. Les échecs intermédiaires
et les corrections des snippets de test sont consignés dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, AS10–AS12, RT6 | Le résultat distingue présence, absence et échec de lancement | Some/None/Err via join et await de handle, destruction unique et réemploi | P — Option<A<Int>> |
| Contrats, transferts, U1 | La provenance et le nettoyage suivent l’enveloppe | Handle public, helpers, capture, bloc/if/break, usages manquants refusés | P — pas d’enveloppe supplémentaire autour de ce Result |
| Durées de vie | Le pool de l’élément survit au résultat ; le vecteur peut disparaître | Programme accepté avec pool extérieur, refus avec pool intérieur | P — cas ciblés |
| AS8–AS10, SL1–SL2 | L’argument préparé reste nettoyable pendant une suspension | Relais puis await ; branche perdante de Select, destruction unique | P — chemin exercé |
| Runtime autonome | Le runtime générique ne dépend pas d’un type d’enveloppe généré | Quatre régressions de réveil/modèle après correction | P — modèle existant rejoué, audit approfondi différé |
| Suite reproduite | Remplacement d’un handle de vecteur dans async | open-async-handle-vector-replace.crust/.log, refus aux deux entrées | array_handle_exchange non raccordé |

Lot précédent : [captures et retours async d'options propriétaires](cycles/ASYNC_HANDLE_OPTION_RESULTS_CYCLE.md).
Huit méthodes ciblées : treize exécutions natives et sept programmes invalides
aux deux entrées. O0/UBSan : 4,734 s, code 0. Régression O2/UBSan : 74 méthodes
en 113,097 s, code 0. Périmètre : Option<A<Int>> via await d'une instance inactive
et capture explicite ; l'enveloppe de spawn/join reste ouverte.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1, AS2–AS5 | L'option transfère son éventuel contenu à la capture ou au receveur | Some/None, flèches, fabriques, relais et helper synchrone | P — Option<A<Int>>, usage explicite requis |
| B1–B5, AS12–AS13 | Les prêts terminent avec l'attente, les sources du résultat subsistent | Lecture du vecteur après await admise, pendant la capture refusée ; pool court refusé | P — le cas de capture courte est refusé dès l'insertion extérieure |
| AS8–AS10, AS14, SL1–SL2 | Destruction unique du contenu non restitué | Inactif, échec de lancement et enfant suspendu d'un perdant Select ; réemploi du pool | P — chemins ciblés, aucune nouvelle campagne adversariale |
| Régressions liées | Contrats, résultats propriétaires et nettoyage conservés | 74 méthodes ; modèle existant de poll/nettoyage rejoué | P — pas de preuve générale |
| Suite | Result<Option<A<Int>>,runtime::Error> après lancement | Diagnostic explicite pour join/await de handle | Non raccordé ; handles publics correspondants également ouverts |

Lot précédent : [options propriétaires dans les appels synchrones depuis async](cycles/ASYNC_HANDLE_OPTION_CALLS_CYCLE.md).
Sept méthodes ciblées : quinze exécutions natives, sept invalides aux deux
entrées. Régression O2 : 61 méthodes en 99,319 s avant les corrections finales.
Validation finale O2 : sept méthodes ciblées et quatre synchrones, onze méthodes
en 10,245 s, code 0. Les erreurs intermédiaires et leurs limites sont consignées.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | Le contrat transporte le contenu optionnel et son nettoyage | Some/None, relais, Void, drop direct ; absence de transfert ou d'usage refusée | P — helpers synchrones, Option<A<Int>> |
| Ordre d'évaluation, AS8–AS12 | L'argument préparé reste protégé pendant l'await suivant | Quatre formes d'argument, séquence 4/7/8 | P — cas ciblés |
| SL1–SL2, destruction | Le perdant nettoie l'argument préparé avant l'appel | Select, helper non appelé, destruction unique et réemploi | P — chemin exercé |
| Provenance, durées de vie | Le résultat dépend du pool de l'élément, pas du vecteur | Retour après destruction du vecteur ; source trop courte refusée | P — union des sources possibles |
| None et contrats | Aucun champ d'allocation n'est lu si le contenu est absent | Plantage préexistant reproduit, cas minimal conservé, quatre tests synchrones réussis après correction | P — pas de preuve générale |
| Suite reproduite | Option retournée par une tâche puis reçue via await | open-async-handle-option-result.crust/.log refusé aux deux entrées | Signature async non raccordée |

Lot précédent : [pop de handles dans les états async](cycles/ASYNC_HANDLE_VECTOR_POP_CYCLE.md).
Ciblé O0/UBSan terminé : huit méthodes en 7,658 s, dix-sept exécutions
natives et six invalides aux deux entrées. Cinq régressions synchrones réussies
en 6,473 s. Régression async O2/UBSan : 91 méthodes en 153,696 s, code 0.
Modèles de listes et de poll/nettoyage existants rejoués ; pas de preuve générale.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE1–VE3 | Le dernier handle est extrait sans changer sa cible ni son pool | Some/None, deux pools, nettoyage unique et réemploi | P — A<Int> |
| U1, transferts | L'option possède son contenu et exige une consommation explicite | Move, match, drop direct/nommé, annotation ; usage absent et seconde consommation refusés | P — options locales aux états async |
| B1–B5 | Pop attend la fin du prêt et exige un receveur mutable | Dernier usage avant/après et vecteur partagé | P — réservation entière du vecteur |
| AS8–AS12, blocs | L'option survit à yield et se transfère dans un receveur | Bloc, if, break ; retour de l'élément via fabrique | P — signatures d'option non raccordées |
| SL1–SL2, nettoyage | Un perdant suspendu détruit son Some une fois | Select après extraction, longueur zéro et réemploi du pool | P — chemin déterministe exercé |
| Suite reproduite | Helper synchrone retournant l'option à une tâche | open-async-handle-option-call.crust/.log refusé aux deux entrées | Signature non prise en charge |

Lot précédent : [extraction de handles de vecteurs dans async](cycles/ASYNC_HANDLE_VECTOR_REMOVE_CYCLE.md).
Huit méthodes : treize exécutions natives (un arrêt contrôlé hors bornes),
sept invalides aux deux entrées. Ciblé O0/UBSan : 5,864 s ; régression
O2/UBSan : 77 méthodes en 60,691 s ; cinq méthodes synchrones en 6,278 s,
toutes terminées avec le code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE3, U1 | Extraction explicite, pool et responsabilité de nettoyage conservés | Liaison, retour direct, helper, drop direct ; flèche absente refusée | P — A<Int> |
| VE1–VE3, nettoyage | Ordre des cases restantes et destruction unique | Extraction du milieu, deux pools, nettoyage du vecteur et réemploi | P — cas finis |
| B1–B5, évaluation | Extraction protégée jusqu'au dernier usage des prêts | Prêt terminé admis ; extraction/remplacement pendant prêt refusés ; indice suspendu et bornes | P — réservation entière du vecteur |
| AS8–AS12, contrats | Résultat indépendant du porteur, durable dans son pool | Join, fabrique, relais await ; sortie du pool du vecteur admise, pool de cible court refusé | P — union conservative des pools |
| Régressions | Conservation des cas précédents | 77 méthodes async/contrats/résultats ; cinq méthodes synchrones ; modèle existant Int/u8 rejoué | P — pas de preuve générale, audit approfondi différé |
| Reste | Autres opérations propriétaires de vecteurs dans async | Pop, replace, try_push, constructions locales et retours de vecteurs | Non clôturé par ce lot |

Lot précédent : [insertion de handles dans un vecteur depuis async](cycles/ASYNC_HANDLE_VECTOR_PUSH_CYCLE.md).
Neuf méthodes : treize exécutions natives, douze invalides aux deux entrées.
O0/UBSan : 4,878 s ; régression O2/UBSan : 68 méthodes en 55,594 s et
cinq méthodes synchrones en 5,353 s, codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1–H2, VE1–VE2 | La case reçoit explicitement le handle et son nettoyage | Variables et allocations neuves, deux pools, vecteur possédé ; refus des types et modes incompatibles | P — push de A<Int> |
| B1–B5 | Le prêt protège le transfert et le receveur jusqu'au dernier usage | Emprunt avant transfert, usage après transfert et prêt au-delà du push refusés | P — scénarios ciblés |
| AS8–AS12, contrats | Les nouvelles sources restent connues après attente | Fabrique, relais et helper synchrone ; pool court refusé ; réemploi après join | P — union des sources possibles, précision des positions limitée |
| SL1–SL2, provenance | Les insertions avant suspension d'un perdant restent observables | Select direct et via fabrique ; défaut d'alias reproduit puis corrigé | P — deux exécutions et deux refus, pas preuve générale |
| Nettoyage, RT6 | Une seule destruction, aucune insertion si le corps ne démarre pas | Inactif, EAGAIN et terminaison ; pools de capacité un réemployés | P — treize exécutions |
| Écart suivant | Extraire explicitement un handle depuis async | open-async-handle-vector-remove.crust/.log, refus aux deux entrées | Non implémenté dans ce cas |

Lot précédent : [retours async d'emprunts de cibles de vecteurs](cycles/ASYNC_HANDLE_VECTOR_BORROW_RETURNS_CYCLE.md).
Six méthodes : sept exécutions natives (une terminaison contrôlée), dix invalides
aux deux entrées. O0/UBSan : 3,248 s ; régression O2/UBSan : 49 méthodes,
41,046 s, codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS11–AS12, H2 | Le résultat emprunté conserve un porteur extérieur durable | Retours ref/mut, relais attendu, refus depuis vecteur possédé par la tâche | P — Vector<A<Int>>, réservation entière |
| B1–B5, dernière utilisation | Le porteur redevient accessible après le dernier usage | Mutations après usage admises ; accès, drop et remplacement prématurés refusés | P — cas ciblés après join et await |
| VE4, ordre des effets | Écriture sync du contenu : cible avant RHS, sans invalidation pendant RHS | RHS partagé admis, RHS mutable refusé, hors bornes avant effet | P — pas remplacement de handle |
| Nettoyage et réemploi | Destruction unique des cibles, slots réutilisables | Résultats 7/11/13/14 selon scénario et réemploi avec 8 ; 49 méthodes de régression | P — pas preuve générale |
| Écart suivant | Insérer un handle dans un vecteur depuis async | open-async-handle-vector-push.crust/.log refusé aux deux entrées | Non implémenté dans ce cas |

Lot précédent : [emprunts nommés des cibles de vecteurs dans async](cycles/ASYNC_HANDLE_VECTOR_BORROWS_CYCLE.md).
Cinq méthodes : six exécutions natives (une terminaison contrôlée), sept invalides
aux deux entrées. O0/UBSan : 2,726 s ; régression O2/UBSan : 41 méthodes,
35,948 s, codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H2, VE1/VE4, AS9 | Référence vers le contenu stable, contrôlée avant usage | Lecture/mutation après yield, indice suspendu et hors bornes | P — cibles Int |
| B1–B5, dernière utilisation | Parent réservé pendant le prêt et ses descendants | Mutation après dernier usage admise ; accès prématurés refusés ; enfant attendu | P — réservation du vecteur entier |
| Nettoyage, transfert | Le prêt ne survit pas à la destruction de son porteur propriétaire | Drop après usage, refus avant usage, destruction unique et réemploi | P — six exécutions natives |
| Écart suivant | Retourner le prêt dans le résultat async | open-async-handle-vector-borrow-return.crust/.log, refus aux deux entrées | Non implémenté dans ce cas |

Lot précédent : [accès au contenu des handles depuis async](cycles/ASYNC_HANDLE_VECTOR_ACCESS_CYCLE.md).
Quatre méthodes : quatre exécutions natives dont une terminaison contrôlée,
trois invalides aux deux entrées. O0/UBSan : 1,708 s, code 0. Régression
O2/UBSan : 50 méthodes en 48,365 s ; trois méthodes Foundation O2/UBSan
en 2,469 s, codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| H1/VE1, B1–B5 | Lire/modifier *v[i] agit sur l'Int sans copier ni remplacer A<Int> | Lecture après yield, écriture puis lecture après join ; capture partagée et accès concurrent refusés | P — contenus Int, pas prêts d'éléments |
| VE4, ordre des effets | Vérifier l'indice avant d'évaluer la valeur entrante | Indice/RHS attendus ; hors bornes sans impression du marqueur RHS | P — quatre exécutions ciblées |
| Capture et nettoyage | Réemploi après terminaison et destruction unique | Régression de 50 méthodes et trois cas synchrones | P — pas preuve générale |
| Prochain écart | Conserver &*values[0] pendant une suspension | open-async-owned-vector-borrow.crust/.log refusé aux deux entrées | Non implémenté ; prochaine fonctionnalité |

Lot précédent : [captures async de vecteurs de handles](cycles/ASYNC_HANDLE_VECTOR_CAPTURES_CYCLE.md).
Cinq méthodes : cinq exécutions natives et six invalides aux deux entrées.
O0/UBSan : 1,787 s, code 0. Régression O2/UBSan : 57 méthodes, 73,554 s, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| VE1–VE2/H1, AS2/AS8–AS12 | Un Vector<A<Int>> capturé conserve ses éléments et leurs pools | Ref, mut, owned, enfant attendu, yield, lecture de longueur | P — capture/longueur ; API d'éléments non raccordée |
| B1–B5, typage | Aucun accès incompatible ni confusion Vector<Int>/Vector<A<Int>> | Six programmes invalides aux deux entrées | P — cas ciblés |
| Nettoyage, pools, RT6 | Transfert du vecteur nettoyé une fois sur chaque issue exercée | Terminaison, tâche inactive, EAGAIN ; pool de capacité un réemployé | P — cinq exécutions et 57 méthodes de régression |
| Prochain écart | Lecture d'un élément propriétaire dans l'état | open-async-owned-vector-read.crust/.log refusé aux deux entrées | Non implémenté ; aucune nouvelle restriction normative |

Lot précédent : [graphes récursifs neufs dans les fabriques](cycles/FRESH_RECURSIVE_FACTORIES_CYCLE.md).
Trois méthodes : cinq programmes natifs et sept invalides aux deux entrées.
O0/UBSan : 2,554 s, code 0. Régression finale O2/UBSan : 83 méthodes,
119,547 s, code 0 (première passe avant jonction finale : 82 méthodes réussies).

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, contrats, T1/T6 | Une construction neuve conserve tous ses pools et champs profonds à travers la fabrique | Deux liens A<Node>, source terminale distincte, appel direct/relayé et depuis async | P — chemins concrets, métadonnées de variantes publiées |
| B1–B5, ST13 | Les références du graphe restent protégées après attente | Mutation de cible prématurée refusée ; lecture après yield et nettoyage puis écriture admis | P — champs &Int testés ; pas preuve générale |
| Contrats par chemin | Une branche absente est distincte d'une variante inconnue | End direct ou deux Link, deux exécutions et refus ; union des formes par chemin | P — jonctions opaques potentiellement conservatrices |
| Pools, nettoyage | Les sources durent et les slots sont restitués | Drop du pool avant attente refusé ; destruction unique et réemploi ; 83 méthodes passent | P — audit indépendant reporté |
| AS2/VE1–VE2, prochain écart | Une tâche devrait pouvoir emprunter un Vector<A<Int>> | open-async-owned-vector-capture.crust/.log : refus aux deux entrées, lecture de longueur seulement | Non implémenté sur ce cas ; prochaine fonctionnalité |

Lot précédent : [remplacement de lien récursif complet](cycles/RECURSIVE_LINK_REPLACEMENT_CYCLE.md).
Deux méthodes : deux programmes natifs et quatre invalides aux deux entrées.
O0/UBSan : 0,916 s, code 0. Régression : 49 méthodes, 30,432 s, code 0,
UBSan fatal (O2 sur les harnais async, sans O2 explicite sur les anciens harnais sync).

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| A<T>, remplacement, nettoyage | Le sous-arbre ancien est détruit une fois ; nouveau pool durable | Champ A<Node> remplacé par helper sync et depuis état suspendu ; pool enfant refusé | P — graphe fini alternant struct/enum |
| B1/B2, match | La projection du champ reste typée et contrôlée | Lecture &*link.node après remplacement ; mutation via porteur partagé et champ absent refusés | P — filtre corrigé, contrôle général conservé |
| Pools, AS8–AS12 | Les slots anciens et nouveaux restent réutilisables | Réemploi avant et après nettoyage de la racine ; 49 méthodes passent | P — graphes neufs dans les fabriques encore à vérifier |

Vérification ciblée précédente : [remplacement propriétaire profond](cycles/RECURSIVE_OWNED_REPLACEMENT_CYCLE.md).
Une méthode : deux programmes natifs et deux invalides aux deux entrées,
réussis à O0 et O2 avec UBSan fatal. Le compilateur prenait déjà ce cas en charge ;
seuls les tests et la documentation sont ajoutés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Remplacement, T1/T6, durée de vie des pools | La nouvelle source survit au porteur ; ancienne allocation détruite une fois | A<Int> derrière deux liens A<Node>, helper sync, état async suspendu, pool enfant refusé | P — champ terminal ; pas remplacement du lien A<Node> complet |
| Nettoyage, réemploi | Les anciens et nouveaux slots sont rendus à leurs pools | Pools de capacité un, valeurs 9/11/12, destruction unique | P — deux programmes à O0/O2 ; aucun changement du compilateur |

Lot précédent : [retours mutables récursifs](cycles/RECURSIVE_MUTABLE_RESULTS_CYCLE.md).
Deux méthodes : trois exécutions natives et sept invalides aux deux entrées.
O0/UBSan : 1,206 s, code 0. Régression : 97 méthodes en 42,486 s, code 0,
UBSan fatal (O2 sur les harnais async, sans O2 explicite sur les anciens harnais sync).

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST11–ST12, B1–B5 | Le retour mutable conserve la cible et les capacités de ses porteurs | Deux liens A<Node>, retour &mut Int, drop du porteur/cible et écriture directe refusés avant usage | P — trois programmes valides, sept invalides |
| Contrats, AS8–AS12 | Le chemin reste valide après relais et suspension | Paramètre renuméroté au relais, yield après appel du helper, écriture puis nettoyage | P — graphes ciblés, remplacement de liens encore ouvert |
| Retours partagés et mutables | La distinction ST13/capacité exclusive demeure | 97 méthodes de régression passent | P — pas de preuve globale ni nouvel audit indépendant |

Lot précédent : [retours partagés récursifs](cycles/RECURSIVE_BORROW_RESULTS_CYCLE.md).
Deux méthodes ciblées : deux exécutions natives et quatre invalides aux deux
entrées. O0/UBSan : 1,077 s, code 0. Régression : 81 méthodes, 48,141 s,
code 0 ; harnais async O2/UBSan, harnais synchrones historiques C sans sanitizer.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST13, B1/B5 | Le retour partagé conserve la cible extérieure sans réserver artificiellement le porteur | Retour après deux liens A<Node>, drop du porteur puis lecture ; mutation et drop de cible précoces refusés | P — &Int partagé, deux chemins d'appel |
| AS8–AS12, contrats | Le prêt issu du helper survit à yield | Lecture après suspension, accès à la cible autorisé après dernier usage | P — retour synchrone appelé depuis une tâche ; pas tous retours async |
| Match et contrats | Les projections propriétaires et les résultats de matchs imbriqués conservent leur chemin | 81 méthodes passent ; retours mutables existants dans la régression | P — retours mutables profonds et remplacement de liens encore ouverts |

Lot précédent : [projections empruntées récursives](cycles/RECURSIVE_BORROW_PROJECTIONS_CYCLE.md).
Quatre méthodes ciblées : six exécutions natives et six programmes invalides
aux deux entrées. O0 : 4,615 s, code 0. Régression O2/UBSan : 86 méthodes en
70,513 s, code 0 ; cinq cas synchrones O2/UBSan passent en 3,417 s.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST14, emprunts | Les champs empruntés restent accessibles derrière des liens récursifs | Lecture &Int et écriture via &mut Int, helpers sync et états async | P — projection symbolique ; retours d’emprunts profonds non déclarés complets |
| AS8–AS12, T1/T6 | Déplacer un descendant conserve toutes ses références concrètes | Drop prématuré maintenant refusé sans usage parasite ultérieur ; fixture conservée | P — perte de prêts corrigée, six programmes invalides aux deux entrées |
| Références nominales | Une cible intérieure conserve son descripteur et son offset | Champ avant la cible valant 99, lecture attendue 7, mutation bloquée puis autorisée | P — six exécutions ciblées, pas toutes les formes |
| Contrats et nettoyage | Pas de régression sur graphes et références existants | 86 méthodes async/contrats et cinq cas synchrones passent | P — pas de preuve générale ; remplacement de liens récursifs encore ouvert |

Lot précédent : [helpers d’attente sur handles récursifs](cycles/RECURSIVE_JOIN_HELPERS_CYCLE.md).
Quatre méthodes ciblées : cinq exécutions natives et trois invalides aux deux
entrées. O0 : 2,230 s, code 0. Régression O2/UBSan : 112 méthodes en 120,958 s,
code 0 ; trois cas synchrones O2/UBSan supplémentaires passent en 2,209 s.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, contrats publics | Une attente déléguée restitue le graphe fini et ses variantes | Handle<A<Node>>, Result retourné, deux helpers, variante terminale | P — cas auparavant refusé corrigé, autres projections ouvertes |
| B1–B5, AS12 | Le descendant conserve sa référence après retour du helper | Mutation prématurée refusée ; cible libérable après nettoyage | P — référence partagée ciblée, pas toutes les formes récursives |
| Nettoyage, RT5–RT6 | Destruction unique des descendants, y compris LaunchFailed | Traces et réemploi en succès/échec injecté | P — cinq exécutions natives ciblées |
| Brouillon 04, attente non bloquante | Le helper ne permet pas de cacher un join dans l’async | Refus aux deux entrées | Exécuté sur le cas ; aucune modification normative |
| Modèle de contrat | Les continuations récursives symboliques ne sont pas des feuilles concrètes | 112 méthodes et trois cas synchrones passent | P — représentation finie, pas preuve de toutes les opérations |

Lot précédent : [fabriques de tâches récursives](cycles/RECURSIVE_TASK_FACTORIES_CYCLE.md).
Trois méthodes ciblées : cinq exécutions natives et cinq programmes invalides
aux deux entrées. O0 : 2,282 s, code 0. La régression O2/UBSan termine
99 méthodes en 77,697 s, code 0. Un helper de join sur Handle<A<Node>> reste
refusé et son programme minimal est conservé dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, contrats | Les graphes concrets et variantes traversent les fabriques et relais | Deux appels successifs, restauration après join, destruction unique et réemploi | P — chemins hérités des paramètres ; résultat récursif neuf opaque non couvert |
| B1–B5, AS12 | Les références de descendants restent réservées après attente | Mutation refusée après join, création directe et fabrique avant relais | P — conservation parfois conservatrice |
| Sources de stockage, nettoyage | Chaque pool capturé survit même sans résultat propriétaire | Consommateur Int, pool terminal protégé, slot réemployé après attente | P — cinq exécutions ciblées, 99 méthodes de régression |
| Contrat d’attente public | Un helper devrait pouvoir attendre un handle récursif | open-recursive-join-helper.crust, trace du déroulement de type | Non implémenté sur ce cas ; prochaine correction |

Lot précédent : [graphes propriétaires récursifs async](cycles/ASYNC_RECURSIVE_OWNED_CYCLE.md).
Cinq méthodes ciblées, sept exécutions natives et quatre invalides aux deux
entrées ; O0 passe. Régression O2/UBSan : 120 méthodes, 98,500 s, code 0.
Une erreur historique d’extraction A<T> est reproduite sur le snapshot puis
corrigée : 22 méthodes passent en 13,706 s ; le module de stockage complété
passe ensuite 11 méthodes en 7,354 s. Les sélections se recouvrent.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, champs A<T> | Graphes finis de type récursif sans déroulement infini ; variantes et sources par chemin | Capture, join, helper sync, nettoyage inactive/échec, réemploi | P — graphes concrets énumérés, fabriques opaques non généralisées |
| Emprunts, contrats publics | Le résultat vivant conserve les références de ses descendants | Mutation prématurée refusée après join, handle inféré et annoté | P — défaut de perte de dépendance corrigé ; héritage potentiellement conservateur |
| Stockage T / A<T> | Le champ possédé a son pool indépendamment du porteur | Extraction depuis enum local/en pool ; annotation locale incompatible refusée | P — erreur historique corrigée, suites ciblées terminées |
| Nettoyage et contrat de source | Descendants avant porteurs, destruction unique | Traces feuille/milieu/racine et réemploi, régression de 120 méthodes | P — pas de preuve générale, audit indépendant reporté |

Lot précédent : [handles publics d’enums locaux](cycles/PUBLIC_LOCAL_ENUMS_CYCLE.md).
Cinq méthodes ciblées passent à O0 : sept exécutions natives et cinq programmes
invalides refusés aux deux entrées. La régression liée passe 67 méthodes en
40,076 s, code 0 ; cas ciblés et modules async à O2/UBSan, deux modules historiques
avec leur harnais sans optimisation explicite ni sanitizer.
Le test conditionnel synchrone du lot précédent utilise désormais `bool` ;
les appels booléens étaient déjà implémentés, aucun nouveau type ou alias ajouté.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS10–AS12, API des handles | Le contrat public conserve T local et sa variante | Fabrique, deux routines distinctes, join, await, échec de soumission | P — Handle<A<T>> incompatible refusé, cas ciblés |
| Emprunts et sources | Le résultat retient ses cibles et les pools de ses descendants | Champs partagé, mutable et A<Int>, destruction unique, réemploi ; drop prématuré refusé | P — sept exécutions, cinq invalides aux deux entrées |
| F2, lecture dans match | print(*référence) suit les contrôles ordinaires | Filtre syntaxique corrigé, régressions de matchs partagés et mutables | P — 67 méthodes, pas de preuve générale |

Lot précédent : [enums sur data stack implicite](cycles/LOCAL_ENUMS_CYCLE.md).
Huit méthodes ciblées : dix programmes admis exécutés et trois invalides refusés
aux deux entrées. O0 passe en 4,281 s. Après correction d’une régression de
portée de symbole C, 124 méthodes passent à O2/UBSan en 103,565 s ; 23 tests
historiques des enums en pool passent aussi avec leur harnais sans optimisation
explicite ni sanitizer. Tous les processus finaux sont terminés avec code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Data stack implicite, transferts enfant → parent | La source de stockage est distincte du layout et du bras actif | Littéraux sync/async, if, bloc, break, retours conditionnels | P — layouts représentés ; réservation synchrone au maximum des bras |
| AS8–AS12, résultats locaux | Métadonnées durables, résultat placé chez le receveur avant libération de l’état | Helpers synchrones, await, join et transfert à un enfant | P — dix programmes ciblés, pas toutes les compositions |
| Nettoyage, champs A<T>, emprunts | Destruction unique du descendant ; aucune promotion de cible empruntée | Match consommant, réemploi du slot, cible trop courte et drop prématuré refusés | P — trois invalides aux deux entrées |
| Pools d’enums et placement existant | Les bras en pool et structures locales gardent leur comportement | 124 méthodes O2/UBSan et 23 historiques ; régression C corrigée | P — pas de preuve générale ni audit indépendant |

Lot précédent : [remplacements de descendants à références nominales](cycles/ASYNC_OWNED_NOMINAL_WRITES_CYCLE.md).
Six méthodes ciblées : neuf exécutions natives (dont un échec de soumission
injecté), douze programmes invalides refusés aux deux entrées. O0 passe en
4,079 s ; la régression O2/UBSan passe 101 méthodes en 82,937 s, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Remplacement, AS12/AS16 | La nouvelle cible reste liée au descendant après await/join | Écriture directe et auxiliaire, cible intérieure, lancement échoué | P — graphes représentés, pas de cycles de références nouveaux |
| SL1, contrats par chemin | Les anciennes et nouvelles cibles possibles restent suivies | Select suspendu et deux branches conditionnelles ; conflits refusés | P — neuf exécutions ciblées, pas tous les entrelacements |
| Durée de vie, exclusivité | L’emprunt ne survit pas à une cible locale et bloque ses mutations | Scope enfant trop court et écritures prématurées refusés | P — douze invalides aux deux entrées, audit indépendant différé |
| Contrats et nettoyage | Compatibilité des graphes possédés existants | 101 méthodes : descendants, vues, enums, appels synchrones, handles publics | P — pas de preuve générale |

Lot précédent : [références nominales des bras d’enums async](cycles/ASYNC_ENUM_NOMINAL_CYCLE.md).
Cinq méthodes ciblées couvrent six programmes admis et six invalides refusés
aux deux entrées. Le passage ciblé O0 passe en 2,695 s ; la régression O2/UBSan
passe 104 méthodes en 91,860 s, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, ST13–ST14 | Les projections gardent la cible intérieure après suspension et destruction du porteur | Deux variantes, retour partagé, consommant, réemploi du slot | P — descripteurs de structures représentées, graphes récursifs ouverts |
| ST10–ST12, dernier usage | Le réemprunt mutable réserve cible et capacité | Helper synchrone, conflit entre réemprunts et accès appelant refusés | P — cas ciblés, pas d’audit adversarial nouveau |
| Construction, transfert, nettoyage | Les pools restent valides et chaque porteur est détruit une fois | Construction async, enfant attendu, comptage de destruction et réemploi | P — 104 méthodes de régression, pas de preuve générale |

Lot précédent : [retours async directs de références nominales](cycles/ASYNC_NOMINAL_RESULTS_CYCLE.md).
Onze méthodes ciblées couvrent douze programmes admis et huit invalides refusés
aux deux entrées. Les dix premières méthodes passent à O0, la régression passe
116 méthodes à O2/UBSan, puis les onze méthodes et les handles publics passent
42 méthodes après le dernier raccordement : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS8–AS12, ST7–ST14 | Le résultat emprunté conserve sa cible après libération de l’état | Await, join, sous-structure, référence stockée, relais, deux branches et Select | P — douze programmes ciblés, graphes récursifs non couverts |
| Exclusivité, durée de vie | La réservation suit le résultat jusqu’au dernier usage | Conflits de mutation et retours locaux refusés aux deux entrées | P — cas énumérés ; pas de nouvelle campagne adversariale |
| Contrats publics, ABI | Le handle conserve le type nominal et sa mutabilité | Paramètre Handle<&Point>, annotation incompatible refusée, 42 méthodes de régression | P — interface publique du scheduler toujours ouverte |
| Nettoyage et slots | Restitution avant libération de l’état, slots réutilisables | Régression de 116 méthodes incluant cinq tests autonomes du runtime | P — exécutions UBSan, pas de preuve générale |

Lot précédent : [références typées stockées en async](cycles/ASYNC_STORED_VIEWS_CYCLE.md).
Huit nouvelles méthodes couvrent neuf programmes admis et neuf invalides
refusés aux deux entrées. Le passage ciblé et historique passe 17 méthodes
à O0 ; la régression finale passe 118 méthodes à O2/UBSan : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS2–AS4, ST7–ST12 | Descripteur intérieur et capacités conservés dans les références stockées | Capture partagée/mutable, yield, tâche enfant, chaîne et helpers synchrones | P — fermeture de layouts représentés, pas de cycles de types généraux |
| AS12, ST10–ST14 | Un remplacement conserve chaque cible possible, y compris si le lancement échoue | Remplacement direct/par contrat ; anciens et nouveaux référents protégés après join | P — parcours exécutés et refus associés |
| AS11–AS12, ST13–ST18 | Le retour propriétaire ne libère pas l'emprunt de sa cible intérieure | Capture/transfert/retour de View, drop du porteur, mutation de cible refusée ; copie et construction locales | P — réservation canonique corrigée ; retours async directs de &T nominaux encore ouverts |
| Nettoyage, ABI, contrats | Régressions sync/async conservées | 118 méthodes, y compris remplacements, références Int, structures mixtes et copies | P — pas de preuve générale ni campagne adversariale nouvelle |

Lot précédent : [captures async de sous-structures](cycles/ASYNC_INLINE_VIEWS_CYCLE.md).
Neuf méthodes ciblées : neuf programmes admis et huit invalides refusés aux deux
entrées. Sept puis huit méthodes passent à O0. La régression générale passe
127 méthodes à O2 ; après raccordement des exigences de copie, 58 méthodes
passent, puis 32 après la correction finale des fabriques : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS2–AS4, ST7–ST12 | La capture garde l'adresse intérieure, la racine et l'exclusivité | Yield, worker, tâche enfant, helper synchrone, accès concurrents refusés, destruction inactive | P — champs Int, références Int et descendants propriétaires représentés |
| AS11–AS12, ST13–ST14 | Un champ emprunté retourné reste lié à la racine après join | Retour &mut Int et drop prématuré de la racine refusé | P — résultats de références nominales async encore partiels |
| ST17–ST18, P8 | Copier une vue n'utilise pas un pool d'un autre type | Copie locale, destination explicite, refus Pool<Pair> pour Point, relais et fabrique | P — exigences inférées ; références nominales stockées encore refusées en async |
| Contrats de remplacement et ABI | Les ponts gardent champs propriétaires, variantes et provenances | Régressions sur remplacements async, Select, copies et méthodes | P — 127 puis 58 et 32 méthodes, pas de preuve générale |

Lot précédent : [résultats mêlant références entières et intérieures](cycles/MIXED_INLINE_RESULTS_CYCLE.md).
Sept méthodes ciblées passent à O0 : douze programmes admis et onze programmes
invalides refusés aux deux entrées. La régression O2 passe 98 méthodes, puis
le passage final après simplification des retours passe 13 méthodes : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST14, contrats par branche | Même type/mode, toutes les cibles possibles restent protégées | Retours conditionnels, relais, if, match, break, branche locale trop courte refusée | P — parcours synchrones testés |
| Adresses stables, ST17–ST18 | Le descripteur commun ne déplace pas la cible | Adresses comparées dans les deux branches, copie et stockage du résultat | P — douze exécutions ciblées |
| Dernier usage, exclusivité | Le résultat mutable reste dérivé de ses cibles et capacités | Stockage dans Writer, réemprunt et appel, destruction/écriture concurrente refusées | P — async des vues encore ouvert |

Lot précédent : [références intérieures stockées](cycles/STORED_INLINE_VIEWS_CYCLE.md).
Neuf méthodes ciblées passent à O0 : huit programmes admis, cinq invalides refusés
aux deux entrées, plus un refus explicite de capture async encore non raccordée.
La régression O2 passe 90 méthodes puis 12 historiques ; après la normalisation
finale des cycles, 33 méthodes liées passent à O2 : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST13–ST14 | Le descripteur stocké conserve l'adresse intérieure et la racine | Construction, copie locale/pool, retours, réemploi du slot porteur, drop de racine refusé | P — parcours synchrones testés |
| ST10–ST12 | Réemprunt mutable dérivé et remplacement libérant l'ancienne cible | Retour mutable, mutation, accès concurrents refusés, référence entière ↔ vue | P — résultats mixtes et async encore ouverts |
| Cycles, nettoyage, ST17 | Pas de destruction de la cible par le porteur, pas d'auto-référence à la racine | Match emprunté/consommant, copie, cycle via sous-structure refusé | P — ABI nominale élargie, pas de preuve générale |

Lot précédent : [champs propriétaires dans les vues](cycles/INLINE_OWNED_VIEWS_CYCLE.md).
Sept méthodes ciblées passent à O0/UBSan : huit programmes admis exécutés et
sept programmes invalides refusés aux deux entrées. La régression liée passe
84 méthodes à O2, plus six méthodes historiques de remplacement : codes 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7–ST8, ST15 | La vue emprunte ses handles, la racine conserve leur nettoyage | Lecture, mutation, retour d'emprunt, destruction unique et réemploi des slots | P — chemins synchrones testés |
| Remplacement, pools, contrats | Effet sur le champ réel ; ancien slot libéré, nouveau pool assez durable | Remplacement direct, relais, vue retournée, argument intérieur et pool court refusé | P — A<Int> et descendant A<Leaf> exercés |
| ST13, ST17 | Cible partagée retenue après destruction des porteurs ; pas de copie des handles | Extraction de &Int, cible détruite trop tôt et copie de la vue refusées | P — stockage et async des vues encore ouverts |

Lot précédent : [vues contenant des références typées](cycles/INLINE_TYPED_VIEWS_CYCLE.md).
Six nouvelles méthodes : six programmes admis exécutés et dix programmes invalides
refusés aux deux entrées. Le passage ciblé final comprend neuf méthodes ; les
régressions liées passent 40 puis 19 méthodes à O2/UBSan, codes de sortie 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST10–ST12 | Effets sur la racine canonique, cible et capacité mutable conservées | Réaffectation typée via vue, retour de la nouvelle cible, accès concurrents refusés | P — appels synchrones et chemins testés |
| ST13, ST17–ST18 | Référence/copie partagée détachée du porteur, cible toujours protégée | Relais, copie, drop des porteurs intermédiaires, drop de la cible refusé | P — références vers structures typées |
| Contrats, provenance transitive | Une dépendance à travers une référence n'est pas une écriture dans son objet cible | Trois régressions historiques corrigées ; remplacements propriétaires sync/async conservés | P — reset testé seulement en compatibilité historique |

Lot précédent : [vues contenant des références Int](cycles/INLINE_REFERENCE_VIEWS_CYCLE.md).
Neuf nouveaux cas fonctionnels, plus les six tests de copies de vues, passent
à O0/UBSan : seize programmes admis exécutés et seize programmes invalides
refusés aux deux entrées. La régression finale passe 82 méthodes à O2, puis
six méthodes de copies async : code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST7, ST10–ST12 | Le chemin et les cibles du sous-arbre restent rattachés à la racine | Réaffectations directes/par contrats, réemprunts mutables, accès incompatibles refusés | P — champs terminaux Int/&Int/&mut Int |
| ST13, ST17–ST18 | Une référence ou copie partagée conserve sa cible sans retenir artificiellement le porteur | Retours par relais et copies, drop du porteur accepté, drop de la cible refusé | P — parcours synchrones testés |
| Brouillon 07, sources de stockage | La copie intérieure sans pool explicite exige une racine locale | Exigence inférée et propagée, retour de copie et pool incompatible | P — champs A<T>, stockage et async des vues non raccordés |

Lot précédent : [copies explicites de vues de sous-structures](cycles/INLINE_VIEW_COPY_CYCLE.md).
Six méthodes ciblées passent à O0/UBSan : sept programmes admis exécutés et
quatre programmes invalides refusés aux deux entrées. La régression liée passe
35 méthodes à O2, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST17–ST18, brouillon 07 | Copie indépendante dans la source correcte, original conservé | Copie locale, pool explicite, source détruite, réemploi du slot | P — vues à champs terminaux Int |
| Transfert enfant → parent | Le stockage de la copie survit au producteur | Blocs, break explicite, fonctions et relais | P — chemins source testés |
| Dernier usage, pools typés | Lecture de copie autorisée et destination assez durable | Réemprunt actif, pool incompatible et pool trop court refusés | P — captures async et champs références non raccordés |

Lot précédent : [emprunts source de sous-structures à champs Int](cycles/INLINE_STRUCTURE_BORROWS_CYCLE.md).
Sept méthodes ciblées passent à O0/UBSan : neuf programmes admis exécutés et
dix programmes invalides refusés aux deux entrées. La régression liée passe
61 méthodes à O2, puis cinq méthodes historiques de chemins de champs : code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST7, dernier usage | Le préfixe réservé protège son sous-arbre, pas ses frères | Appels sur deux frères, accès incompatibles refusés, réemprunt Int | P — vues à champs terminaux Int |
| ST8, enfant → parent | Le retour conserve le chemin et la racine vivante | Relais, sortie de bloc, drop et racine locale refusés | P — appels synchrones et chemins testés |
| Adresses stables, nettoyage | Vue sans allocation indépendante, résultat conservant son adresse | Cas enregistré, résultats if/loop et trace de destruction | P — copies, champs références et async encore à raccorder |

Lot précédent : [représentation des vues de sous-structures](cycles/STRUCTURE_VIEW_RUNTIME_CYCLE.md).
Cinq méthodes ciblées passent à O0/UBSan et 34 méthodes liées à O2, code 0.
Les tests ciblés vérifient les métadonnées et six exécutions C de l'ABI interne.
À la clôture de ce lot interne, `open-inline-structure-borrow.crust` était
encore refusé aux deux entrées ; le lot source ci-dessus traite ensuite ce cas.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST1, ST7, adresses stables | Une vue désigne les octets de la racine, sans allocation distincte | Métadonnées, sonde C de retour et réemploi, voisin inchangé | P — représentation interne seulement |
| AS10–AS13, MT | Le descriptif peut être conservé dans un état puis transmis entre threads | Suspension/reprise sur pthread, attente avant drop de la racine | P — ABI manuelle ; capture source non raccordée |
| ST6–ST8, emprunts et contrats | Préfixe réservé, durée de la racine et retours vérifiés statiquement | Cas source enregistré, actuellement refusé comme non pris en charge | N — raccordement requis avant validation source |

Dernier lot fonctionnel : [constructeurs inline imbriqués](cycles/INLINE_STRUCTURE_CONSTRUCTION_CYCLE.md).
Huit méthodes ciblées passent à O0/UBSan : neuf exécutions natives et huit
programmes invalides aux deux entrées. La régression finale passe 62 méthodes
à O2, code 0. Trois fixtures historiques migrées vers A<T> passent également
sur le compilateur du snapshot initial ; les échecs précédents sont conservés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST1, ST3, ST4 | Un seul slot, défauts récursifs, type nominal et ordre écrit | Littéraux locaux, pools injectés/aliasés, chemins nommés, doublons et types refusés | P — littéraux contenus ; valeurs nommées/calculées hors lot |
| ST6–ST8, ST17–ST18 | Chemins distincts et cibles partagées préservés | Retours, copies, emprunts disjoints, drop prématuré refusé | P — champs Int et références représentables |
| AS10–AS14, nettoyage | Champs préparés nettoyés avant publication si suspension interrompue | Await dans un champ, retour local, champ A<Int>, sonde de destruction suspendue | P — chemins finis, aucune preuve générale |

Lot précédent : [copies directes de structures async](cycles/ASYNC_DIRECT_COPY_CYCLE.md).
Six méthodes ciblées passent à O0/UBSan sur la version finale : six exécutions
natives et quatre programmes invalides aux deux entrées. Une première régression
passe 69 méthodes à O2 ; après ajustement des références locales, 20 méthodes
directement liées passent à O2 sur la version finale. Tous les processus : code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST17, emprunts | Copie structurelle explicite, cibles partagées conservées | &Int copié, drop prématuré et copies A<T>/&mut refusés | P — champs représentables testés |
| ST18, V1, placement parent | Nouvelle valeur locale ou slot du pool choisi, sans promotion de source | Copies locales/capturées, pool explicite, alias et transferts successifs | P — structures inline imbriquées hors lot |
| AS10–AS13, nettoyage | Résultat créé chez le receveur, adresse stable après libération de l'état | Sonde C, identité, pool d'états vide, destruction et réemploi | P — chemins finis, sans preuve générale |

Lot précédent : [destination extérieure des résultats de Select](cycles/SELECT_RESULT_PLACEMENT_CYCLE.md).
Cinq méthodes ciblées passent à O0 : six exécutions natives et deux programmes
invalides aux deux entrées, soit quatre contrôles de refus. La régression
finale passe 94 méthodes à O2/UBSan, code 0, incluant les méthodes ciblées.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Placement parent, AS10–AS13, SL1 | Les constructeurs de branches utilisent la destination du résultat reçu | Fabriques, branches directes, bloc intermédiaire et retour de tâche | P — Point local testé ; formes générales à compléter |
| Adresses stables, nettoyage | Le gagnant garde son adresse ; les autres valeurs et les états sont nettoyés | Sondes C à suspension et terminaison, compteurs de stockage et pools vides | P — chemins finis, aucune preuve générale |
| Durée des pools et emprunts | Le placement ne promeut ni pool explicite ni cible empruntée | Pool court et drop avant dernière lecture refusés | P — cas ciblés et régressions liées |

Lot précédent : [restitution après remplacement propriétaire](cycles/RETURNED_OWNED_REPLACEMENT_CYCLE.md).
Six méthodes ciblées passent à O0 : six exécutions natives et quatre programmes
invalides aux deux entrées, soit huit contrôles de refus. Après correction de
deux régressions sur les descendants imbriqués, les 90 méthodes liées passent
sur la version finale à O2/UBSan, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Remplacement, transferts, adresses stables | Le résultat restitue la racine et son graphe final | Même adresse avant/après appel et join, ancien et nouveau champs détruits une fois | P — racines et champs testés |
| AS10–AS13, durées de sources | Le résultat conserve le nouveau pool et les champs inchangés | Relais await, pool court refusé en sync/async, voisin inchangé, modèle de profondeurs | P — graphes généraux et branches à compléter |
| Emprunts, nettoyage | Le descendant remplacé conserve ses cibles ; l'échec de lancement ne remplace rien | Descendant &Int, drop prématuré refusé, LaunchFailed, réemploi de slots | P — cibles et chemins testés, sans preuve générale |

Lot précédent : [remplacements propriétaires des fabriques](cycles/FACTORY_OWNED_EFFECTS_CYCLE.md).
Six méthodes ciblées passent à O0 : huit exécutions natives et trois programmes
invalides aux deux entrées, soit six contrôles de refus. La régression finale
passe 117 méthodes à O2/UBSan, incluant les six méthodes ciblées, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS3–AS5, AS16, contrats | Un remplacement différé conserve son porteur et son pool à chaque phase | Pools intermédiaire/final distincts ; relais et permutation sans corps synchrones | P — graphes représentés, A<Int> et descendant contenant &Int testés |
| AS14, SL1, D1 | Création inactive sans écriture ; perdante conservée puis nettoyée | Drop inactif, await, join, LaunchFailed et Select, réemploi des slots | P — pas de preuve générale sur toutes les alternatives |
| Durées des pools, emprunts | Le champ reçu et ses cibles survivent aux derniers accès | Pool final court refusé en await et join, cible empruntée protégée | P — préfixes concurrents des handles hors lot |

Lot précédent : [préfixes de suspension des fabriques synchrones](cycles/FACTORY_SUSPENSION_CONTRACTS_CYCLE.md).
Cinq méthodes passent à O0 : neuf exécutions natives et six programmes invalides
aux deux entrées, soit douze contrôles de refus. La régression finale passe
97 méthodes à O2/UBSan, incluant les cinq méthodes ciblées, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS3–AS5, contrats | Une fabrique conserve les effets de suspension de la tâche transférée | Relais, permutation, transfert et contrôle de contrats sans corps synchrones | P — champs empruntés Int représentés |
| AS14, AS16 | Création inactive, suspension et terminaison ont des effets distincts | Drop inactif sans écriture ; restauration seulement à la terminaison | P — remplacements possédés aux suspensions des fabriques non raccordés |
| SL1, emprunts, branches | Une perdante conserve ses écritures suspendues et leurs dépendances | Select direct ou via relais, choix entre deux captures, drop prématuré refusé | P — unions conservatrices, préfixes concurrents des handles hors lot |

Lot précédent : [retours mutables depuis un descendant possédé](cycles/ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE.md).
Cinq méthodes ciblées passent à O0 : six exécutions natives et neuf programmes
invalides aux deux entrées, soit dix-huit contrôles de refus. Régression finale :
110 méthodes à O2/UBSan, incluant les cinq méthodes ciblées, code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Retours enfant → parent, emprunts mutables | Le descendant emprunté conserve une provenance durable et sa capacité | Retour synchrone puis async, exemple auparavant refusé maintenant exécuté | P — &mut Int et graphes représentés |
| Dernière utilisation, AS16 | Le porteur et la cible restent réservés jusqu'au dernier usage | Lectures, écriture de cible, drop et remplacement refusés avant ; accès admis après | P — check et génération concordent sur les cas testés |
| Remplacement, SL1 | Les effets visent le nouveau descendant et le résultat traverse les attentes | Join, LaunchFailed, relais await, Select ; contrôle d'exclusivité inchangé | P — autres formes de graphes et types à compléter |

Lot précédent : [retours d'emprunts après remplacement d'un descendant](cycles/ASYNC_REPLACED_BORROW_RESULTS_CYCLE.md).
Six méthodes ciblées passent à O0 et O2 : dix exécutions natives et dix programmes
invalides aux deux entrées par passage. Régression liée : 125 méthodes à O2/UBSan,
sur la même implémentation, avant l'ajout des deux derniers tests ciblés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Retours d'emprunts, AS16 | Le résultat garde la cible lue au moment de sa création | Ancien snapshot et nouvelle lecture distingués par les contrats et l'exécution | P — références partagées Int |
| Transferts, dernière utilisation, D1 | Le porteur peut être détruit ; la cible externe du résultat doit survivre | Drops admis/refusés après join et relais await ; échec de lancement | P — descendants suivis et cibles extérieures |
| Branches, SL1 | Les alternatives restent protégées et le résultat survit au nettoyage de Select | Deux branches exécutées, résultat gagnant après drop de Select et du porteur | P — pas de généralisation à tous les résultats mutables |

Lot précédent : [mécanisme interne des mutex](cycles/MUTEX_RUNTIME_CYCLE.md).
Quatre méthodes ciblées exécutent six sondes C à O0 ; la régression liée passe
26 méthodes à O2. Clang/pthread/UBSan, processus terminés avec code 0. Les
constructeurs et le contrôle statique des gardes ne sont pas raccordés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| MT9 sync | Garde liée au thread ; acquisition suivante observe les écritures | Deux threads, drop du mauvais thread refusé, destruction unique | P — runtime ; interdiction de suspension non implémentée |
| MT9 async, RT2 | Garde conservée à travers yield et libérable après migration | Premier poll dans main, libération sur un autre thread, réveil du waiter Pending | P — mécanisme C ; typage et prêts dérivés à raccorder |
| SL1, MT9 | Drop perdant retire attente/réservation ou détruit la garde | Trois états de perdante dans Select, réservation transmise au suivant | P — callbacks de sondes manuels ; génération source mutex absente |

Lot précédent : [descendants remplacés contenant des emprunts](cycles/ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
Huit méthodes ciblées passent à O0 : 12 exécutions natives, 13 programmes
invalides et 26 contrôles de refus. La régression O2/UBSan passe 127 méthodes
avant le dernier ajustement conditionnel, puis 19 méthodes liées passent sur
l'état final à O2/UBSan. Tous ces processus sont terminés avec code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS16, SL1, contrats | Le descendant remplacé conserve ses cibles selon l'état réellement atteint | Await, join, LaunchFailed, Select, écritures avant/après yield | P — champs &Int et &mut Int |
| Emprunts, durées de vie, transferts | Le champ reçu protège sa cible jusqu'au dernier usage | Drop et mutation prématurés refusés, cible de scope court refusée | P — cibles Int suivies |
| Branches, remplacement, D1 | L'absence de remplacement conserve l'ancienne cible ; les slots restent réutilisables | Deux branches exécutées, alternatives protégées, nettoyage et réemploi | P — unions conservatrices ; audit approfondi différé |

Lot précédent : [remplacement de champs possédés en async](cycles/ASYNC_OWNED_FIELD_WRITES_CYCLE.md).
Sept méthodes ciblées passent à O0 et O2 : huit exécutions natives et un
programme refusé aux deux entrées par passage. La régression liée passe
109 méthodes à O2 avec UBSan avant le dernier ajustement de scope, ensuite
couvert par les deux passages ciblés. Aucune nouvelle campagne adversariale.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS16, contrats de champs | Les sources aux suspensions sont distinctes de celles à la terminaison | Contrats, await, join, Select perdant, descendant d'enum | P — descendants remplacés sans emprunts contenus |
| Transferts, pools, D1 | Le receveur conserve la source et détruit son ancien champ une fois | Affectation directe, auxiliaire, réemploi des slots, LaunchFailed | P — unions de sources parfois conservatrices |
| Durées de vie enfant → parent | Le pool survit à la dernière allocation reçue | Pool intermédiaire court accepté, pool final court refusé, receveur transféré vers l'enfant | P — cas énumérés ; audit indépendant différé |

Lot précédent : [lectures de champs dans un match partagé](cycles/SHARED_MATCH_FIELD_READS_CYCLE.md).
Trois méthodes ciblées passent à O0, avec quatre exécutions natives et un
programme refusé aux deux entrées. La régression liée passe 64 méthodes à O2
avec UBSan, code 0. Le cas enregistré `open-shared-enum-descendant-read.crust`
est maintenant exécuté. Aucune campagne adversariale supplémentaire.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| F2, lectures et copies Int | Le champ est lu via sa projection partagée ; le résultat copié ne retient pas son porteur | Lecture directe, variable, calcul et destruction avant usage du résultat | P — expressions Int testées |
| Typage, emprunts | Le filtre de syntaxe ne remplace pas le contrôle du champ et de sa cible | Champ inconnu refusé, régressions de champs et matchs mutables | P — pas de généralisation à toutes les expressions |

Lot précédent : [références des descendants d'enums aux suspensions](cycles/ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE.md).
Cinq méthodes ciblées passent à O0 : trois contrôles d'analyse, deux exécutions
natives et un programme refusé aux deux entrées. La régression directement liée
passe 127 méthodes à O2 avec UBSan, code 0. Aucune campagne adversariale ou de
mutations supplémentaire n'est effectuée, selon la consigne utilisateur.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS16, contrats de champs | L'état suspendu conserve les écritures déjà effectuées | Cibles distinctes aux suspensions et à la terminaison, union de plusieurs yield | P — références Int dans un graphe de stockage inchangé |
| AS8–AS15, SL1 | Les effets atteignent le descendant de l'appelant après await ou Select | Deux exécutions natives, relais de contrat, drop de la nouvelle cible refusé | P — formes testées ; remplacement d'allocation distinct |
| Contrats, identité locale | L'emprunt mutable d'un enum conserve le porteur et son graphe | Application des contrats aux enums locaux, régressions de descendants et alias | P — pas d'audit indépendant ni de couverture des graphes récursifs |

Lot précédent : [match consommant d'enums en async](cycles/ASYNC_CONSUMING_ENUM_MATCH_CYCLE.md).
Dix méthodes ciblées passent à O0 : 10 exécutions natives, 10 programmes invalides
et 20 contrôles de refus. La régression directement liée passe 117 méthodes à O2
avec UBSan, code 0. Selon la dernière consigne utilisateur, ce lot implémente et
teste les cas déjà énumérés ; il n'ajoute pas de campagne adversariale ni de
mutations. L'audit indépendant n'est pas réputé effectué.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Transferts, F2/U1, D1 | Les champs possédés sont reçus, le porteur détruit une fois avant le corps | Usage explicite de chaque motif, destruction porteur/champ, adresse conservée, réemploi | P — enums et champs représentés |
| Pools, contrats de provenance | Le résultat extrait conserve ses propres sources | Retour du descendant, graphe imbriqué, porteur en pool court admis et cible en pool court refusée | P — producteurs sans métadonnées détaillées restent conservateurs |
| B1–B5, AS8–AS15 | Les emprunts extraits conservent leurs cibles et capacités | Retours partagés/mutables, référence stockée dans un champ, drop prématuré refusé | P — formes testées |
| D1, SL1, sorties de boucle | Suspension et sortie nettoient les champs transférés sans double destruction | Yield, perdante Select, break, continue et return | P — tests fonctionnels et régressions, sans audit indépendant |

Lot précédent : [match d'enums par emprunt en async](cycles/ASYNC_ENUM_MATCH_CYCLE.md).
Dix-sept méthodes ciblées passent à O0/O2 : 20 exécutions natives, 16 programmes
invalides et 32 contrôles de refus. Les six mutations sont détectées. La
régression synchrone passe 125 méthodes et la régression async finale passe
173 méthodes, à O2 avec UBSan. Tous les processus finaux sont terminés avec
code 0. Le rapport distingue les défauts corrigés, une assertion historique
actualisée sur preuve du snapshot, et les compositions encore ouvertes.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| P9, AS8/AS9, branches | Bon bras, projections stables et résultat correctement reçu | Trois variantes réordonnées, yield, alias, Int/Bool, branches imbriquées et allocations retournées | P — match par emprunt, pas consommant |
| B1–B5, ST13, AS12, retours de match | Le porteur est réservé pendant le bras ; les prêts sortants gardent leurs cibles et capacités | Réemprunts, enfant async, retour mutable chez l'appelant, résultat partagé détaché et parent exclusif | P — projections et contrats représentés |
| D1, SL1, RT6 | Sorties et perdantes nettoient sans libérer une cible encore requise | Return/break/continue, échec de lancement, réemploi, perdante mutable et usages avant/après drop | P — graphes finis testés |
| AS16, SL1 | Un contrat incomplet n'est pas publié comme absence d'effets | Résumé de terminaison précis, suspension du graphe possédé explicitement incomplète, mutation détectée | P — composition valide restant à implémenter |

Lot précédent : [enums alloués en async](cycles/ASYNC_OWNED_ENUMS_CYCLE.md).
Douze méthodes ciblées passent à O0/O2 : 24 exécutions natives, 14 programmes
invalides et 28 contrôles de refus. Les cinq mutations finales sont détectées,
dont une lecture de bras inactif initialement survivante ; le rapport décrit
le renforcement de l'oracle et ses limites. Les régressions finales passent
200 méthodes async et 235 méthodes synchrones à O2 avec UBSan. Tous les
processus finaux sont terminés avec code 0. Les échecs intermédiaires et
corrections sont conservés dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS2, AS8–AS10, transferts, pools d'enums | Capture et retour conservent allocation, bras et source | Await, join, relais, pools par bras et tailles différentes, réemploi | P — agrégats finis représentables ; match direct async encore ouvert |
| AS11–AS15, contrats, emprunts | Les prêts et sources nécessaires survivent aux retours | Handles publics, contrat opaque sans corps, drop et pool courts refusés, choix de bras | P — variants racines ; précision des descendants à éprouver |
| SL1, D1, RT6 | Sélection et échec de lancement nettoient chaque capture une fois | Modèle indépendant de quatre ordres de suspension, champs possédés, réemploi | P — pas tous les graphes ni toutes les enveloppes |
| Layout actif et frontière C | Un auxiliaire ne lit pas les champs d'un bras inactif | Trois bras avec offsets distincts, lectures C instrumentées, mutation détectée | P — oracle dépend des métadonnées du layout ; UBSan seul insuffisant |

Lot précédent : [type et stockage du résultat de Select](cycles/SELECT_RESULT_STORAGE_CYCLE.md).
Dix méthodes ciblées passent à O0/O2 : 17 exécutions natives, 18 programmes
invalides et 36 contrôles de refus. Les cinq mutations sont détectées par
assertions. La régression élargie passe 167 méthodes à O2 avec UBSan.
Tous les processus finaux sont terminés avec code 0 ; le rapport conserve
les échecs intermédiaires et leurs causes.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, V1, T1/T6 | Le type du résultat distingue T local de A<T>, même sans poll | Contre-exemple accepté auparavant, refus aux deux étapes ; huit combinaisons stockage/suspension | P — classes de stockage des structures représentées |
| Branches, boucles, contrats | If, break et relais de tâches ne masquent pas le stockage du résultat | Programmes admis exécutés et mélanges refusés ; quatre mutations des comparaisons détectées | P — compositions finies testées |
| D1, AS8–AS15, RT6, L1/L2/L6 | Les origines concernent le résultat ; les prêts et nettoyages subsistent | Captures non retournées, descendants en pool, résultat partagé, drop prématuré, échec de lancement et réemploi | P — pas de généralisation à tous les agrégats |

Le type et les signatures publiques de `runtime::set_scheduler` restent
explicitement à arbitrer, selon la réponse de l'utilisateur. Ses responsabilités
et garanties validées ne sont pas reportées. Voir `design-buffer/points-ouverts.md`.
`validation/open-async-owned-enum.crust` est désormais accepté et exécuté dans
ce lot. Ses limites restantes sont détaillées dans le rapport associé.
`validation/open-async-enum-match.crust` est maintenant exécuté dans le lot
suivant. `validation/open-async-consuming-enum-match.crust`, initialement refusé,
est maintenant exécuté par le lot de match consommant ci-dessus.

Lot précédent : [choix entre descendants empruntés](cycles/NESTED_FIELD_CHOICES_CYCLE.md).
Onze méthodes ciblées passent à O0/O2 : 17 exécutions natives, 15 programmes
invalides et 30 contrôles de refus. Le modèle indépendant couvre 12 combinaisons
(7 admises exécutées, 5 refusées aux deux étapes). Les cinq mutations finales
sont détectées ; une survivante au premier test ciblé est détectée par le cas
objet entier/descendant dans la suite complète. Les régressions passent
178 méthodes de contrats/async et 90 méthodes de tableaux à O2 avec UBSan.
Tous les processus finaux sont terminés avec code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| Branches, ST6–ST15, B1–B5 | Une écriture par alias choisi ne remplace pas certainement tous les candidats | Effets par champ inspectés, deux choix observés en C, branches identiques, modèle de cibles | P — unions conservatrices, toutes les corrélations non représentées |
| Contrats, D1 | L'appelant opaque conserve les cibles anciennes possibles des descendants | Contre-exemple verify/compile divergent corrigé ; refus aux deux étapes ; mutation détectée | P — chemins et types finis couverts |
| Réemprunts mutables, T1/T6, AS8–AS15 | Capacités et cibles traversent projections, boucles et transferts | Cible mutable, projection supplémentaire, objet entier/descendant, destruction anticipée refusée | P — signatures générales encore à auditer |

`open-nested-field-choice.crust` est désormais accepté et exécuté.
Le contrat public précis du scheduler reste à clarifier ; la question a été
adressée à l'utilisateur sans suspendre les travaux indépendants.

Lot précédent : [contrats empruntant le parent d'un descendant](cycles/NESTED_FIELD_WRAPPERS_CYCLE.md).
Dix méthodes passent à O0/O2 : 17 exécutions natives, 16 programmes invalides
et 32 contrôles de refus. Les cinq mutations sont détectées, dont la mutation
des champs enfant survivante au cycle précédent : un nouveau scénario lit
le descendant modifié avant de mettre à jour son frère. La régression passe
153 méthodes à O2 avec UBSan ; les trois derniers tests passent dans les
baselines finaux. Tous les processus sont terminés avec code 0.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, contrats, B1–B5 | Le contrat appliqué au parent actualise le descendant exact | Contrat inspecté, appelants sync/async, relais successifs, alias, source externe | P — choix conditionnel entre descendants encore non raccordé |
| D1, affectations conditionnelles | L'absence de remplacement préserve l'ancienne cible possible | Contre-exemple accepté pendant le raccordement corrigé ; modèle indépendant à 12 combinaisons | P — modèle fini, aucune preuve générale |
| AS8–AS15, RT6 | Transfert vers une tâche conserve les nouvelles cibles jusqu'au nettoyage | Drop anticipé refusé, cible mutable, échec injecté, réemploi de slot | P — familles de signatures testées |

`open-nested-field-wrapper.crust` et sa variante synchrone sont exécutés.
`open-nested-field-choice.crust` était alors un programme valide refusé,
traité par le lot ci-dessus.

Lot précédent : [remplacement des références dans les descendants](cycles/NESTED_FIELD_REPLACEMENT_CYCLE.md).
Onze méthodes passent à O0/O2 : 18 exécutions natives, 18 programmes invalides
et 36 contrôles de refus. Le modèle indépendant couvre 12 combinaisons
(7 admises exécutées, 5 refusées aux deux étapes). Trois mutations sur quatre
sont détectées ; la quatrième survit aussi à toute la suite ciblée, sans
équivalence générale revendiquée. Les régressions passent 144 méthodes async
et 46 synchrones à O2 avec UBSan. Tous les processus sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1–B5, D1 | Remplacer un champ ne modifie que ses dépendances ; la nouvelle cible reste valide | Champs partagés/mutables, deux frères homonymes, deux niveaux, conditionnel, modèle de cibles | P — graphes finis ; mutation des métadonnées enfant survivante |
| T1/T6, AS2/AS8–AS15 | Transfert/retour du graphe conserve les cibles actualisées | Projection directe/alias, modification dans la tâche, retour propriétaire, drop prématuré refusé | P — relais empruntant le parent entier encore non raccordé |
| RT6, contrats | Échec de lancement détruit une fois les captures, même après remplacement | Échec injecté, traces Inner/Outer, fabrique sans écritures différées | P — aucune généralisation des préfixes suspendus de fabriques |

`open-nested-field-replacement.crust` est accepté et exécuté après correction
de sa notation d'emprunt explicite. `open-nested-field-wrapper.crust` demeure
un cas alors valide refusé, désormais traité par le lot ci-dessus.

Lot précédent : [handles lancés en arguments depuis async](cycles/ASYNC_EXECUTION_ARGUMENTS_CYCLE.md).
Dix-neuf méthodes passent à O0/O2 : 26 exécutions natives, 25 programmes
invalides et 50 contrôles de refus. Six mutations ciblées sont détectées ;
les sept historiques le sont aussi, dont une par plantage du compilateur.
Trois modèles finis passent, avec 53 cas admis exécutés et 19 cas refusés.
La régression élargie passe 214 méthodes à O2 avec UBSan ; les deux derniers
tests ajoutés passent séparément dans les baselines finaux O0/O2. Tous les
processus du lot sont terminés.
Les essais intermédiaires et leurs limites sont conservés dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, contrats, AS9/AS12, MT5/MT6 | Un relais de handle conserve captures, stockage et dépendances du résultat | Relais publics/concrets, références, structures T/A<T>, tableaux, str, pools courts, réemploi | P — signatures représentées ; pas de généralisation à toutes les formes |
| RT5–RT7, SL2, ordre des arguments | Pas de relancement, join caché ou abandon du handle préparé | Compteur de soumissions, échec de lancement, bloc natif, return/break/continue, perdante Select refusée aux deux étapes | P — capture d'un handle lancé dans une tâche inactive reste séparée |
| B1–B5, D1, effets de champs, RT6 | Après attente, les cibles possibles comprennent les écritures réussies et l'état initial de LaunchFailed | Contre-exemple drop accepté corrigé ; champs locaux et injectés ; deux mutations distinctes détectées | P — auxiliaires attendant sans écritures propres et à résultat scalaire ; autres compositions conservativement incomplètes |

`open-public-structure-async-relay.crust` est désormais accepté et exécuté.
Le remplacement de dépendances d'un champ descendant était encore ouvert ;
le lot ci-dessus traite les projections directes et leurs alias.

Lot précédent : [handles publics de structures](cycles/PUBLIC_STRUCTURE_HANDLES_CYCLE.md).
Quatorze méthodes ciblées passent à O0/O2 : 24 exécutions natives, 26 programmes
invalides et 52 contrôles de refus, plus le contrôle d'un appelant privé des
corps. Six des sept nouvelles mutations et cinq des six historiques sont
détectées ; les deux survivantes sont documentées, sans équivalence générale
revendiquée. La régression finale passe 157 méthodes à O2 avec UBSan.
Tous les processus cités sont terminés ; les deux campagnes de mutations
conservent leur code 1 pour les survivantes, sans masquer cette limite.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| V1, T1/T6, contrats, AS9/AS12, MT5/MT6 | Handle<T> ne convertit pas le stockage en A<T>, ni l'inverse | Annotations sync/async, obligations de fabriques, deux types de routines, branches mixtes refusées avec/sans annotation | P — structures représentées ; signatures générales encore ouvertes |
| B1–B5, D1, MT5/MT6 | Le type public conserve les cibles et capacités des champs retournés | Emprunts partagés/mutables, ancêtre mutable, descendants possédés, relais et appelant sans aucun corps | P — graphes finis testés ; mutation de liste des prêts survivante, protection des champs toujours active dans ces cas |
| A2, L1/L2/L6, AS8/AS12, RT6/RT7 | Le pool survit au résultat et le nettoyage restitue chaque slot une fois | Pool court refusé, capacité un réemployée, échecs de lancement à deux niveaux, traces de destruction | P — scénarios natifs O0/O2 UBSan, pas de preuve générale ni nouveau résultat ASan/TSan |

`open-public-local-structure-handle.crust` est désormais accepté et exécuté.
`open-public-structure-async-relay.crust` était alors valide mais non raccordé,
et est traité par le lot ci-dessus. Le remplacement de dépendances
d'un champ descendant reste également ouvert. SL2 demeure appliquée.

Lot précédent : [stockage des résultats de tâches dans les contrats](cycles/TASK_RESULT_STORAGE_CYCLE.md).
Onze méthodes ciblées passent à O0/O2 : 14 exécutions natives, 18 programmes
invalides et 36 contrôles de refus. La régression O2 passe 128 méthodes avec
UBSan ; sept fautes ciblées et six historiques sont détectées. Les processus
cités sont terminés. Les types publics de structures restent à raccorder.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| V1, T1/T6, contrats, AS9/AS12, MT5/MT6 | Le résultat conserve son stockage T local ou A<T> à travers une tâche/handle opaque | Matrice local/pool, trois relais, deux sources conditionnelles, Execution concret ; contrats inspectés, faux appels refusés | P — tâches et handles concrets ; Handle<Structure> reste ouvert |
| V1, A2, L1/L2/L6, AS12 | Les sources de racine, descendants et captures non retournées restent distinctes | Copie depuis un emprunt ; racine locale/descendant en pool ; réemploi de capacité un ; mutations des projections | P — graphes finis pris en charge, pas de généralisation aux types récursifs |
| B1–B5, D1, MT6 | Une annotation de résultat ne libère pas ses emprunts | Retour d'une structure contenant une référence, relais puis drop prématuré refusé | P — interactions finies, pas de preuve générale |
| RT7, SL2 | Aucun join caché ni abandon d'un handle lancé dans une perdante | Join caché refusé depuis async ; contre-exemple SL2 refusé aux deux étapes | P — capture d'un handle lancé dans une tâche inactive reste à arbitrer |

Lot précédent : [arguments de tâches depuis un état async](cycles/SYNC_TASK_ARGUMENTS_CYCLE.md).
Dix-huit méthodes ciblées passent à O0/O2 (dix-sept dans la régression O2,
puis le complément break/continue séparé). Le comptage O0 relève 24 exécutions
natives, 26 programmes invalides et 52 contrôles de refus. Sept mutations
ciblées sont détectées, dont une par plantage du compilateur sur un programme
valide ; huit mutations historiques sont détectées. La première régression
passe 140 méthodes et la finale 132, sélections recouvrantes. Tous les processus
finaux sont terminés ; chronologie et limites dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, B1–B5, D1, AS2/AS9/AS12 | Le relais d'une tâche conserve captures, sources et prêts du résultat | Emprunts partagés/mutables, tableaux, graphes imbriqués, résultats locaux/en pool, choix conditionnels, handles publics/concrets | P — signatures représentées ; Handle<structure locale> reste ouvert |
| AS8/AS13/AS14, L1/L2/L6, SL1 | Les tâches préparées sont nettoyées avant leurs sources, sans lancer leur corps | Suspension, retour anticipé, break/continue, Select perdant, capacité un réemployée, ordre inverse ; mutations de fuite détectées | P — constructions/routines couvertes ; préfixes de fabriques générales encore conservatifs |
| Contrats, SL1 | Un relais pur conserve les effets suspendus, sans masquer une alternative fraîche | task_forward_only inféré sur tous les chemins ; tâche nouvelle dans une branche, mutation du fait inféré | P — analyse statique par contrats, pas de preuve générale de convergence |
| SL2, RT7, MT3/MT4 | Une perdante ne peut abandonner un handle lancé encore à attendre | Décision explicite de l'utilisateur intégrée ; open-select-launched-handle.crust refusé aux deux étapes avec diagnostic SL2 | P — restriction conservative ; capture de handle dans une tâche inactive toujours à arbitrer |

Le relais `validation/open-async-task-relay-argument.crust` est désormais
exécutable. `validation/open-public-local-structure-handle.crust` et
`validation/open-nested-field-replacement.crust` restent ouverts. SL2 clôt
l'arbitrage de Select ; les mentions d'arbitrage en attente dans les anciens
rapports sont historiques.

Lot précédent : [références détachées des descendants possédés](cycles/NESTED_DETACHED_REFERENCES_CYCLE.md).
Quatorze méthodes ciblées passent à O0/O2. Le comptage final O0 relève
22 exécutions natives, 27 programmes invalides et 54 contrôles de refus.
Sept fautes ciblées et six historiques sont détectées. Le lot a été rouvert
après découverte d'une double projection perdant le prêt dans un appelant async ;
ce défaut est corrigé et son contre-exemple conservé. Les premières régressions
passent 110 méthodes async/ponts et 56 méthodes de champs synchrones à O2 avec
UBSan. Les 110 méthodes async/ponts passent à nouveau après le dernier correctif.
Les sélections se recouvrent ; les comptes ne s'additionnent pas comme des tests
uniques. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST13/ST14/ST15, H1/H2, B1–B5 | Une référence partagée retournée conserve la cible, sans retenir le porteur possédé | Direct/fabrique, chaîne de helpers, handle public, waiter, fin des pools intermédiaires ; refus du stockage propre et de la copie mutable | P — graphes finis à feuilles &Int ; pas de généralisation aux graphes cycliques |
| D1, AS2/AS9/AS12, T1/T6 | Le prêt retourné subsiste après await/join ; l'union des chemins possibles est protégée | Modèle cible × instant × chemin ; deux acceptations invalides après await corrigées ; retours conditionnels et mutation de perte du prêt | P — provenance par chemin, couverture finie ; mise à jour des champs descendants ouverte |
| AS8/AS13/AS14, RT6/RT8, SL1, L1/L2/L6 | Nettoyage unique des porteurs et réemploi sans invalider la cible | Inactive, échecs de lancement, thread natif, Select perdant, boucle avec slot réutilisé ; sept mutations et UBSan O0/O2 | P — handles lancés soumis aux arbitrages existants ; pas de preuve ASan/TSan ou générale |

Le cas `validation/open-nested-detached-reference.crust` est corrigé dans ce
périmètre. `validation/open-async-task-relay-argument.crust` et
`validation/open-nested-field-replacement.crust` restent ouverts. Les anciens
constats ci-dessous sont historiques et sont remplacés par ce lot lorsqu'ils
concernent le détachement partagé des descendants.

Lot précédent : [emprunts dans les descendants possédés](cycles/NESTED_OWNED_BORROWS_CYCLE.md).
Quinze méthodes ciblées passent à O0/O2 (treize à O2 puis deux ajouts séparés).
Le comptage final O0 relève 23 exécutions natives, 32 programmes invalides et
64 contrôles de refus. Six fautes ciblées et neuf fautes du lot précédent sont
détectées. Les régressions async passent 98 méthodes avant la restitution
complète des champs, puis 96 sur le code final ; sélections recouvrantes.
Un complément synchrone de 87 méthodes passe sur le code final pour les
champs, les références imbriquées et les résultats propriétaires. Tous les
processus finaux cités sont terminés ; journaux et chronologie dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1–B5, D1, AS2/AS9/AS12 | Les cibles des descendants possédés sont conservées par leur chemin complet | Modèle des huit dispositions, champs homonymes, profondeurs deux et quatre, fabriques, retours conditionnels et restitution entière | P — graphes de types finis, &Int/&mut Int ; détachement d'un emprunt descendant encore ouvert |
| H1/H2, T1/T6, AS8/AS12 | L'accès explicite au contenu ne déplace pas les allocations ni leurs cibles | `read(&*result.inner)`, sonde C de trois adresses, réemprunt d'enfant après retour mutable, refus de drop et d'accès précoce | P — lectures et emprunts de contenu couverts ; modifications des champs descendants via helper non généralisées |
| L1/L2/L6, AS10/AS13/AS14, RT6/RT8, SL1 | Destruction unique des descendants, jamais des cibles empruntées ; pas de réemploi vivant | Inactive, LaunchFailed et échec natif injectés, Select perdant, pools de capacité un/deux réemployés ; six mutations dont deux acceptations invalides détectées | P — UBSan O0/O2, pas de preuve ASan/TSan ni d'exhaustivité |

Le refus du graphe Outer → A<Inner> → &Int annoncé ci-dessous est corrigé.
Les prochains contre-exemples valides refusés sont consignés dans
`validation/open-nested-detached-reference.crust` et
`validation/open-async-task-relay-argument.crust`. Aucun arbitrage normatif
n'est déduit de ces restrictions du compilateur.

Lot précédent : [structures async mixtes](cycles/ASYNC_MIXED_STRUCTURES_CYCLE.md).
Treize méthodes passent à O0/O2 ; le comptage final O0 relève 23 exécutions
natives et 32 programmes invalides refusés aux deux étapes. Neuf mutations
sont détectées après correction d'un test qui n'exerçait pas son point
d'injection. Régressions : 161 méthodes après le correctif des sources et
33 méthodes après celui du placement ; sélections recouvrantes. Tous les
processus cités sont terminés. Aucun changement normatif.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST1/ST6–ST16, B1–B5, D1, AS2/AS9/AS12 | Un porteur possédé conserve les pools de ses enfants et les cibles empruntées | Modèle indépendant des 8 dispositions × direct/fabrique ; cible enfant non promue ; mutabilité, copie non Copy refusée, descendant possédé dans un pool distinct | P — emprunts directs Int ; emprunts dans les descendants encore ouverts |
| T1/T6, P3/P4, AS8/AS12 | Le placement suit les retours par paramètre sans déplacement d'adresse | Remplacement en boucle par tâche ou fabrique ; sonde des trois adresses sur suspensions et transfert ; deux mutations de placement détectées | P — origines locales suivies par contrats ; placement général non achevé |
| L1/L2/L6, AS10/AS13/AS14, RT6/RT8, SL1 | Nettoyage unique des seuls enfants possédés ; prêts détachés conservés | Inactive, échecs injectés, thread natif, retour anticipé et Select perdant pendant un argument suspendu ; slots immédiatement réutilisables ; neuf fautes détectées, UBSan O0/O2 | P — pas de nouvelle preuve ASan/TSan ; handles lancés soumis aux arbitrages existants |

L'écart mixte direct du lot précédent est corrigé. Le programme
`validation/open-nested-owned-borrowed-capture.crust` reste refusé : un champ
A<Inner> dont Inner contient un emprunt exige des projections supplémentaires.

Lot courant : [fabriques de tâches à résultat emprunté détaché](cycles/DETACHED_TASK_FACTORIES_CYCLE.md).
Treize méthodes passent à O0/O2 : 21 exécutions natives et 30 programmes
invalides refusés aux deux étapes au comptage O0. Huit mutations détectées.
Les régressions passent 190 méthodes puis 107 après les compléments du waiter
et de Select ; 100 méthodes de champs passent sur le compilateur final.
Ces sélections se recouvrent. Chronologie et limites dans le rapport ; tous
les processus finaux sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST8/ST13/ST14, AS10/AS12, B1/B2/B4a | Le résultat détaché conserve sa vraie cible, sans retenir les autres champs ni le stockage du porteur | Contre-exemple de drop après await auparavant accepté aux deux étapes puis refusé ; modèle cible × instant × trois chemins, mutation de perte du prêt | P — champs partagés Int ; projections mutables et graphes généraux ouverts |
| ST10, D1, T1/T6, AS2/AS9 | Les fabriques et helpers ont un contrat de terminaison disponible ; les cibles restent durables même après remplacement | Trois ordres de déclarations, retours conditionnels, pool du porteur terminé, cible locale refusée, waiter et Handle public | P — inférence à la demande puis stabilisation ; pas de preuve générale de convergence |
| L1/L2/L6, RT6, AS8/AS13/AS14, SL1 | Nettoyage unique et prêts du perdant conservés jusqu'au drop de Select | Refus de lancement injecté, inactive, fabrique dans Select, réemploi en boucle, huit mutations et UBSan O0/O2 | P — sans obligation de handle lancé non résolue ; ASan/TSan non établis |

L'écart de fabrique détachant un champ signalé dans le cycle historique
ci-dessous est corrigé dans ce périmètre.

Lot courant : [contrats de capture par champ et restitution du porteur](cycles/ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE.md).
Treize méthodes passent à O0/O2 : 24 exécutions natives, 37 programmes invalides
refusés aux deux étapes au comptage O0. Sept mutations nouvelles et huit
historiques sont détectées ; la nature des détections est détaillée dans le
rapport. La régression élargie passe 195 méthodes à O2 sous UBSan. Tous les
processus finaux sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| B1/B2/B3/B4a, AS2/AS9, MT8 | Chaque champ garde sa cible et sa capacité dans les relais | Modèle de six accès × deux relais, contrat symbolique par champ, mutations de fusion | P — Int/&Int/&mut Int ; graphes mixtes ouverts |
| T1/T6, D1, ST6–ST15, AS10/AS12 | Le porteur retourné conserve exactement ses cibles, sans promotion ni déplacement | Retour entier partagé/mutable, fabriques, parent, boucles, conditions, modèle des quatre dispositions, adresses et slot réutilisé | P — cas directs et fabriques du porteur couverts ; fabrique détachant un champ encore refusée |
| L1/L2/L6, AS8/AS13/AS14, RT6, SL1 | Nettoyage unique, prêts conservés après await et pour le perdant Select | Inactive, LaunchFailed injecté, Select, contre-exemples de drop, sept mutations et UBSan O0/O2 | P — pas de handle lancé abandonné, pas de nouvelle preuve ASan/TSan ni de preuve générale |

Les deux écarts de relais mixte et de retour entier mentionnés dans le lot
historique ci-dessous sont corrigés dans ce nouveau périmètre.

Lot courant : [captures propriétaires de structures empruntantes](cycles/ASYNC_OWNED_BORROWED_CAPTURES_CYCLE.md).
Onze méthodes passent à O0/O2 : 19 exécutions natives et 24 programmes invalides
refusés aux deux étapes au comptage O0. Huit mutations sont détectées ; la
régression élargie passe 155 méthodes. Tous les processus finaux sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, B1/B2/B3/B4a, D1, MT8 | Le transfert du porteur conserve les prêts de ses champs | Direct, fabriques, relais de tâche, mutable et modèle de deux durées × deux chemins | P — Int/&Int/&mut Int ; relais mixte partagé/mutable trop restrictif |
| AS2/AS5/AS8/AS9/AS13/AS14, RT6/RT8, L1/L2/L6 | Nettoyage du porteur unique, jamais de destruction de sa cible | Tâche inactive, échec de lancement, thread natif, argument préparé et Select perdant | P — sans obligation de join non résolue ; huit mutations, UBSan O0/O2 |
| ST6–ST15, AS12 | La cible d'une référence détachée survit au porteur | Résultat partagé utilisé après join, drop de cible prématuré refusé | P — retour de structure entière encore refusé ; graphes mixtes ouverts |

Lot courant : [enveloppes Result de valeurs locales](cycles/LOCAL_RESULT_ENVELOPES_CYCLE.md).
Dix-neuf méthodes passent à O0/O2 : 29 exécutions natives et 36 programmes
invalides refusés aux deux étapes au comptage O0. Les 14 mutations finales et
huit historiques sont détectées ; une mutation antérieure redondante et un
point d'injection périmé sont audités dans le rapport. La régression finale
passe 138 méthodes à O2. Tous les processus finaux cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST6–ST15, AS9/AS12, B1/B2/B4 | L'enveloppe conserve ses cibles et réservations après fin de l'état | Relais opaques, méthode, mutable, branches/boucles et extractions imbriquées | P — familles Int/&Int/&mut Int testées ; graphes généraux ouverts |
| D1, L7, exigences de stockage | Result<T> et Result<A<T>> restent distincts dans signatures et jonctions | Modèle 2×2, annotations, feature et contre-exemple mixte refusé | P — distinction aussi sans charge ; couverture finie |
| L1/L2/L6, RT6/RT7, AS12 | Une erreur sans charge ne crée ni identité ni destruction fictive | Échecs injectés, relais et trois formes de contrôle, branche terminante conservée | P — absence prouvée distincte de l'inconnu ; UBSan O0/O2, pas de preuve générale |

Lot courant : [résultats locaux async contenant des emprunts](cycles/ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md).
Dix-sept méthodes ciblées passent à O0/O2 : 36 exécutions natives et 36
programmes invalides refusés aux deux étapes. Neuf mutations finales sont
détectées ; la survie initiale d'une faute non exercée et son audit sont conservés.
La régression finale de 98 méthodes passe. La régression élargie antérieure
comporte 238 réussites et une fixture historique erronée, reproduite avant
le lot et corrigée ; les 49 méthodes des deux modules historiques passent
ensuite avec UBSan. Tous les processus finaux cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST6–ST15, B1/B2/B4a, AS9/AS12 | Champs empruntés du résultat conservés après libération de l'état | Await/join, fabriques, relais sync/async, champs disjoints, mutable et Select, neuf mutations | P — champs Int/&Int/&mut Int, cibles paramétriques durables ; graphes mixtes ouverts |
| D1, T1/T6, L7, AS5/AS13 | Racine locale chez le receveur, cibles jamais promues | Modèle indépendant des quatre dispositions de deux cibles, transferts parent successifs, résultats conditionnels | P — sources représentées ; signatures Result<T> locales générales ouvertes |
| L1/L2/L6, V5, AS8/AS14 | Adresses stables et nettoyage unique, y compris réservation non utilisée | Sondes C normales/suspendues, construction directe/helper, échec injecté, réemploi de slots | P — UBSan O0/O2 ; réserve inutilisée corrigée ; pas de preuve générale |

Lot courant : [résultats locaux async à champs propriétaires](cycles/ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
Douze méthodes ciblées passent à O0/O2 : 19 exécutions natives et 19 programmes
invalides refusés aux deux étapes. Huit mutations nouvelles et huit historiques
détectées. La régression élargie passe 180 méthodes ; 63 méthodes passent après
les derniers compléments de placement et de sources de fabrique. Chronologie
précise dans le rapport. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS12 | Racine construite chez le receveur, descendants laissés dans leurs pools | Retours directs, fabriques, relais, parent après join, identité C à travers deux polls | P — graphes finis sans emprunts, racines fraîches |
| D1, ST7, AS5/AS13 | Chaque pool descendant survit au résultat | Modèle de quatre dispositions × trois chemins d'appel, contrats de petits-enfants, refus aux deux étapes | P — sources représentées ; sources locales générales ouvertes |
| B1/B2, L1/L2/L6, AS8/AS14 | Prêt du résultat respecté, nettoyage unique et réemploi après destruction | Remplacements en boucle, échec injecté, tâche inactive, sondes suspendues, huit mutations | P — tests finis UBSan O0/O2 ; pas de preuve générale |

Lot courant : [pools async de structures empruntantes](cycles/ASYNC_BORROWED_STRUCT_POOLS_CYCLE.md).
Quinze méthodes ciblées passent à O0/O2 : 28 exécutions natives et 31 programmes
invalides refusés aux deux étapes. Dix mutations détectées. La régression finale
passe 153 méthodes à O2. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST1–ST4/ST10, AS8/AS9, T1/T6 | Champs empruntés initialisés, transportés et mis à jour sans posséder la cible | Constructeurs, arguments suspendus, branches/boucles, remplacements directs/sync/async | P — Int/&Int/&mut Int ; graphes mixtes ouverts |
| ST6–ST14, B1/B2/B4a, D1 | Cible protégée tant que le porteur reste emprunté ; détachement partagé et réservation mutable distincts | Contre-exemple tâche corrigé, variantes handle/alias, chemins disjoints et dix mutations | P — prêts des types représentés ; précision générale ouverte |
| AS10/AS12, L1/L2 | Retour partagé indépendant du porteur ; nettoyage unique sans promotion locale | Retour via helper, cible locale refusée, sondes suspendues, UBSan O0/O2 | P — retours entiers/captures propriétaires de structures empruntantes ouverts |

Lot courant : [pools de structures async](cycles/ASYNC_STRUCT_POOLS_CYCLE.md).
Les pools locaux/injectés et les constructeurs nommés sont raccordés pour les
structures Int/A<T> finies prises en charge. Le retour frais depuis un pool
injecté transmet les sources des champs dans les contrats.
Quinze méthodes ciblées passent à O0/O2 : 25 exécutions natives et 19 programmes
invalides refusés aux deux étapes. Huit mutations sont détectées. La régression
élargie passe 174 méthodes ; 51 méthodes supplémentaires de contrats/résultats
passent sur l'état final. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| A1–A4/P8, ST1–ST4, AS8 | Source et layout durables entre polls ; valeurs initialisées avant exposition | Défauts, champs nommés, ordre avec await, pools injectés et alias, sonde de slots | P — Int/A<T> finis ; champs empruntés ouverts |
| ST15/ST16, D1, T1/T6, AS10/AS12 | Nettoyage des champs préparés ; dépendance aux sources de tous les descendants | Retour anticipé, suspension, graphe imbriqué, résultat direct/fabrique et voisin à pool trop court | P — résultat neuf dans pool injecté ; résultat local général ouvert |
| B1/B2, L1/L2, AS14, SL1 | Réemprunts protégés ; fermeture après destruction, réemploi sans déplacer le voisin | Drop admis/refusé, continue/break, sonde suspendue, huit mutations ciblées | P — couverture finie UBSan ; complément Select suivi dans le rapport |

Lot courant : [fabriques de tâches et destination du résultat](cycles/ASYNC_RESULT_FACTORIES_CYCLE.md).
Seize méthodes ciblées passent à O0/O2 : 35 exécutions natives et neuf
programmes invalides refusés aux deux étapes. Huit mutations détectées,
dont une acceptation indue de drop après retour d'une vue UTF-8.
La régression après le complément de terminaison est terminée : 216 méthodes
réussies en 166,544 s à O2, journal
`validation/async-result-factories-completion-regression-o2.log`.
Le passage précédent de 191 méthodes reste une preuve historique antérieure
à ce dernier complément.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS5/AS9/AS10/AS12, L7, V5, T1/T6 | La destination du résultat futur survit à la fabrique, sans déplacement ni conversion T/A<T> | Chaînes, transfert d'instance, branches et boucle, contrats et deux modes de sonde C | P — structures racines couvertes ; graphes généraux ouverts |
| B1/B2, D1, AS2/AS13 | Captures et résultat conservent leurs dépendances distinctes ; aucun pool ni cible empruntée n'est promu | Copies locales/de pool, parents, neuf voisins invalides, résultat &mut Int et &str, huit mutations | P — signatures de pont prises en charge ; préfixes de fabriques non généraux |
| ST10/ST15, AS10/AS12 | Les écritures de champs à la terminaison traversent les fabriques et restent visibles chez l'appelant | Contre-exemple accepté par une version intermédiaire puis refusé aux deux stages ; contrat final exact et mutation | P — fin normale suivie ; contrat de suspension inconnu conservé explicitement |
| L1/L2, AS8/AS14, RT6 | Le pont retourne une tâche vivante ; destruction et fermeture uniques | Inactive/drop, refus de lancement, deux tâches natives, sondes, assertion runtime et UBSan sur mutants | P — chemins finis O0/O2, pas d'API d'annulation ni de preuve générale |

Lot courant : [transferts parents et relais des résultats locaux async](cycles/ASYNC_RESULT_RELAYS_CYCLE.md).
Neuf méthodes ciblées passent à O0/O2 : 18 exécutions natives et quatre
programmes invalides refusés aux deux étapes. Six mutations sont détectées.
La régression finale passe 130 méthodes. Tous les processus sont terminés.
Les deux défauts corrigés (forme explicite d'affectation attendue et priorité
de la destination externe) et les journaux intermédiaires sont conservés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS10/AS12 | Les résultats neufs remontent les scopes et états dans la destination de l'ancêtre | Tâches nommées/transférées, chaîne de trois états, branches et boucles, sondes C d'identité | P — résultats indépendants sans champs propriétaires/empruntés ; fabriques sync et alternatives de provenance ouvertes |
| V4, B1/B2, D1, AS2/AS13 | Ancienne allocation conservée pendant attente ; aucune promotion d'une capture empruntée ou d'un pool | Remplacements directs et en boucle, copie locale indépendante, quatre voisins invalides, six mutations | P — formes et sources représentées ; pas de preuve générale |
| L1/L2, AS8/AS14 | Destruction unique de la chaîne d'états avant fermeture de la destination | Terminaison et destruction interne d'instance suspendue non lancée, slots vides et source fermée une fois | P — sondes finies O0/O2 sous UBSan, pas d'annulation publique |

Lot courant : [destination des résultats locaux neufs async](cycles/ASYNC_RESULT_STORAGE_CYCLE.md).
Quatorze méthodes passent à O0/O2 : 20 exécutions natives et trois programmes
invalides refusés aux deux étapes. Six mutations détectées (cinq sur les contrats
et le placement, une au runtime avec UBSan). La régression finale passe 116
méthodes. Les erreurs initiales, une mutation survivante puis couverte et deux
classements initiaux non concluants sont conservés. Tous les processus sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| L7, V5, T1/T6, AS9/AS10/AS12 | Le résultat neuf survit à la récupération de l'état sans changer d'adresse | Destination cachée, copies, retours conditionnels/calculés, boucles, deux sondes C | P — structures sans champs propriétaires/empruntés couvertes ; relais, fabriques et transferts parents ouverts |
| B1/B2, D1, AS2/AS13 | La copie relâche l'original mais conserve son pool ; les emprunts restent protégés | Trois voisins invalides, tableau de références, copie de pool, mutations de provenance et de table des captures | P — paramètres racines connus ; graphes généraux ouverts |
| L1/L2, AS8/AS14, RT6 | Nettoyage unique en cas d'échec, de fin normale ou d'abandon interne d'une instance non lancée | Lancement refusé, instance inactive, sonde d'enfant suspendu, deux tâches natives et mutation UBSan | P — scénarios finis O0/O2 ; pas d'annulation publique ni preuve de tous les ordonnancements |

Lot courant : [exigences de stockage dans les contrats](cycles/STORAGE_REQUIREMENTS_CYCLE.md).
Dix méthodes ciblées passent à O0/O2 : 12 exécutions natives et neuf programmes
invalides refusés aux deux étapes. Six mutations sont détectées. Les régressions
de 108 et 97 méthodes passent avant le dernier complément Select ; une sélection
de 46 méthodes passe sur le code final. Les erreurs initiales, corrections et
limites restent détaillées dans le rapport. Tous les processus sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST17/ST18, distinction T/A<T>, AS9/AS12 | Les annotations imposent la provenance locale ou pool ; les obligations traversent les contrats | Copie annotée auparavant refusée, helpers, fabriques, relais async, deux sources possibles, modèle de quatre combinaisons et voisins invalides | P — paramètres racines des structures couvertes ; projections générales non raccordées |
| L7, V5, B1/B2/B4 | Les résultats locaux sont construits dans la destination prévue, sans affaiblir les prêts | Retours calculés de copies dans deux branches, drop avant/après attente, Select et conversion, six mutations | P — flot conservateur ; résultat neuf sortant d'un état encore ouvert ; UBSan fini, pas de preuve générale |

Lot courant : [structures locales capturées par les tâches enfants](cycles/ASYNC_LOCAL_CAPTURES_CYCLE.md).
Treize méthodes passent à O0/O2 : 14 exécutions natives et onze programmes
invalides vérifiés aux deux étapes. Six mutations sont détectées après ajout
d'une sonde de stockage pour deux survivantes initiales. La régression finale
passe 97 méthodes ; une sélection précédente en passe 67 avant la garde de
retour A<T>. Les essais initiaux, l'erreur du harnais et le comptage corrigé
restent documentés. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, V5, L7, AS2/AS9/AS12 | La provenance locale traverse les captures et relais sans déplacement ni conversion en A<T> | Appelants sync/async, copies, retour du paramètre, retour/capture A<T> refusés, mutations | P — familles existantes de structures ; corps valables exclusivement pour une provenance locale encore refusés dans certains cas |
| AS8/AS10, L1/L2, ST17/ST18 | Copies locales indépendantes, sources fermées par leur scope, capacité d'états commune aux variantes | Sonde C normale/suspendue, lancement refusé, quatre réemplois d'un slot entre variantes, contrôle du pas des slots | P — union C par fonction et scénarios finis UBSan O0/O2 ; pas de nouvelle preuve ASan/TSan |
| B1/B2/B4, D1, AS12 | Le résultat emprunté protège la cible après fin de l'enfant ; la source survit à la capture | Dernier usage, mutation et drop voisins refusés, capture sortant d'un bloc trop court refusée | P — graphes et signatures généraux restent ouverts |

Lot courant : [provenances après les boucles async](cycles/ASYNC_LOOP_PLACEMENT_CYCLE.md).
Sept méthodes ciblées passent à O0/O2 : dix exécutions C et trois programmes
invalides vérifiés aux deux étapes. Cinq nouvelles mutations et les huit du
placement parent sont détectées. La régression élargie réussit 95 tests mais
sa commande échoue sur un nom de module incorrect ; les treize tests du module
réel passent séparément, soit 108 tests distincts réussis. Les essais initiaux
et l'erreur de commande restent documentés. Tous les processus sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T3/T5/T6, V5, L7, AS9/AS12 | Les producteurs possibles après une boucle construisent dans le stockage du receveur parent | Zéro à cinq itérations, continue/break, scopes et boucles imbriqués, modèle de propagation à plusieurs passages | P — familles de structures locales couvertes ; provenance inconnue conservatrice, états enfants encore ouverts |
| V4, L1/L2, B1/B2, D1 | Ancienne valeur vivante pendant construction ; nouvelle adresse conservée ; pools des champs et prêts protégés | Sonde C des versions successives, compteur de destructions, emprunt et source trop courte refusés, treize mutations détectées | P — tests finis UBSan O0/O2 ; pas de preuve générale ni nouvelle mesure ASan/TSan |

Lot courant : [placement parent des structures locales async](cycles/ASYNC_LOCAL_PARENT_CYCLE.md).
Quatorze méthodes ciblées passent à O0/O2 : 29 exécutions natives et cinq
programmes invalides refusés aux deux stages. Huit mutations finales sont
détectées. La sélection de 51 méthodes passe sur le code final ; la régression
élargie de 148 méthodes précède les derniers compléments. Chronologie et
échecs initiaux sont conservés dans le rapport. Tous les processus sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T3/T5/T6, V5, L7, AS9/AS12 | Le producteur construit dans la stack du parent, sans déplacer le résultat ni retenir le stockage temporaire enfant | Blocs successifs, if/match, break/continue, receveurs existants/nominaux, sonde d'identité et curseurs | P — provenance après boucle statement à généraliser ; transfert aux tâches enfants ouvert |
| ST17/ST18, D1/T11, B1/B2 | Une copie locale est indépendante de son original ; les champs possédés gardent leurs pools | Copies possédées/partagées et méthode, pool enfant refusé, prêt/drop refusé ; mutations copie/champs détectées | P — familles de structures prises en charge, sans promotion des cibles |
| V4, L1/L2/L6, AS8 | Ancienne valeur vivante pendant l'évaluation, nettoyages uniques et récupération du suffixe libre | Remplacement direct/nommé/conditionnel, modèle de trois itérations, deux receveurs, huit mutations finales | P — sondes finies UBSan O0/O2, pas d'annulation publique ni preuve générale |

Lot courant : [réception locale de structures depuis un helper en async](cycles/ASYNC_LOCAL_STRUCT_HELPERS_CYCLE.md).
Onze méthodes ciblées passent à O0/O2, cinq mutations sont détectées.
La régression élargie passe 120 méthodes avant la garde finale T/A<T> ; une
sélection de 50 méthodes et la baseline ciblée passent sur le code final.
Les essais initiaux non concluants et leur chronologie sont conservés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| L7, T1/T6, V5, ST17/ST18, AS9/AS12 | Le résultat local est construit dans la data stack du receveur ; copie locale distincte de celle d'un pool | Programme auparavant refusé, variantes de bridges, copies propriétaires/partagées, sonde de stockage et métadonnées | P — réception dans le scope courant ; transfert au parent et aux états enfants ouverts |
| B1/B2/B4a, ST15, L1/L2/L6, AS8/AS9 | Prêts respectés à travers yield ; valeurs détruites avant fermeture de la stack | Dernier usage/drop admis/refusé, modèle de trois préfixes de boucle, nettoyages suspendu et normal, mutation de fermeture détectée | P — familles représentées, UBSan O0/O2 ; pas d'annulation publique |
| Règles T/A<T> du brouillon 05, V4 | Un paramètre, une annotation ou une réaffectation ne convertit pas T local en A<T> | Contre-exemple affiné et audit temporaire, refus des deux substitutions, mutations type détectées | P — provenance locale dans l'état courant ; signatures d'états enfants non raccordées |

Lot courant : [structures propriétaires dans les appels synchrones depuis async](cycles/ASYNC_OWNED_STRUCT_SYNC_CALLS_CYCLE.md).
Quatorze méthodes ciblées passent à O0/O2, dont 23 exécutions natives et quinze
programmes invalides refusés dans les deux stages au passage final O2.
La régression de 114 méthodes passe sur le code final. Cinq mutations sont
détectées après audit de deux survivantes dues au ciblage initial ; les journaux
initiaux et finaux restent conservés. Tous les processus cités sont terminés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, ST1/ST7, D1/T11, AS12/AS13 | Un auxiliaire reçoit/restitue le graphe explicitement, en conservant les pools des descendants | Relais successifs, modèle de huit placements, Result simple/double et échecs injectés, interrogation de contrat historique | P — graphes finis sans emprunts ; création locale et restitution après remplacement ouvertes |
| B1/B2/B4/B4a, ST15, AS9 | Un emprunt de champ propriétaire réserve le porteur jusqu'au dernier usage, y compris à travers yield | Lecture et mutation admises, consommation et lecture concurrente refusées, perte de prêt détectée par mutation | P — projections Int dans les structures prises en charge |
| L1/L2/L6, AS8, T6 | Même adresse à la remise, nettoyage unique après consommation, échec ou suspension d'un argument | Trois sondes C, remplacement puis consommation, réemploi, mutations Err/nettoyage/destruction détectées | P — UBSan O0/O2, sondes finies ; pas d'annulation publique ni preuve générale |

Lot courant : [retours de structures propriétaires](cycles/ASYNC_OWNED_STRUCT_RETURNS_CYCLE.md).
Douze méthodes ciblées réussissent à O0/O2 ; passage final O0 : 19 exécutions
natives et onze programmes invalides refusés par les deux stages. Cinq mutations
nouvelles et cinq antérieures détectées. Régression élargie de 86 méthodes avant
le dernier complément de relais ; 54 méthodes sur le code final, plus les douze
tests ciblés finaux. Chronologie et limites dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| D1/T11, ST1/ST7, AS5/AS12/AS13 | Le résultat retient le pool de chaque champ, distinct de celui de la racine | Modèle de huit dispositions, contrats de fabriques et helpers, contraintes de sources ; mutations pool/contrat détectées | P — graphes finis sans emprunts des types listés |
| T1/T6, B1/B2/B4 | Transfert explicite et protection des champs après remise | Await direct/nommé, Result imbriqué, if/break, emprunt puis drop admis/refusé | P — signatures et constructions générales ouvertes |
| AS8/AS9/AS10, L1/L2/L6 | Même adresse et une destruction, avant ou après remise | Deux sondes C, lancement refusé, réemploi, mutation de destruction prématurée | P — UBSan, chemins finis, pas d'annulation publique |

Lot courant : [captures de structures propriétaires](cycles/ASYNC_OWNED_STRUCT_CAPTURES_CYCLE.md).
Neuf méthodes ciblées réussissent à O2 : 20 exécutions natives et 32 programmes
refusés par les deux stages. Couverture O0 des neuf méthodes en deux passages.
Cinq mutations détectées après ajout d'une sonde pour une mutation survivante.
La régression initiale retrouve un attendu historique obsolète, reproduit avant
le lot puis corrigé ; onze méthodes de contrôle passent. La régression consolidée
O2 de 76 méthodes réussit en 115,025 s sur le code final. Tous les processus
de ce lot sont terminés ; chronologie et limites dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| D1/T11, AS5/AS13, ST1/ST7 | Chaque pool du graphe possédé survit à la tâche et traverse les contrats | Contre-exemple de fabrique, modèle de 24 dispositions/appels, chemins symboliques imbriqués, trois mutations de sources | P — graphes sans emprunts et types listés |
| T1/T6, ST5/ST15, B1/B2/B4a | Transfert explicite, accès mutable, emprunt terminé avant capture | Renommage, enfant async, champs Int/A<Int>, familles de collections, refus des lectures incompatibles et usages après consommation | P — pas de retour async d'agrégat propriétaire |
| AS8/AS9/AS14, L1/L2/L6, RT8 | Adresses conservées, destruction unique enfant avant parent, reprise des slots | Quatre états C, lancement refusé, thread natif, argument préparé ; mutation survivante puis détectée | P — sondes sans exécution concurrente de la racine, UBSan seulement |

Lot courant : [retours directs d'allocations attendues](cycles/ASYNC_DIRECT_OWNED_RETURNS_CYCLE.md).
Six méthodes ciblées passent à O0 et O2 ; trois mutations sont détectées.
La régression élargie de 44 méthodes passe à O2 sur le code final. Tous les
processus du lot sont terminés ; la chronologie et les limites figurent dans
le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| T1/T6, AS4/AS10/AS12, D1/T11 | Retour explicite de A<T>, distinction avec le Result d'un handle, source durable | Quatre types, tâches nommées/calculées et branches, pool trop court et types incompatibles refusés | P — agrégats généraux ouverts |
| V5, L1/L2, AS8/AS14, SL1 | Même adresse après remise, une destruction, nettoyage d'un enfant suspendu et des arguments préparés | Sondes C d'identité/destruction, Select propriétaire, return dans argument suivant, réemploi ; mutations de destruction et d'oubli d'enfant détectées | P — chemins finis, pas d'annulation publique |

Lot courant : [Result propriétaires produits par await](cycles/ASYNC_AWAITED_OWNED_RESULTS_CYCLE.md).
Neuf méthodes ciblées passent à O0 : 110 exécutions natives et 17 programmes
refusés dans les deux stages (34 contrôles). Les sondes de nettoyage aux
suspensions et le cas Select passent également à O2. La régression de 96
méthodes et la baseline finale de neuf méthodes passent à O2. Cinq mutations
nouvelles et les huit du lot précédent sont détectées ; les deux campagnes
sont terminées avec le code 0. Chronologie et limites dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS4/AS10/AS12, T1/T2/T6, U1 | Attente directe consommée une fois, transfert explicite, type et source conservés | Arguments synchrones et async, retours et match, six formes d'attente, quatre charges, deux niveaux de Result, voisins refusés | P — signatures et conteneurs généraux ouverts |
| AS2/AS8/AS14, B4a, L1/L2/L6, SL1 | Un argument déjà reçu reste possédé pendant la suite ; nettoyage unique si l'appel n'a pas lieu | Return dans argument suivant, dix sondes de suspension fondées sur un modèle fini, perdante Select, identité au réemploi ; mutations des préparations et du nettoyage détectées | P — modèle fini, aucune annulation de tâche lancée |

Lot courant : [résultats sans charge et relais](cycles/ASYNC_FAILURE_ONLY_RESULTS_CYCLE.md).
Neuf méthodes ciblées passent à O0 (38 exécutions natives, 12 programmes refusés
dans les deux stages), puis douze à O2 sur le code final. Les formes directes
et imbriquées sont raccordées et testées. La sélection de 149 méthodes passe
avant ces derniers raccordements ; 42 méthodes passent après les formes directes.
Huit mutations nouvelles et cinq des résultats Select sont
détectées. La régression runtime élargie passe 275 méthodes sur la version
précédant les expressions directes et imbriquées, couvertes séparément.
La chronologie des versions, la première campagne et ses limites sont
conservées dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS4/AS12/AS16, RT6 | Non-terminaison prouvée distincte d'un effet inconnu ; seul LaunchFailed peut continuer | Neuf familles de résultat, attente directe, inconnu récursif, erreurs injectées | P — variantes générales non raffinées |
| B1/B2, D1/D3, U1 | Une enveloppe sans charge ne reçoit pas de pool fictif ; une charge possible garde sa source | Retours et transferts, modèle cinq issues finies, absence de pool de résultat, huit mutations détectées | P — cas finis, versions exercées détaillées dans le rapport |
| T1/T2/T11, L1/L2, RT7 | Import/break explicite ; responsabilité des arguments et exports de pont | Result Int/String/Vector, attente d'argument suivant, return anticipé, réemploi, Result imbriqué | P — types listés, choix de handles dans if, pas toutes les compositions |

Lot courant : [résultats Select et effets de champs](cycles/SELECT_RESULTS_CYCLE.md).
Douze méthodes ciblées passent à O0 et O2 ; le passage O0 compte 27 exécutions
natives et 20 programmes refusés dans les deux stages. Cinq mutations nouvelles
sont détectées après renforcement d'un oracle de terminaison ; onze mutations
de terminaison, huit de contrats et huit de suspension restent détectées.
La sélection de 122 méthodes et la régression async élargie de 275 méthodes
passent à O2. La chronologie et les limites sont détaillées dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS4/AS12/AS16, ST10/ST13 | Conserver ensemble résultat typé et champs modifiés à la terminaison ou à la suspension | Gagnante et perdante, retour propriétaire/vue, modèle de neuf ordres, cinq mutations | P — agrégats généraux et corrélations ouverts |
| B1/B2/B4/B5, D1/D3, L1/L2 | Sources et cibles encore protégées après attente et drop de Select ; nettoyage unique | Int/String/Vector, vues partagées/mutables, réemploi, refus de drop/mutation et source locale | P — familles représentées, pas tous les conteneurs de références |
| RT6, U1 | LaunchFailed ne crée pas de résultat réussi ; usage explicite des résultats | Deux échecs injectés, champs initiaux conservés, propriétaires et résultats faillibles inutilisés refusés | P — handle ordinaire attendu, perdante avec handle non arbitrée |

Lot courant : [Select depuis le langage source](cycles/SELECT_SOURCE_CYCLE.md).
Vingt-quatre méthodes ciblées passent à O0 et dans la baseline de mutations O2.
Le passage final O0 exécute 56 programmes admis et vérifie 49 programmes
refusés dans les deux stages (98 contrôles), dont un modèle indépendant de
neuf ordres de suspension. Douze mutations nouvelles, huit mutations des
nettoyages précédents, huit des contrats Select et sept du runtime sont détectées.
Les sélections de régression passent 76, 95 puis 97 méthodes ; le rapport précise
les versions exercées et les défauts de couverture corrigés pendant le lot.
La régression runtime élargie passe 292 méthodes sur le code précédant les
deux derniers compléments, puis la sélection de 97 méthodes exerce le code final.
Les sections suivantes décrivent la chronologie des lots
précédents et leurs limitations au moment de leurs passages.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, B1/B2/B4/B5, AS2/AS12 | Capture immédiate, perdantes retenues, résultat emprunté encore durable après drop | Lectures/mutations/drop admis ou refusés, deux cibles possibles, mutations des prêts et des provenances | P — unions conservatrices, types généraux ouverts |
| SL1, T1/T2/T11, AS8/AS9 | État stable, transferts explicites, même type de résultat et attente unique conservée | Blocs, if, break, renommages, branches calculées ; contre-exemple de mutabilité corrigé | P — jonctions de l'état extérieur conservatrices |
| SL1, L1/L2, S4/S5, AS10/AS14 | Destruction unique et réemploi après nettoyage des perdantes | Deux pools propriétaires, boucle de huit réemplois, sorties anticipées, construction suspendue, Select imbriqué, modèle neuf ordres | P — ordonnancements exercés sous UBSan ; pas de preuve générale |
| SL1, ST10/ST13, AS4/AS12 | Les écritures de la perdante ne sont pas restaurées par sa destruction | Champ modifié avant yield, résultat 9 puis cible 2, refus de drop de cette cible | P — préfixes conservateurs, handles lancés à arbitrer |
| SL1, AS4/AS12 | L'ordre de poll appartient à chaque alternative de sélection ; un corps jamais pollé n'exige pas de résumé | Contre-exemple récursif admis, if/break à effets distincts, mutations de frontière et d'aplatissement détectées | P — contrats de suspension possibles, sans corrélation générale des gagnantes |
| SL1, B4/B5, AS10/AS12 | Les captures terminées d'une gagnante certaine sont libérées ; ses résultats et les perdantes restent protégés | Programme auparavant refusé admis, voisins de mutation refusés, attentes équivalentes par chemin, deux mutations détectées | P — familles représentées, résultats agrégés généraux encore ouverts |

Lot précédent : [parsing et composition des contrats Select](cycles/SELECT_CONTRACTS_CYCLE.md).
Seize méthodes ciblées passent à O0/O2 ; modèle indépendant de 25 couples
de branches et sonde Select C avec deux champs modifiés et huit réemplois.
Huit mutations nouvelles et les dix-neuf précédentes sont détectées.
Les sélections de régression passent 74 puis 83 méthodes, selon la chronologie
du rapport. Le vérificateur des captures et le backend source restent ouverts :
un programme Select complet n'est pas encore compilable.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS2/AS4/AS9/AS12, B4/B5 | Gagnante terminée, perdantes suspendues ou non pollées ; aucune restauration fictive | Modèle 25 couples, assertions de priorité, champs et résultat emprunté, sonde C | P — union conservative ; source non exécutable |
| SL1, T1/T2, I1/I6 | Transferts explicites, type de résultat commun, captures conservées dans les choix | Parsing, construction inactive, if/break/move, contre-exemple et huit mutations | P — contrat symbolique ; contrôle de l'attente unique à raccorder |
| B1/B2, ST10/ST13, AS8–AS10 | Les dépendances laissées par la perdante persistent après destruction | Préfixes via enfants, helpers opaques et sélections imbriquées ; champs C après drop | P — rétention des prêts côté backend encore ouverte, handles lancés à arbitrer |

Lot courant : [effets de champs aux suspensions](cycles/SUSPENSION_EFFECTS_CYCLE.md).
Les états aux yield et aux suspensions des enfants directs sont résumés
séparément de la terminaison normale. Quinze méthodes ciblées passent à
O0/O2 ; modèle indépendant de 64 séquences et huit mutations détectées.
La régression de contrats passe 94 méthodes, puis 52 après la garde finale
sur les conteneurs non suivis. La régression runtime élargie passe 292 méthodes.
Le rapport précise les versions chargées et les périmètres de ces exécutions ;
les onze mutations antérieures des contrats restent détectées.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS4/AS9/AS12, ST10/ST13, B4/B5 | Une restauration après yield ne masque pas la cible laissée par une perdante | États séparés, trois appels, captures sauvegardées, branches, boucles, RHS suspendu, modèle 64 séquences | P — champs injectés représentés ; composition Select source non raccordée |
| B1/B2, D1/D3, AS12 | Attente complète précise ; résumé inconnu distinct d'un résumé vide | Voisins drop admis/refusés, champs mutables, enfant divergent, inconnu propagé, huit mutations | P — effets concurrents des handles et agrégats généraux ouverts |
| SL1, AS8–AS10 | Détruire une perdante n'exécute pas sa continuation | Sonde C avec callbacks générés, huit réemplois, identité et valeur du champ après destruction | P — harnais C ; pas encore un refus du programme Select source |

Lot courant : [nettoyages générés aux suspensions](cycles/SUSPENDED_CLEANUP_CYCLE.md).
Les états disposent de chemins de destruction par point de reprise, avec
prévalidation des enfants directs et sans attente cachée des handles lancés.
Le remplacement async explicitement marqué d'une construction est corrigé.
Dix méthodes ciblées passent à O0/O2, avec modèle de 22 scénarios et huit
mutations détectées ; la sélection pools/régions/notifications passe 47 méthodes.
La sélection de champs passe 42 méthodes. La suite async complète passe 274
méthodes sur 275 ; son échec d'ancre d'instrumentation est corrigé et la méthode
repasse séparément. La chronologie est détaillée dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, AS8–AS10, L1/L2, S4/S5 | Détruire les ressources réellement vivantes à la suspension, enfant avant ses cibles | Captures préparées, attente sur trois niveaux, pools, branches, boucles, renommage, réemploi | P — callbacks générés exercés par harnais C ; Select source non raccordé |
| V4, B1/B2, D1 | Nouvelle allocation évaluée avant destruction de l'ancienne ; emprunt conservé pendant await | Construction et appel explicitement marqués, modèle 22 scénarios, voisins refusés | P — formes de remplacement exercées ; pas preuve générale |
| RT6/RT7, SL1 | Prévalidation sans destruction d'un arbre portant une obligation d'attente | Handle dans un enfant, reprise normale après refus interne, résultat de join Ok/Err, huit mutations | P — arbitrage de la perdante avec handle toujours ouvert |

Lot courant : [mécanisme interne de Select](cycles/SELECT_RUNTIME_CYCLE.md).
Les branches ont des tickets de réveil distincts qui notifient leur appelante.
Le scan respecte l'ordre des branches éligibles ; les perdantes sont retenues
jusqu'au drop. Sept méthodes finales passent à O0/O2, dont un modèle de
3 280 opérations et une sonde de frames générées. Sept mutations sont détectées.
La syntaxe source et les nettoyages suspendus généraux ne sont pas encore
raccordés ; une perdante possédant un handle lancé demande un arbitrage.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| SL1, RT2/RT4, AS4 | Seules les branches prêtes avancent ; priorité d'écriture et réveil de l'appelante | Modèle 80 scénarios, réveils pendant poll, sélection imbriquée et fin de handle | P — mécanisme interne C ; vérificateur/source non raccordés |
| SL1, AS8–AS10, L1/L2 | Résultat extrait une fois, perdantes retenues, slots réemployés après destruction | Quatre états de nettoyage, huit tours de frames générées et A<Int>, sept mutations | P — callbacks suspendus fournis au harnais ; nettoyage général à générer |
| RT2/RT4, AS9, D4 | Notification tardive sans accès à une frame libérée ni réveil d'un remplaçant | Producteur concurrent, 16 tours de retrait/réemploi, 5 000 paires de notifications tardives par tour | P — entrées persistantes jusqu'à arrêt des producteurs ; pas de preuve générale ni TSan |

Lot courant : [provenances de champs aux reprises async](cycles/ASYNC_FIELD_LOOPS_CYCLE.md).
Les boucles réanalysent leurs entrées avec les nouvelles cibles de champs,
sans abandonner les obligations de nettoyage. Les identités initiales et les
provenances des reprises sont conservées séparément des vues UTF-8.
Huit méthodes ciblées passent à O0, quarante à O2 avec les lots de champs,
puis vingt sur les vues et résultats de boucles. Les quatre mutations ciblées
sont détectées ; les journaux sont référencés dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST11, B1/B2/B5, AS9/AS12/AS16 | Reprises vérifiées avec toutes les cibles possibles, sauvegarde de l'ancienne cellule | while 0/1/3, continue, enfants, boucles imbriquées, échanges de champs, helpers de stockage | P — cibles représentées de porteurs injectés ; corrélations exclusives générales ouvertes |
| L1/L2, D1/D3 | Nettoyage conservé et sources protégées jusqu'au dernier usage | Modèle de 12 traces, reset historique/réemploi, quatre mutations détectées | P — modèles finis ; configuration et chronologie dans le rapport |


Lot courant : [remplacement des champs mutables dans les états](cycles/MUTABLE_FIELD_COMPLETION_CYCLE.md).
Les stores directs et les helpers transmettent les nouvelles cibles des champs
`&mut Int` ; les réemprunts retiennent aussi la capacité du champ. Une alternative
inchangée ne crée plus de prêt du champ sur lui-même. L'oracle d'identité a été
renforcé après une mutation survivante ; les deux campagnes sont consignées.
Dix méthodes finales passent à O0/O2 ; la sélection de contrats passe 58 méthodes
et celle des réemprunts/handles 56 à O2. Les cinq mutations finales sont détectées.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST11/ST12, B1/B2/B4/B5, AS12/AS16 | Nouvelle cible exclusive et capacité du champ réservée jusqu'au dernier usage | Store/helper, mutation, résultat partagé/mutable, enfant et fabrique, champ conditionnel | P — Int injecté ; origines générales ouvertes |
| D1/D3, AS13/AS14/AS15, RT6 | Nettoyage inactif sans store, réservations après attente ou échec | Modèle 8 cas (5 exécutés, 3 refusés), échec injecté, reset historique/réemploi, oracle d'identité | P — alternatives conservatrices ; résultats et mutations dans le rapport |


Lot courant : [champs modifiés et résultats empruntés](cycles/BORROWED_FIELD_COMPLETION_CYCLE.md).
Les provenances de terminaison distinguent la référence sauvegardée de la
cible du champ remplacé. L'affectation directe d'un champ partagé Int est
raccordée. Les contraintes de sources sont vérifiées après stabilisation des
provenances. Les frontières historiques des lots précédents sont conservées.
Onze méthodes ciblées passent à O0/O2 ; les sélections finales de contrats et
de retours d'emprunts passent respectivement 48 et 85 méthodes à O2. Cinq
mutations sont détectées. Les erreurs de fixtures et les premières passes en
échec sont conservées et expliquées dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS16, B4/B5, ST10/ST13 | Effets et résultat distincts, captures sauvegardées avant publication | Ancien/nouveau champ, enfants, fabrique et handle public ; programme consigné exécuté | P — Int partagé, résultat Int emprunté ; agrégats généraux ouverts |
| B1/B2, D1/D3, AS13/AS15 | Cible retenue sans prolonger une autre allocation inutilement | Modèle 8 cas (2 exécutés, 6 refusés), drop/reset historique, mutation refusée, cinq mutations détectées | P — cas finis, diagnostic local encore général ; chronologie des passes dans le rapport |


Lot courant : [effets différés des fabriques synchrones](cycles/FACTORY_FIELD_EFFECTS_CYCLE.md).
Les fabriques conservent maintenant les modifications de champs partagés Int
préparées dans leurs nouvelles tâches. L'attente les publie à travers les
relais et les ponts async/natifs ; la destruction inactive ne les applique pas.
Les rapports précédents conservent leurs frontières historiques.
Treize méthodes ciblées passent à O0 ; la sélection O2 passe 83 méthodes,
puis les deux ajouts finaux passent séparément à O2. La régression des contrats
passe 77 méthodes. Huit mutations ciblées sont détectées ; chronologie et limites
dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS2/AS5/AS16, B4/B5, ST10/ST13 | Création distincte de terminaison ; contrat opaque de fabrique | Relais, champs sauvegardés, branches, loop, helper attendante, pont async et natif | P — champs partagés Int injectés ; types généraux ouverts |
| AS12/AS13/AS14, B1/B2, D1/D3, RT6/RT7 | Cible durable et encore protégée après attente, absence d'effets si inactive | Modèle 8 cas (5 exécutés, 3 refusés), échec injecté, reset historique, réemploi ; huit mutations détectées | P — union conservative, modèles finis ; résultats finaux dans le rapport |


Lot courant : [contrats synchrones des handles portant des modifications](cycles/SYNC_HANDLE_FIELD_EFFECTS_CYCLE.md).
Les contrats conservent les entrées attendues et retournées avec leurs effets
différés, y compris par relais et jonction. Le test opaque ne dispose d'aucun
corps synchrone. Le raccourci des résultats scalaires a été retiré pour les
paramètres de tâche ; les retours de tableaux transférés sont raccordés à ce
parcours. Les rapports précédents indiquent leurs frontières historiques.
Sept méthodes ciblées passent à O0, 67 à O2 avec les contrats de handles, et
96 dans la sélection tableaux/appels modulaires. Six mutations ciblées sont
détectées ; les journaux et la chronologie des autres sélections figurent au rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| B4/B5, ST10/ST13, AS12 | L'attente opaque publie les dépendances et le transfert conserve les effets différés | Trois appels, corps synchrones absents, branches et loop, deux handles | P — entrées de tâches/handles ; nouvelles fabriques modificatrices ouvertes |
| B1/B2, D1/D3, AS14, RT6/RT7 | Inactif sans écriture, pool et cibles encore protégés après attente | Modèle 8 cas (5 exécutés, 3 refusés), reset historique, réemploi, échec injecté | P — ensembles conservatifs de chemins, corrélation complète ouverte |

Lot courant : [modifications de champs à travers les tâches enfants](cycles/ASYNC_CHILD_FIELD_EFFECTS_CYCLE.md).
Les attentes directes et de handles publient les dépendances des enfants dans
le parent ; les états inactifs n'appliquent aucun effet. Les contrats des
instructions await Void, auparavant ignorées, sont corrigés avec un
contre-exemple de destruction prématurée. Les rapports antérieurs ci-dessous
conservent leurs limites historiques ; ce lot lève leur refus général des enfants.
Onze méthodes ciblées passent à O0 ; cinquante-deux à O2 avec les contrats et
le lot précédent. La sélection de régression finale passe 48 méthodes, et les
neuf mutations ciblées sont détectées. La sélection antérieure de 75 méthodes
et sa chronologie sont détaillées dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS4/AS12 | Les effets suivent les captures à travers attente, choix et transfert | Trois relais, douze variantes de transfert/attente, ancien emprunt et échanges de champs | P — champs partagés Int et résultats scalaires/Void ; relais synchrones ouverts |
| B1/B2, D1, AS13/AS14, RT6 | Inactif sans effet ; cibles durables après terminaison ou échec de lancement | Modèle 12 cas (7 exécutés, 5 refusés), refus injectés, cible enfant et contre-exemple Void | P — union conservative succès/échec, pas de preuve générale de concurrence |

Lot courant : [application des modifications de champs après join](cycles/ASYNC_FIELD_APPLICATION_CYCLE.md).
Les stores de champs `&Int` via helpers synchrones dans les états async/natifs
sont exécutables pour les porteurs et cibles injectés décrits dans le rapport.
Seize méthodes ciblées passent à O0 ; quarante et une avec les contrats à O2.
La régression finale passe 112 méthodes. Huit mutations sont détectées et une
survit, compensée par un contrôle ultérieur dans le scénario choisi.
Le contre-exemple de perte d'effets par match enum est corrigé. Le rapport
distingue la mutation survivante du contrôle de destination, les régressions
exécutées et les frontières non raccordées. Les limites des lots plus anciens
ci-dessous décrivent leur état à leur date ; ce lot lève une partie de leurs refus.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS12/AS13 | Le join publie les dépendances de la tâche ; création inactive sans effet | C natif, modèle 8 cas, choix de handles, match enum/builtin, loop/break/continue | P — champs partagés Int injectés ; enfants et relais synchrones ouverts |
| B1/B2, ST10/ST13 | Cible initiale détachée distincte de la cible courante ; jonction conserve toutes les alternatives | Helpers stockant les emprunts, stores conditionnels, drop/mutation/reset historique | P — récurrence des stores à travers backedge ouverte |
| D1/D3, AS14, RT6/RT8 | Échec de lancement et destruction inactive sans écriture ni double nettoyage | Refus de lancement injecté, réemploi de slot, méthode et bloc natif | P — union conservative succès/échec ; pas preuve générale multithread |

Étape en cours : [résultats empruntés et effets de terminaison](cycles/ASYNC_COMPLETION_RESULTS_CYCLE.md).
Les contrats des enfants attendus conservent ensemble les champs modifiés et
le résultat emprunté. Le modèle indépendant de seize scénarios a découvert et
fait corriger une perte de modification à travers les alias du porteur.
Vingt-cinq méthodes passent à O0/O2 : vingt-trois d'analyse, deux voisins C exécutés.
Onze mutations sont détectées et une sélection de régression passe 73 méthodes ;
la chronologie des versions testées est précisée dans le rapport.
Le remplacement de champs extérieurs dans un programme async reste refusé.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10/ST13, B4/B5, AS12/AS13 | Effets et résultats partagent les captures sauvegardées, sans confondre ancienne et nouvelle cible | Modèle 16 cas, relais, choix de handles, contre-exemple consigné | P — contrats ; application aux appelants réels ouverte |
| ST11/ST12, B1/B2 | Un résultat mutable conserve la réservation de son porteur | Contrat indirect et mutations de cible/capacité | P — types de résultats scalaires empruntés traités |
| S5, AS2/AS14, RT6 | Pas d'effet à la création ni de continuation après divergence ; lancement refusé sans payload | Régression du modèle 125 cas, attente directe et enveloppe de handle | P — corrélation générale Ok/Err non raccordée |

Dernier lot : [descripteurs des emprunts capturés](cycles/CAPTURED_CELL_DESCRIPTORS_CYCLE.md).
Les exigences de Cell traversent les tâches et les fabriques synchrones jusqu'à
stabilité, indépendamment de leur ordre de déclaration. Vingt-sept méthodes
ciblées O0/O2 passent, dont treize nouvelles ; modèle de huit scénarios et cinq
mutations détectées. Régressions de 72 et 102 méthodes. Les cibles inline et les effets
des remplacements de champs après attente restent ouverts.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| B4, ST8/ST13, AS2/AS12/AS13 | Une capture conserve le descripteur de l'allocation stockée dans un champ | Cinq relais/deux ordres, fabriques synchrones, identité, récursion bornée | P — Int Cell ; cibles inline non raccordées |
| B1/B2, ST11/ST12, D1/D3 | Résultat emprunté et capacité mutable restent protégés jusqu'au dernier usage | Modèle huit cas drop/reset/join, retour mutable, porteur local refusé | P — formes testées ; reset historique uniquement |
| L1/L2, RT6/RT8 | Une capture empruntée ne détruit pas sa cible | Inactive/drop, lancement refusé, thread natif et réemploi de slot | P — UBSan, pas de preuve générale de concurrence |

Dernier lot : [emprunts stockés par les bridges](cycles/CELL_REFERENCE_BRIDGES_CYCLE.md).
Quatorze méthodes ciblées passent à O0/O2, avec modèle indépendant de seize
scénarios (dix exécutés, six refusés) et huit mutations détectées. Le descripteur
réel est conservé pour les allocations et champs suivis. Les références capturées
brutes et la propagation des remplacements extérieurs après join restent ouvertes.
La régression finale de fonctions/divergence passe 45 méthodes ; les autres
sélections et leur chronologie figurent dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| B4, ST8/ST10–ST13, AS12/AS13 | Les stores temporaires conservent le descripteur et les cibles même sans effet final | Contrats relayés, choix conditionnels, méthode, identité et bridge C | P — cibles Cell connues ; pointeurs capturés bruts et effets après attente ouverts |
| B1/B2, D1/D3, L1/L2, RT6 | Dernier usage, nettoyage unique et réemploi sans cible pendante | Modèle 16 scénarios, pool capacité un, refus de lancement et thread natif | P — scénarios finis, pas preuve générale multithread |
| S5, B4 | La divergence conserve les exigences de représentation et ne fabrique pas un retour C | Deux variantes divergentes compilées, mutations et régressions | P — corps divergents compilés mais non exécutés |

Étape en cours : [contrats différés des champs async](cycles/ASYNC_STRUCTURE_EFFECTS_CYCLE.md).
L'inférence conserve les cibles remplacées à travers les auxiliaires synchrones
et les enfants attendus. Seize méthodes de contrats et un voisin synchrone
exécuté à O0/O2, modèle indépendant de 125 scénarios et sept mutations détectées.
Le raccordement aux états, au bridge
C et à l'appelant après join reste ouvert : le refus du backend est conservé.
Une analyse non résolue est distincte d'un contrat vide. Les régressions natives
de 312 méthodes et synchrones de 56 méthodes passent, ainsi que les 17 méthodes
de handles publics après le dernier correctif. Leur chronologie et leurs
limites figurent dans le rapport ; ces sélections se recouvrent.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST10, B4, ST13 | Les contrats instancient les nouvelles cibles depuis les arguments sauvegardés | Auxiliaires sans corps, origines détachées, alias, ordre et deux champs échangés | P — inférence des effets ; remplacement async encore non exécutable |
| AS2/AS4/AS14, RT6 | Créer n'exécute pas ; attendre applique les effets ; lancement refusé conserve l'ancien état | Modèle de 125 scénarios, enfants imbriqués, choix if/loop, destruction inactive | P — contrats, pas preuve d'application au runtime |
| S5, AS12/AS13 | Pas de continuation inventée ni d'effet perdu à une frontière non résolue | Divergence, while/continue/break, statuts incomplets et mutations | P — récursion, agrégats généraux, résultats empruntés d'enfants et relais via helper de handle non raccordés |

Dernier lot : [relais de handles concrets](cycles/CONCRETE_HANDLE_RELAYS_CYCLE.md).
Le descripteur d'entrée et les sources des résultats sont conservés lors de la
conversion publique. Les contraintes ordonnées remplacent le refus historique
global de reset ; les autres tâches restent protégées, même sans join futur.
Quatorze méthodes ciblées O0/O2 plus deux compléments, modèle de 32 cas,
régression de 122 méthodes et onze tests de tableaux. Sept mutations détectées,
une survivante. Le rapport distingue les versions testées, les erreurs de
fixtures et les compléments finaux ; il ne revendique pas un passage groupé
de seize méthodes sans échec.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS13, RT5, ST11–ST14 | Le résultat garde sa cible et la capacité d'origine après conversion | Contre-exemple exécuté, champs inline/indirects/détachés, Int/u8 | P — signatures exercées |
| B1/B2, D1/D3, RT7 | Captures protégées jusqu'à join, cibles jusqu'au dernier usage | Modèle indépendant de 32 cas, trois formes de capture, refus de lancement | P — scénarios finis |
| B4d, PR1 | Ordre lecture/join/reset propagé dans les contrats | Appelants sans corps, sources de champs et de cases, autre tâche active, chemins divergents | P — profil historique uniquement ; mutation masquée par un contrôle redondant |

Dernier lot : [résultats de handles projetés dans les champs](cycles/SYNC_HANDLE_FIELDS_CYCLE.md).
Neuf méthodes ciblées O0/O2, modèle indépendant de 36 scénarios et régression
handles de 43 méthodes. La régression élargie finale passe 107 méthodes O2.
Cinq mutations détectées, une survivante explicitée. Le rapport conserve
les échecs intermédiaires et distingue la chronologie des passages.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12, ST8/ST11–ST14, B1/B2/B5 | Captures relâchées après attente, chemins et capacité du résultat conservés | 36 scénarios, champs inline/indirects/détachés, relais et champs imbriqués | P — champs Int exercés ; relais Execution concret couvert par le lot suivant |
| RT5, D1/D3 | Une capacité du handle ne devient pas deux prêts ; prêts indépendants protégés | Deux fautes de double comptage détectées, deuxième capture et drop prématuré refusés | P — graphes testés, pas preuve générale |
| B4d, PR1 | Les sources du résultat traversent les contrats | Relations exigées, appelant sans corps, pool disjoint admis et cible refusée | P — reset historique seulement ; mutation de résolution concrète survivante |


Dernier lot : [fabriques synchrones de handles dans les états](cycles/SYNC_HANDLE_BRIDGES_CYCLE.md).
Seize méthodes ciblées réussies à O0/O2 ; modèle indépendant de 32 cas ; six
mutations détectées. Régressions O2 de 73, 24 et 19 méthodes, avec leur chronologie
dans le rapport. L’attente d’une fabrique directe et la réception nommée sont
raccordées. Les projections de champs du résultat restent ouvertes.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12, B1/B2/B5, D1/D3 | Captures requises jusqu’à attente ; seules les cibles du résultat après | Modèle 32 cas, deux relais, vues et références Int, mutations des deux groupes | P — paramètres directs, pas projections de champs |
| RT4/RT5/RT8, AS8 | Attente suspendable d’un handle produit en code sync | Trois lancements, attente directe/nommée, sept niveaux async et douze reprises du programme | P — cas finis, pas preuve générale d’équité |
| RT6/RT7, L1/L2 | Ressources transférées une fois et nettoyage avant erreur/réemploi | Contrat C à quatre états, injection de refus, capacité un, mutations du détachement/erreur/consommation | P — pas nouvelle preuve ASan/TSan |
| U1, RT5/RT7 | Résultat explicite et attente unique, aucun abandon | Drop, sortie anticipée, double attente et résultat abandonné refusés ; 19 régressions usage/attente | P — signatures testées |


Lot précédent : [vues des auxiliaires synchrones dans les états](cycles/SYNC_VIEW_BRIDGES_CYCLE.md).
Douze méthodes couvertes par onze passages groupés et un complément natif,
à O0/O2 sous UBSan ; modèle indépendant de 32 scénarios, cinq mutations
détectées. Régression élargie : 99 méthodes O2, avant le dernier contrôle U1
couvert par les passages ciblés finaux et 23 méthodes de régression U1/UTF-8. La fabrique publique de handle appelée
depuis un état reste ouverte ; les types de vues directs ci-dessous sont raccordés.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| B1/B2/B4/B5, AS2/AS8 | Prêts préparés protégés pendant les arguments suivants et les suspensions | Ordre observable, mutation d’un argument refusée, indice suspendu, mutation détectée | P — vues directes et projections textuelles exercées |
| AS12, D1/D3, RT5 | Résultat garde ses cibles, libère les captures sans lien après join | Deux relais, modèle 32 cas, sous-vues et thread natif ; mutations de prêts/contrats | P — signatures de vues listées dans le rapport |
| U1 | Résultat faillible explicitement utilisé | Appel abandonné, liaison inutilisée et `_` refusés ; drop admis ; mutation détectée | P — auxiliaire retournant Result<&str,SliceError> |
| L1/L2, AS10 | Retour anticipé d’argument nettoie une fois et empêche l’appel | Trace destroy puis reclaim et absence du marqueur de l’auxiliaire | P — scénario String local |


Lot précédent : [contrats publics de handles à résultat vue](cycles/PUBLIC_VIEW_HANDLES_CYCLE.md).
Signatures synchrones pour &str, &u8, &[Int/u8], &mut [Int/u8] et
Result<&str,SliceError>. Dix méthodes O0/O2 réussies, modèle indépendant de
32 scénarios, appelant opaque et échecs de lancement injectés. Douze méthodes
async préexistantes et 132 méthodes de régression élargie passent à O2.
Quatre mutations détectées et une survivante
(capacité exclusive également conservée dans le descripteur du prêt).
Le rapport distingue les passages ciblés, les régressions et les limites.
Les anciennes mentions de vues publiques entièrement ouvertes sont remplacées
pour ces formes synchrones seulement.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12, RT5, MT5/MT6, D1/D3 | Résultat garde ses cibles ; captures temporaires libérées après attente | Modèle 32 cas, deux frames, relais, appelant sans corps | P — signatures synchrones listées, agrégats généraux ouverts |
| B1/B2/B5, TX4/TX5/TX12 | Modes et origines des vues après join | String, tableaux u8, tranches Int/u8, readonly, réemprunts et derniers usages | P — mutation de capacité survivante, pas de preuve générale |
| B4d, PR1 | Sources distinctes si reset historique avant lecture | Deux relais plus conversion concrète/publique, obligation contrôlée et mutation détectée | P — profil historique uniquement |
| RT6, L1/L2 | Échec de lancement nettoie les captures avant résultat | Injection d'échec, traces et résultats de secours | P — chemins exercés sous UBSan O0/O2 |


Arbitrage en attente : [capture async d'un handle déjà lancé](ASYNC_HANDLE_CAPTURE_DECISION.md).
AS14 permet de détruire l'instance inactive ; RT6 détruit ses captures en cas
d'échec de lancement ; RT7 interdit de détruire ou d'attendre implicitement
le handle capturé. Les deux programmes minimaux et le refus actuel du backend
sont conservés. Aucun nouveau comportement normatif n'est choisi avant réponse.

Lot indépendant : [expressions calculées dans set](cycles/SET_EXPRESSIONS_CYCLE.md).
Neuf méthodes ciblées O0/O2, modèle indépendant de 36 mutations Int et trois
fautes injectées détectées. Les appels dans la RHS contribuent aux contrats ;
la cible est revérifiée avant écriture. La régression initiale de 150 méthodes
retrouve six fixtures U1 anciennes : les mêmes trois échecs d'assertions et
douze erreurs sont reproduits avec les sources du compilateur avant ce lot.
Les scénarios sont corrigés en lisant explicitement l'ancienne valeur, sans
retirer leurs assertions de destruction, d'identité ou de refus.
La deuxième passe réussit 149 méthodes sur 150 ; le dernier scénario négatif
est corrigé pour utiliser aussi son nouveau receveur. Les 41 méthodes des
deux modules modifiés passent ensuite. Chronologie complète dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| V4/B4a | Calcul Int complet avant écriture, identité inchangée | Appels ordonnés, copie scalaire, tableau, match, adresse et réemploi | P — expressions Int déjà supportées |
| B1/B2/B3, D1 | Cible vivante et accessible après RHS | Drop, transfert, lecture future et readonly refusés ; dernier usage admis | P — chemins exercés, pas de preuve générale |
| B4c/B4e, L6, PR1 | Effets de RHS propagés dans les contrats | Deux relais, reset historique disjoint admis/dangling refusé ; mutation d'effet détectée | P — reset uniquement par option historique |

Dernier lot : [handles à résultat emprunté](cycles/PUBLIC_BORROWED_HANDLES_CYCLE.md).
Contrats synchrones publics pour &Int, &mut Int et &mut u8 ; captures actives
séparées des cibles du résultat, relais et appelants opaques, projections de
champs et de cases. Dix méthodes passent à O0/O2, modèle indépendant de
32 scénarios ; cinq mutations détectées, une survivante dans la campagne finale.
Régression de 97 méthodes O2 réussie avant les derniers compléments octets,
couverts par les tests ciblés finaux, 122 méthodes tableaux/octets/vecteurs
et 36 méthodes de contrats publics à O2. Les projections inline partagées
ajoutées ensuite passent leur complément ciblé O0/O2.
Chronologie, journaux initiaux et limites dans le rapport. Les mentions
historiques de charges empruntées entièrement ouvertes sont remplacées pour
ces trois formes seulement ; les signatures async restent ouvertes.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| AS12/AS13, RT5, MT5, D1 | Cibles du résultat conservées après join, autres captures libérées | Deux relais, auxiliaire d'attente, deux branches, modèle 32 scénarios, appelants sans corps | P — trois signatures empruntées synchrones |
| B1/B2/B5, ST11–ST14, MT3 | Capacité mutable d'origine retenue, cible détachable distinguée du porteur | Drop/accès prématurés refusés, dernier usage, champs stockés, capture directe ; mutation de capacité détectée | P — graphes exercés, pas tous les agrégats |
| B4a, VE1/VE3, E1, AS2 | Case Int/u8 stable et bornée, réservée pendant l'évaluation de l'indice | Tableaux/vecteurs, helper octet, readonly, croissance et transfert interdits, dépassement runtime | P — mutation de source dans les contraintes survivante ; contrôles backend conservés |
| L1/L2, RT6, P8 | Nettoyage puis réemploi, erreur de lancement après fin de tâche | Traces, pools réemployés, refus de lancement, O0/O2 UBSan | P — pas de nouvelle preuve ASan/TSan ou formelle |

Lot précédent : [handles à résultat alloué](cycles/PUBLIC_OWNED_HANDLES_CYCLE.md).
Contrats synchrones Handle<A<T>> pour Int, String et Vector<Int/u8>,
résultats alloués faillibles, sources des captures séparées des sources du
résultat, jonctions et appels opaques. Neuf méthodes O2 réussies ; modèle
indépendant de 32 scénarios et cinq mutations détectées. Régression de
104 méthodes O2 réussie ; les neuf méthodes ciblées passent aussi à O0.

| Règles | Invariant / interactions | Preuves de l'étape | Statut / limites |
| --- | --- | --- | --- |
| RT5 / MT5 / AS13 / D1 / D3 | Les pools du résultat survivent après join, les autres captures sont libérées | Deux relais, auxiliaire d'attente, pool de secours, appelants opaques, modèle 32 scénarios | P — quatre contenus alloués, signatures sync |
| RT6 / T6 / U1 | Résultat et erreur distincts, consommation explicite et nettoyage unique | Deux niveaux d'erreur, lancement refusé, adresses avant/après transfert et réemploi, refus de mauvais A<T> | P — enveloppes exercées, pas tous les agrégats |

Lot précédent : [contrats publics des handles](cycles/PUBLIC_HANDLE_CONTRACTS_CYCLE.md).
Paramètres et retours synchrones Handle à charge scalaire ou tableau fixe
Int/u8, captures et sources conservées sans corps disponibles à l'appelant.
17 méthodes ciblées O0/O2, régression de 54 méthodes et sept mutations détectées.
Le modèle de permissions couvre 36 scénarios. Les jonctions de frames distinctes
par if/loop/match passent cinq méthodes ciblées et quatre mutations ; passes
communes finales : 22 méthodes O0 et 60 O2. Les 18 tests de résultats de boucle
passent ; une sélection historique supplémentaire a révélé des fixtures
sans usage explicite U1, corrigées avec assertions conservées : 71 méthodes
réussissent à la relance. Signatures async et
charges empruntées/propriétaires restent ouvertes. Détail et chronologie dans le rapport.

| Règles | Invariant / interactions | Preuves de l'étape | Statut / limites |
| --- | --- | --- | --- |
| RT5 / MT5 / brouillon 04 | Type public indépendant de la frame, contrat sans corps | Fabriques, relais, deux frames, formes de tableaux et mauvais types refusés | P — signatures synchrones, charges prises en charge |
| AS2 / AS13 / MT3 / RT7 | Captures et pools vivants jusqu'à attente, obligation transférable | Modèle 36 cas ; appelants opaques ; drop et accès anticipés refusés ; mutations | P — captures testées, graphes généraux ouverts |
| D1 / RT6 / E1 | Nettoyage unique, tableau détaché, réemploi du stockage | Refus de lancement, drop après attente, réemploi des slots, O0/O2 UBSan | P — pas de preuve générale ni TSan |
| D3 / T6 / S5 / MT5 | Jonctions de handles : même charge, union des captures et des pools | if, loop/continue, trois matchs ; 22 exécutions C, contrats opaques, quatre mutations | P — charges scalaires/tableaux prises en charge ; corps async ouverts |

Lot précédent : [type public des handles](cycles/PUBLIC_HANDLE_TYPES_CYCLE.md).
Annotations `runtime::Handle<T>` sync/async, transferts calculés et variantes
de lancement. Régression voisine : 50 méthodes réussies ; trois mutations
détectées. Les signatures génériques restent ouvertes, avec un contre-exemple
source conservé. Les journaux ciblés finaux O0/O2 sont indiqués dans le rapport.
Sept méthodes passent à O0/O2 : 29 exécutions C et 35 variantes invalides
contrôlées aux deux entrées par passage complet.

| Règles | Invariant / interactions | Preuves de l'étape | Statut / limites |
| --- | --- | --- | --- |
| Brouillon 04 / RT5 | Le type public décrit le résultat, pas la frame | Six charges dans deux contextes ; deux fonctions différentes produisant Int ; mauvais types refusés | P — annotations locales ; signatures génériques ouvertes |
| AS2 / AS13 / MT3 / RT7 | L'annotation n'efface ni capture, ni source, ni attente | Drop et accès prématurés refusés, résultats empruntés/alloués, réemploi ; mutation d'effacement détectée | P — familles exercées, pas tous les agrégats |
| D1 / RT4 / RT8 | Les transferts et lancements gardent leur comportement | Bloc, if, boucle, rename, spawn/blocking/thread, essais C | P — jonctions entre définitions différentes encore ouvertes |

Lot précédent : [notifications des attentes async](cycles/AWAIT_NOTIFICATIONS_CYCLE.md).
RT2/AS4 : inscription du parent, transmission du ticket dans les attentes directes,
notification par les workers coopératifs, dédiés et natifs. Tests ciblés O0/O2,
200 ordres imposés, 200 réemplois sur deux workers et vingt chaînes générées.
Sept mutations spécifiques détectées, six de file et six de frontière native.
Les régressions élargies passent : 275 méthodes async et 311 natives.
Elles précèdent le dernier correctif d'association d'entrée et le test
concurrent, couverts séparément ; voir le rapport pour la chronologie.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS4 | Attente inscrite endormie, réveil de toute la chaîne | Programme généré avec tableau et emprunt local, compteurs de polls, vingt réemplois | P — un consommateur par handle ; Select ouvert |
| RT2 / AS8 / MT7 | Pas de réveil perdu entre inscription, poll et fin | Quatre ordres, deux voies de fin, 200 reprises concurrentes ; mutations | P — ordonnancements exercés, pas de TSan ni preuve formelle |
| RT2 / AS14 | Fin visible après notification, libération unique | Publication intermédiaire forcée, compteurs de libération, tickets obsolètes | P — contexte durable requis ; boucle du runner dédié conservée |

Lot précédent : [file prête et workers réutilisés](cycles/READY_QUEUE_CYCLE.md).
RT2–RT4/RT8 : entrées générées hors des frames, tickets générationnels,
file FIFO, deux workers par défaut réutilisés, voie bloquante et native séparées.
Neuf méthodes ciblées passent à O0 ; baseline de cinq méthodes à O2 et six
mutations de file détectées. Modèle indépendant : 40 scénarios, 5 440 opérations.
La régression native initiale termine avec 308 méthodes et seize échecs
d’injections pthread devenues inadaptées à la réutilisation des workers.
Les attentes de résultats sont conservées et les injections migrées vers les
soumissions logiques. La campagne async termine avec 275 méthodes : 273 réussites
et deux injections anciennes chargées avant correction, réexécutées avec succès
séparément. Les deux méthodes hors du module async qui avaient échoué sont
également réexécutées avec succès. Les journaux initiaux conservent leurs échecs.
Une sixième méthode force la migration d’une frame générée portant un emprunt
local et une attente d’enfant ; elle passe à O0/O2. Chronologie dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS8–AS9 | Une entrée planifiée, réveils regroupés, FIFO et workers réutilisés | Modèle deque, compteurs de polls, huit tâches et trois workers, six mutations | P — pas de preuve des ordonnancements OS ; attentes générées encore en Yield |
| RT2 / AS7 / MT7 | Ancien ticket sans accès à une frame libérée/réutilisée | Générations, vingt réemplois, producteur après free ; entrées générées par emplacement | P — les producteurs doivent cesser avant destruction de leur contexte |
| RT4–RT6 / AS14 | Refus de lancement après nettoyage ; pool réutilisable | Refus du deuxième worker et de la condition, trois tâches successives et traces | P — erreurs OS choisies, pas toutes les défaillances système |
| RT4 / RT8 | Bloc natif indépendant, opérations bloquantes hors workers coopératifs | Tests natifs et spawn_blocking ; mutations de la frontière native | P — remplacement public du scheduler encore ouvert |

Lot précédent : [réveils du runtime](cycles/TASK_WAKES_CYCLE.md).
RT2 : distinction interne Pending/Yield, permission de poll coalescée,
conservation des réveils pendant le corps et exclusion des polls concurrents.
Quatre méthodes passent à O0/O2 ; modèle indépendant de 2 401 séquences
(9 604 transitions), vingt essais de concurrence/migration et deux cents
courses réveil/publication. Six mutations du protocole sont détectées.
La régression native passe : 302 méthodes, 312,219 s. La campagne async initiale
termine avec 278 méthodes, 276 réussites et deux attentes de tests corrigées
puis réexécutées ; ses échecs restent visibles dans le rapport. RT2 demeure
partielle : ni files du scheduler ni inscriptions de réveil publiques dans ce lot.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| RT2 / AS8–AS9 | Un seul corps actif ; réveils pendant un poll conservés et regroupés | `test_task_wakes.py`, modèle fini, courses et six mutations | P — protocole C interne ; files, équité et API publique encore ouvertes |
| RT2 / AS4 / MT8 | Reprise sur un autre thread à adresse stable | Vingt essais avec premier thread encore vivant | P — migration exercée au niveau runtime ; aucune garde de mutex couverte |
| RT4–RT6 / AS14 | Résultat extrait avant libération, nettoyage unique | Lancement joinable/détaché après Pending ; mutations de la frontière native | P — durée de vie des pointeurs de réveil assurée par le harnais ; inscriptions futures non gérées |
| V4 / AS12 | Une liaison immutable de référence mutable peut écrire sa cible | Fixture historique corrigée selon V4, échec reproduit avec l’ancien runtime ; programme exécuté | P — pas de changement normatif ni de généralisation aux réaffectations |

Lot précédent : [stockage des réemprunts de champs](cycles/STORED_FIELD_REBORROWS_CYCLE.md).
ST4/ST8/ST11–ST14, B1–B5, D1 et AS12/AS13 : représentation de la véritable
allocation conservée par les références indirectes, ascendance réservée dans
les porteurs et les résultats. Quatorze exécutions C (dont un lancement refusé),
28 programmes refusés aux deux entrées ; six mutations ciblées détectées.
Modèle indépendant : seize combinaisons, dix exécutions et six refus.
Régression des contrats : 35 méthodes réussies ; champs historiques :
75 réussites et une fixture U1 corrigée puis réexécutée séparément.
Le contre-exemple `open-struct-field-reborrow-stored-shared.crust` est corrigé.
La campagne finale de helpers détecte aussi ses six fautes après ajout du
voisin inline ; une mutation antérieure des retours de champs reste survivante.
Régression native élargie : 297 méthodes réussies en 226,611 s. Les derniers
compléments sont couverts par les passages ciblés ; chronologie dans le rapport.

| Règles | Invariant / interactions | Preuves du lot | Statut / limites |
| --- | --- | --- | --- |
| ST4/ST8/B5 | Le champ stocké et retourné garde sa cible et son type | Construction partagée/mutable, helper, méthode, fabrique, copie ; mutations de représentation et d’origine | P — références vers allocations Int ; stockage inline général ouvert |
| ST11/ST12/D1/AS13 | La capacité originale survit à tous ses réemprunts | Drop/reset historique, sortie de bloc, résultat async/natif, chaînes d’enums ; modèle 16 cas | P — modèles finis ; mise à jour des champs async ouverte |
| ST13/ST14/B1/B2/AS12 | Portée du porteur partagée distincte de la capacité mutable originale | Join, handle reçu, résultats mixtes, mutation indépendante ; mutation d’ascendance désormais détectée | P — graphes exercés, pas tous les agrégats |
| L1/L2/L6/P8/AS14 | Nettoyage unique et réemploi après dernier usage | Trace View → Writer → Int, EAGAIN injecté, pool original de capacité un réemployé | P — UBSan, pas de résultat ASan/TSan ajouté |

Lot précédent : [retours partagés détachés](cycles/ASYNC_DETACHED_FIELD_RETURNS_CYCLE.md).
ST13, ST11/ST12/ST14, B1–B5, D1, AS12/AS13 et MT3 : la cible extérieure
survit à la destruction du porteur ; le champ mutable conserve sa capacité.
Couverture partielle : 27 exécutions C (dont un lancement refusé injecté),
32 programmes refusés aux deux entrées, modèle indépendant de douze cas
(huit exécutions/quatre refus). Quatre mutations détectées, deux survivantes
sans équivalence générale établie. Ciblé final O0 : treize méthodes réussies ;
régression voisine O2 : 61 méthodes réussies avant les derniers ajouts de tests.
La régression native élargie termine avec 291 méthodes réussies en 239,123 s.
Les ajouts finaux d’ascendance et de traces de destruction ont aussi leurs
passages ciblés ; voir le rapport pour la chronologie exacte.
Le stockage d'un réemprunt de champ mutable, alors refusé à tort, est traité
dans le lot suivant ci-dessus.

| Règles | Invariant et interactions | Preuves du lot détaché | Statut / limites |
| --- | --- | --- | --- |
| ST13/B5/AS12 | Le résultat partagé conserve sa cible extérieure sans retenir le porteur | Retour direct, alias, helper, méthode, enfant, relais après join ; pool du porteur fermé/réemployé | P — champs &Int ; autres graphes ouverts |
| ST11/ST12/ST14/B1/B2 | Le champ direct et la capacité mutable gardent leurs réservations | Résultats mixtes, destruction et mutation prématurées refusées, réemprunt partagé mutable valide | P — union conservative des chemins ; mutation de capacité antérieure survivante |
| B3/D1/AS13/MT3 | Cible et ancêtres durables jusqu’au dernier usage | Drop/reset historique, ancêtre mutable, résultat de bloc local refusé ; modèle 12 cas | P — deux mutations du lot survivent ; stockage d’un réemprunt de champ encore ouvert |
| L1/L2/L6/P8/AS14 | Destruction puis récupération, une fois ; réemploi du slot | Traces exactes, capacité un, erreur de lancement injectée | P — chemins finis sous UBSan |

Lot précédent : [contrats mixtes sync/async](cycles/ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md).
B4c/B4e, ST8/ST12/ST14, AS12/AS13 et MT3 : résumés des helpers disponibles
pendant l'inférence async, chemins conservés par les fabriques de handles
et les fonctions qui attendent un handle reçu. Couverture partielle : neuf
exécutions C et quinze programmes refusés aux deux entrées ; modèle de 24 cas
(18 exécutions/six refus) ; six mutations détectées. Régression de 67 méthodes
avec une fixture U1 préexistante corrigée puis réexécutée séparément, et
56 méthodes de champs réussies. Les limites, profils et journaux en échec
restent détaillés dans le rapport. Aucun énoncé général de sûreté.
La sélection native de 278 méthodes a également terminé avec succès ; elle
précède le dernier complément sur le paramètre handle, couvert par les
passages ciblés finaux.

Complément suivant : [retours de champs async](cycles/ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
Mise à jour finale du lot : contrats des relais synchrones après join et
ascendance raccordés ; baseline de 23 exécutions C et 58 programmes refusés
dans deux stages ; sept mutations détectées, une survivante. Régression native
de 269 méthodes puis complément final de 42 méthodes réussis (périmètres et
chronologie explicités dans le rapport). Aucune preuve générale de sûreté.
ST8/ST12/ST14, AS12, B1/B2 et MT3 : les contrats restituent les chemins Int
directs et &mut Int réempruntés, y compris après relais, branches et join.
Champs disjoints accessibles, porteur et cible protégés jusqu'au dernier usage.
Couverture partielle : modèle indépendant de 24 cas (18 exécutions/six refus),
baseline de 21 exécutions et 50 programmes invalides contrôlés dans deux stages,
cinq mutations détectées et une survivante (protection transitive redondante
dans les cas exercés ; équivalence générale non établie). Un complément de
recapture ajoute une exécution et quatre refus. ST13 détaché et graphes plus
généraux restent ouverts. Voir le rapport pour les erreurs conservées,
les configurations et la régression élargie.
Le relais synchrone d'un join dont l'enfant async retourne un résultat de
helper synchrone reste refusé ; contre-exemple conservé dans
`validation/open-async-helper-result-sync-contract.crust`.

Complément précédent : [réemprunts de champs async](cycles/ASYNC_FIELD_REBORROWS_CYCLE.md).
ST6–ST9/ST11–ST12, B1/B2/B4a et AS12/AS13 : couverture partielle des chemins
de champs, aliases durables, arguments préparés et résultats d'auxiliaires
synchrones. V4 : mutation via une liaison immuable de &mut autorisée ; sa
réaffectation reste refusée. Modèle indépendant de 32 cas, baseline finale
de 21 exécutions C et 29 programmes refusés dans deux stages, sept mutations
détectées. Régressions de 256 et 76 méthodes réussies ; voir le rapport pour
la chronologie du dernier changement. Le retour projeté depuis une fonction
async elle-même et la modification des dépendances de champs restent ouverts.

Référence normative : [LANGUAGE_RULES.md](LANGUAGE_RULES.md). Inventaire du
2 novembre 2026, établi après lecture de l'ensemble des règles. Les 67 identifiants
ci-dessous viennent de cette spécification ; aucun nouvel énoncé normatif n'est
introduit ici. Une modification de règle demande de réexaminer ses dépendances.

Complément async : AS1–AS16, RT1–RT8, MT1–MT9, SL1 et PR1 sont inventoriés
en fin de document. Leurs lignes précisent la couverture partielle actuelle ; l'inventaire historique
des 67 identifiants ci-dessus n'inclut pas cette extension. Les lignes et preuves
historiques concernant A5/reset décrivent encore l'ancien comportement : elles
ne vérifient pas le retrait d'API décidé par PR1.

Cette matrice distingue **P** (couverture partielle par tests exécutables),
**A** (examen de conception/spécification, sans preuve exécutable dédiée) et
**N** (comportement visé non implémenté, non vérifié). Aucune règle n'est déclarée
prouvée formellement ni entièrement vérifiée. Le résultat du cycle des types de pools est
dans [POOL_REQUIREMENTS_VALIDATION.md](POOL_REQUIREMENTS_VALIDATION.md). Le cycle des champs
&Int est détaillé dans [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md).

Chaque ligne hérite du profil indiqué : il donne les exemples admis/refusés,
les invariants, les préconditions communes, assertions runtime, modèles,
mutations et limites. La colonne interactions ajoute les dépendances propres
à la règle. Les restrictions par ligne prévalent sur le profil. Une suite
référencée n'est pas une couverture exhaustive de chaque variante de la règle.

Préconditions des profils synchrones historiques : fonctions sans récursion,
Int32 et enums à champs Int/&Int/&mut Int, sans destructeur utilisateur,
provenances finies et sources non déplaçables. Les sources `allocator()` et
`stack(...)` restent des backends explicites de compatibilité, sans fallback
silencieux ; les nouveaux cas de ce cycle privilégient les pools.

| Règle | Comportement attendu / invariant protégé | Profil | Interactions | Statut et limite particulière |
| --- | --- | --- | --- | --- |
| I1 | Intention explicite des opérations mémoire | INTENT | I2,T1,B4,L6 | P — sources et opérations couvertes seulement |
| I2 | Stockage local implicite et pool nommé pour les allocations de pool | INTENT,POOL | V1,A1,P8 | P — pool typé et littéraux de structures locales exercés. Mutation après dernier emprunt, drop et champ propriétaire cross-pool testés à O0/O2. Placement des transferts locaux, autres valeurs locales et retrait des syntaxes historiques à intégrer. [Cycle stockage](cycles/STORAGE_DESIGN_CYCLE.md) |
| I3 | Calcul du stockage sans réordonner les effets | STORAGE | B4a,L3,P3 | P — placement anticipé général non implémenté |
| I4 | Valeurs par défaut déclarées localement | FUTURE | P2 | N — configuration locale non définie |
| I5 | Noyau minimal inspiré de Rust, règles Crust prioritaires | DESIGN | I1,B4 | A — choix de conception, pas équivalence à Rust |
| S1 | Blocs délimités par accolades | INTENT | S4,T4 | P — grammaire actuelle seulement |
| S2 | Exécution synchrone | DESIGN | S3,S4 | A — threads et async hors périmètre |
| S3 | Activation enfant du scope appelant | CALLS | S5,T3,T4 | P — appels non récursifs ; récursion différée |
| S4 | Scope propre aux branches et itérations | FLOW,LOOP_CARRY | S5,T9,L2 | P — loop/while/if ; pas for |
| S5 | Nettoyer exactement les scopes quittés | FLOW | T3,L2,L3 | P — return/break/continue sans labels |
| S5a | Résultat de loop et nettoyage avant sortie ; types, modes et durabilité | LOOP_RESULT | S5,T6,T11,V4,D1,B2,A3 | P — aucune valeur de while ; labels absents |
| S6 | main sans paramètre, sortie Void/Int et nettoyage | ENTRY | S5,L2 | P — mode script conservé |
| V1 | Le transfert explicite conserve le type local `T` ou le type de pool `A<T>` | INTENT | T1,T2,T6,P3 | P — transfert de `A<Point>` et de structures locales dans des blocs imbriqués et les deux branches de if exercé. Adresse conservée, temporaires nettoyés et dépendance locale trop courte refusée. Réaffectations entre T local et A<T> refusées. Break terminal et breaks dans les branches if après continue exercés, avec réemploi après drop dans le cas terminal. Retours locaux directs de fonction, conditionnels et finaux, exercés avec emplacement fourni par l’appelant. Relais de résultats locaux par deux fonctions et un bloc exercé, y compris avec dépendance empruntée. Construction avant continue exercée avec champ propriétaire et réservation réutilisable. Return Int avant et après construction à travers une réservation de boucle exercé. Retour direct de la structure réservée à travers une boucle instruction ou expression exercé avec reprises. Autres formes syntaxiques de résultats à intégrer. [Cycle stockage](cycles/STORAGE_DESIGN_CYCLE.md) |
| V2 | Initialisation complète avant usage | ENUM | B4a,P9 | P — champs Int/&Int/&mut Int ; emprunts nommés, capacité contrôlée |
| V3 | Copies implicites limitées aux builtins copiables | INTENT | V1,B4 | P — Int seulement dans le prototype |
| V4 | let immutable / let mut ; mutation Int sans allocation, remplacement après RHS | ASSIGN,LET_MUT | B1,B2,B4,L6,A5,P8 | P — Int et modes existants ; expressions Int dans .set (SET_EXPRESSIONS_CYCLE.md), pas de collections. En async, receveur Int détenu remplacé par déplacement, await, bloc, if et boucle à résultat. Conservation d’identité et dernière lecture de l’ancien contenu exercées, y compris avec une vue déclarée deux blocs plus haut. Un usage ultérieur dans chaque bloc ou par une tâche conserve la protection. Chaque bras d’un if instruction ou à valeur peut terminer le prêt séparément. Exercices complémentaires avec match à valeur et bloc à transfert. Une lecture après la jonction ou dans un argument évalué ensuite préserve la protection. Un remplacement sur un chemin qui mène à un break direct peut terminer le prêt, y compris depuis un bloc enfant et avec plusieurs instructions avant le break. Les usages intermédiaires, la valeur du break, la continuation après la boucle et les reprises conservent la protection. Affectations imbriquées propagées à la sortie des blocs et réunies sur les chemins continuants des branches. Réaffectation d’un receveur de boucle exercée sur continue, fin normale et break. Provenances de boucle réunies sur les reprises jusqu’à stabilisation, puis propagées à la sortie par break ou condition fausse. Exercice avec deux pools possibles et un troisième pool exclu. Repli conservateur si un effet reste non résolu. |
| V5 | Adresse stable jusqu'à fin de vie | STORAGE | T11,L7,P8 | P — stabilité des allocations fixes et des éléments de collections grandissantes exercée ; voir G12 et les tests de croissance |
| T1 | Pas de transfert implicite par affectation | INTENT | I1,B4 | P — syntaxes de transfert implémentées seulement |
| T2 | Move local invalide l'ancien accès sans nouvelle réception | TRANSFER | L3,B3 | P — pas de déplacement de sources. Renommage async testé avec conservation de l’ordre de destruction, y compris après import et sortie anticipée. |
| T3 | Transfert montant au bilan vers parent direct | TRANSFER | S5,A3 | P — marquage valide jusqu'à sortie, sauf consommation |
| T4 | Transfert descendant à l'entrée vers enfant direct | TRANSFER | T8,B3 | P — imports explicites seulement. Le retour d’un import réinscrit sa destruction dans le parent en async. |
| T5 | Traverser les scopes intermédiaires | TRANSFER | T3,T4,A3 | P — profondeurs bornées dans les tests |
| T6 | Retour et receveur explicites, identité sans ancien alias | TRANSFER | U1,T2,B4c | P — objet remplacé reçu explicitement, sans réactiver l’accès importé ; let <- suivi du nom final vérifié dans bloc, if et fonction, adresse stable, refus d’un pool local et avertissement sans receveur |
| T7 | Destination ancêtre sans promotion implicite | TRANSFER | I1,T5 | P — blocs et jonctions compatibles, y compris sorties et reprises de boucle. 818 tests de régression, 14 ciblés sous UBSan et deux mutations détectées. [Jonctions conditionnelles](ANCESTOR_JOIN_VALIDATION.md), [cycle des boucles](LOOP_REPLACEMENT_VALIDATION.md) |
| T8 | Retour garanti avant réutilisation d'un import | FLOW | T4,T9 | P — restitution après remplacement contrôlée par révision du handle ; ordre de réception compatible requis |
| T9 | Validité sur tous les chemins qui continuent | FLOW | S5,T11,L2 | P — analyse conservative, pas tous les prédicats |
| T10 | if expression reçoit un Int copiable ou une allocation ; type et mode communs | FLOW,LOOP_RESULT | T6,U1,T11,V4 | P — résultats empruntés synchrones et retours terminaux async exercés ; voir REFERENCE_EXPRESSIONS_CYCLE.md et ASYNC_REFERENCE_RETURNS_CYCLE.md |
| T11 | Toutes provenances protégées, nettoyage de la vraie source | PROVENANCE | A5,P9,L6 | P — ensembles finis ; champs &Int, sans graphes transitifs |
| U1 | Usage explicite du résultat reçu requis, y compris les résultats faillibles sans allocation | INTENT | T6,B4c,F5,L6 | P — usages conditionnels et transmission admis ; abandon, `_`, liaison inutilisée et écrasement direct refusés pour les résultats inline testés, sync/async. Mutation du contrôle détectée. Usage possible, pas exécution garantie ; familles propriétaires et jonctions à compléter. Le contournement par await sur une tâche choisie par if est corrigé, testé à O0/O2 et détecté par mutation (UTF8_TRY_SLICE_CYCLE.md). INTEGER_CONVERSIONS_CYCLE.md Complément brouillon 01 : contrôles de motifs propriétaires et consommation explicite, O0/O2, emprunts et réemploi ; trois mutations détectées. Couverture partielle et contre-exemples encore ouverts dans [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). Réceptions ordinaires et await, renommages, remplacements et continuations contrôlés ; 21 méthodes dédiées à O0/O2 avec UBSan fatal, 154 régressions synchrones et 37 async/UTF-8 réussies, modèle indépendant de 64 cas et cinq mutations détectées. Couverture toujours partielle : [U1_RECEIPTS_CYCLE.md](cycles/U1_RECEIPTS_CYCLE.md). |
| D1 | Cibles déjà durables à chaque frontière, aucune promotion implicite | RETURN_FIELD | I1,T3,T5,D2,D3,A3 | P — cibles &Int/&mut Int ; graphes généraux non implémentés |
| D2 | Suivre les références sans prolonger les cibles | FIELD | D1,D3 | P — champs &Int/&mut Int ; graphes transitifs non implémentés |
| D3 | Retenir toutes les dépendances possibles | PROVENANCE | T11,D4 | P — ensembles finis de sources et cibles &Int/&mut Int ; graphes généraux futurs |
| D4 | Aucun accès à une valeur/stockage invalidé | BORROW | A2,T9,L6 | P — preuves bornées, aucune preuve générale de sûreté |
| B1 | Lectures partagées ou mutation exclusive | BORROW | B2,B3,B4a | P — références directes et champs partagés et exclusifs (MUT_FIELD), projections mutables limitées au bras (MUT_MATCH) |
| B2 | Fin d'emprunt après dernier usage | BORROW,LOOP_CARRY | V4,B3,L2,L6 | P — analyse conservative des chemins. [Dernier usage d'un champ sur une reprise](LOOP_DEAD_FIELD_VALIDATION.md) |
| B3 | Pas de move avec emprunt encore utilisé | BORROW | T2,L6 | P — retours &Int couverts par RETURN_REF |
| B4 | Modes explicites et types de paramètres préservés | POOL | B4a,P8 | P — pools read/mut ; emprunts existants par nom (REF_VALUE), capacité runtime |
| B4a | Arguments évalués de gauche à droite et protégés | ARGS | B1,A5,V4 | P — sources nommées, expressions du sous-ensemble ; reset dans un argument suivant vérifié par contrat avec tableaux de références copiés, empruntés et imbriqués |
| B4b | Résumés de sources propagés sans effet local exporté | POOL | B4,B4e,P8 | P — graphe d'appels non récursif |
| B4c | Origines et restitutions d'identité du résultat | RESULT | T6,T11,L7 | P — pas de référence retournée |
| B4d | Égalités de drop et distinctions après reset | CONSTRAINT | A5,L6,T11 | P — pas de solveur général de types/provenances |
| B4e | Vérifier chaque corps, appels par contrats opaques | POOL | B4b,B4c,B4d | P — backend encore spécialisé ; pas de preuve du C |
| B5 | Emprunts retournés valides pendant leur usage | RETURN_REF | D1,D3,B1,B2,B3,B4a,A3,A5,L6 | P — &Int et &mut Int ; autres types non implémentés |
| L1 | Destruction avant récupération du stockage | CLEANUP | L2,L6,P4 | P — destructeurs démonstratifs et champs propriétaires. Cellules hétérogènes du runtime exercées avec un champ détenu cross-pool, préfixe vivant et réemploi. Deux mutations de nettoyage et de recul détectées à O0/O2. Raccordement des structures locales au compilateur restant. [Cycle stockage](cycles/STORAGE_DESIGN_CYCLE.md) |
| L2 | Nettoyage unique dans le scope final | CLEANUP | S5,T3,A6 | P — arrêt sur échec sans déroulement |
| L3 | Ordre inverse de création/réception, ordre physique distinct | CLEANUP | T2,T9,P8 | P — ordres de réception incompatibles refusés. En async, groupe descendant et renommage local exercés. Réception d’un retour descendant en fin de bloc, sur break et dans les branches exercée. Les ordres incompatibles entre branches et sur une reprise sont refusés. Le C async sélectionne l’ordre des captures selon le chemin de retour, exercé sous UBSan avec restitution, retour anticipé, drop inactif et échec de lancement. Ordre combiné vérifié après restitution d’une capture et réception d’un Int par await. Les nettoyages terminaux suivent le même ordre lexical dans le callback de libération après extraction. |
| L4 | Dépendances des destructeurs encore vivantes | FUTURE | D1,D2,L3 | N — destructeurs utilisateur et cycles non implémentés |
| L5 | Nettoyage anticipé seulement si effets préservés | FUTURE | L1,L3 | N — mode d'optimisation de destruction non implémenté |
| L6 | `drop(-> x)` consomme la liaison et respecte les emprunts et provenances ; drop(-> expression) évalue puis consomme le résultat | DROP | B3,L7,T11,U1 | P — Int et tableaux locaux synchrones, tableaux locaux async ; résultats faillibles inline sync/async consommés et effets d’expression exécutés une seule fois avant l’instruction suivante. Deux mutations de validité détectées dans le cycle stockage. Couverture propriétaire à poursuivre. [Cycle stockage](cycles/STORAGE_DESIGN_CYCLE.md), INTEGER_CONVERSIONS_CYCLE.md Complément brouillon 01 : contrôles de motifs propriétaires et consommation explicite, O0/O2, emprunts et réemploi ; trois mutations détectées. Couverture partielle et contre-exemples encore ouverts dans [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). |
| L7 | Mort logique indépendante de la réservation physique | STORAGE | L6,P4,P8 | P — stockage peut rester réservé. Cellules de tailles différentes exercées par 200 transitions du modèle par intervalles, graine 9081, sous UBSan à O0 et O2. Raccordement aux structures locales restant. [Cycle stockage](cycles/STORAGE_DESIGN_CYCLE.md) |
| A1 | Stockage local implicite ou pool explicitement nommé, transmis par `&mut Pool<T>` pour l’allocation | SOURCE | I2,B4,P8 | P — création et transfert via `&mut Pool<Point>` exercés. Migration des anciennes syntaxes à intégrer. |
| A2 | Stockage valide pendant vie de l'allocation | SOURCE | A3,A5,V5 | P — champs &Int/&mut Int ; transferts bornés |
| A3 | Pas de transfert implicite d'une source trop courte | SOURCE | T3,T5,A6 | P — pas de sources retournées ou stockées |
| A4 | Allouer sans emprunt permanent de la source | SOURCE | B1,P8,E1 | P — capacité stricte requise |
| A5 | Reset détruit avant réinitialisation et protège les futurs usages | RESET | B4a,T11,L3 | P — effets conditionnels conservatifs |
| A6 | Objets détruits avant fermeture de leur source | SOURCE | L2,A3,A5 | P — pas de sources déplaçables |
| P1 | Plages virtuelles stables, bornées et gardées | STORAGE | V5,E1 | P — backend Rust, garde de fin des deux datastacks. 16 scénarios sous UBSan à -O0/-O2 sur macOS arm64. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#p1--pages-de-garde) |
| P2 | Configuration locale explicite des réservations | DIRECTIVES | I4,P1,G6,G7 | P — syntaxe catégorisée et héritage lexical exercés ; adresses et limites après transfert sous UBSan O0/O2. Blocs annotés async encore refusés. [Cycle directives](cycles/DIRECTIVES_CYCLE.md) |
| P3 | Préparer le stockage local durable côté receveur en conservant adresse et ordre d’évaluation | STORAGE | I3,L3,T6,V2 | P — réservation anticipée sur les sources historiques et dans les formes de G1. Réservation de structures dans la data stack implicite à intégrer. |
| P4 | Ne récupérer au curseur que des suffixes morts | STORAGE | L7,P8,V5 | P — modèle fixe sans croissance |
| P5 | Deux fronts de croissance sans chevauchement | STORAGE | P1,P6,E1 | P — deux fronts de Vector et collisions exercés ; String suit TX21 |
| P6 | Borner la population vivante, pas le total successif | FUTURE | P3,P5,E1 | N — analyse statique générale non implémentée |
| P7 | Fallback local explicite conservant les garanties | SOURCE | I1,A1,P8 | P — backends explicites ; sélection statique automatique absente |
| P8 | Pool typé, slots adaptés, type conservé aux appels | POOL | B4,B4b,P4,L7 | P — Int et enums ; pas de traits ni collections |
| P9 | Pool public d'enum, stack par variante, ordre global | ENUM | P8,L3,A5 | P — champs Int/&Int/&mut Int, match exhaustif et projections mutables (MUT_MATCH) |
| E1 | Épuisement : arrêt diagnostiqué sans déroulement | FAILURE | V4,P1,P8 | P — échec OS forcé non exhaustif |
| E2 | Tableaux : contrôle des bornes statique ou runtime | FUTURE | D4,E1 | N — tableaux hors périmètre |

## Profils de vérification

Pour tous les profils : les tests sont des éléments bornés ; aucun argument
formel ou machine-checkable général n'a été établi. Les mutations mentionnées
ci-dessous désignent uniquement les cinq fautes de ce cycle. Les mutations
runtime historiques ne sont pas présentées comme réexécutées ici.
Le [cycle des résultats de boucle](LOOP_RESULTS_VALIDATION.md) ajoute
quatre mutations ciblées, dont deux concernent la récupération des pools.
La régression globale du cycle compte 789 tests réussis.

| Profil | Exemples admis et refusés / preuves exécutables | Assertions runtime pertinentes | Modèle indépendant / mutations | Limites propres |
| --- | --- | --- | --- | --- |
| INTENT | [test_crust.py](../tests/test_crust.py) : `test_move_and_primitive_copy` admis ; `test_implicit_alias_rejected`, `test_source_required`, `test_uninitialized_new_rejected`, `test_unused_receiver_rejected` refusés | validation d'état Python ; pas de contrôle runtime remplaçant une intention manquante | Aucun modèle complet ni mutation dédiée à la grammaire | syntaxes réellement implémentées ; pas tous les builtins |
| ENTRY | [test_crust.py](../tests/test_crust.py) : main Void/Int, mauvais paramètres/retours, mélange script/main ; sorties et nettoyages | code retour du binaire, traces avant sortie | Pas de modèle ou mutation de main | arrêt et codes dépendants de la plateforme |
| LOOP_RESULT | [test_loop_results.py](../tests/test_loop_results.py) : résultats imbriqués, reprise et return, reset multi-provenance, emprunts et mauvais types/durées | traces de destruction, identité par adresse et capacité bornée | modèle de destruction par blocs et variantes générées avec graine 20261103 | voir le [rapport de cycle](LOOP_RESULTS_VALIDATION.md) |
| LOOP_CARRY | [test_loop_replacements.py](../tests/test_loop_replacements.py) : break/continue, fin normale, test faux, retours, enum, pools et refus d'emprunts/reset/ordre | identité par adresse, destruction unique, garde de nettoyage et provenance de chaque alternative | modèle de traces sur six séquences, graine 20261103 ; deux mutations ciblées | ordre compatible requis, accès actifs ou réactivables refusés, champ inactif conservé pour son nettoyage. [Dernier usage](LOOP_DEAD_FIELD_VALIDATION.md). [Rapport](LOOP_REPLACEMENT_VALIDATION.md) |
| FLOW | [test_conditionals.py](../tests/test_conditionals.py), [test_if_expressions.py](../tests/test_if_expressions.py), [test_loops.py](../tests/test_loops.py), [test_continue.py](../tests/test_continue.py), [test_while.py](../tests/test_while.py) : sorties avec réception admise ; usages après consommation conditionnelle refusés | gardes de nettoyage, compteurs de valeurs vivantes | Modèle de nettoyage sur une partie des branches, `test_audit_regressions.py` ; aucune mutation de contrôle de flux ce cycle | exploration bornée, pas tous les prédicats ni for |
| CALLS | [test_function_bodies.py](../tests/test_function_bodies.py), [test_modular_calls.py](../tests/test_modular_calls.py) : appels opaques et corps valides ; doubles consommations et emprunts incompatibles refusés | vérificateur des accès, invariants d'état | Modèle des exigences de pools seulement ; mutations signature/propagation/appel | pas de contrat pour récursion, FFI ou références retournées |
| TRANSFER | [test_crust.py](../tests/test_crust.py) : `test_nested_transfer_preserves_address`, `test_reception_and_child_cleanup_order` ; `test_use_after_move`, `test_downward_transfer_requires_direct_parent` refusés ; [test_results.py](../tests/test_results.py) | pas de contrôle runtime autorisant un ancien nom ; traces de destruction | Modèle indépendant moves/réceptions dans `test_audit_regressions.py` ; pas de mutation transfert ce cycle | imports directs et types actuels |
| ASSIGN | [test_reassignment.py](../tests/test_reassignment.py) : RHS utilisant le dernier emprunt admis, emprunt futur refusé ; adresse restituée et remplacement de pool | destructeur avant récupération ; arrêt capacité | modèle de nettoyage partiel, pas de modèle général de réaffectation | capacité simultanée RHS + ancienne valeur ; pas de champs |
| PROVENANCE | [test_provenances.py](../tests/test_provenances.py) : sélection stable et reset partiel après dernier usage ; reset avant usage ou fuite de source locale refusés | `cell_has_source`, gardes conditionnelles | modèle de nettoyage partiel ; aucune mutation provenance ce cycle | pas de graphe de références utilisateur |
| BORROW | [test_crust.py](../tests/test_crust.py) : `test_multiple_read_borrows`, `test_last_use_ends_borrow` ; `test_live_borrow_blocks_move`, `test_exclusive_mutable_borrow` refusés ; [test_function_bodies.py](../tests/test_function_bodies.py) | exclusivité et dernières utilisations contrôlées statiquement | Aucun modèle complet indépendant des emprunts ni mutation dédiée ce cycle | dernier usage conservatif ; réemprunts stockés restreints |
| ARGS | [test_arguments.py](../tests/test_arguments.py) : copie avant reset admise, emprunt préparé invalidé refusé ; [test_modular_calls.py](../tests/test_modular_calls.py) | temporaires C séquencés ; validation des arguments préparés | cas spécifiés indépendamment, pas de modèle complet ; pas de mutation ordre ce cycle | arguments de sources nommés |
| POOL | [test_pool_requirements.py](../tests/test_pool_requirements.py) : pool correct admis, autre type/tas/stack refusés ; [test_effects.py](../tests/test_effects.py), [test_modular_calls.py](../tests/test_modular_calls.py) | vérification statique des types ; `source_check_empty`, contrôles de capacité n'établissent pas seuls le typage | modèle de routes `pool_requirement_model.py` ; cinq mutations dans `validation/pool-requirement-mutations.json` | modèle readonly sans branches ; interactions couvertes par tests distincts, pas exhaustives |
| RESULT | [test_results.py](../tests/test_results.py), [test_conditional_returns.py](../tests/test_conditional_returns.py) : identité garantie admise, ancien accès et source locale refusés | correspondance résumé/racines observées dans le backend | modèle de réception/nettoyage partiel ; aucune mutation résultat ce cycle | pas de résultats empruntés |
| CONSTRAINT | [test_constraints.py](../tests/test_constraints.py) : lire puis reset admis, reset puis lecture de même source refusé ; égalité de `source.drop` | comparaisons statiques de sources, pas de test dynamique de relation | modèle des routes indépendant pour exigence de pool uniquement ; aucune mutation solveur | pas de satisfiabilité générale |
| CLEANUP | [test_scope_exit.py](../tests/test_scope_exit.py) : `test_normal_exit_closes_only_inner_scopes`, `test_explicit_drop_is_not_repeated_during_unwinding` ; source trop courte refusée | `source_check_empty`, `source->live`, gardes et traces | modèle de 32 opérations × 2 graines × 3 backends dans `test_audit_regressions.py` ; pas de mutation cleanup ce cycle | destructeur de démonstration ; pas de déroulement à l'échec |
| DROP | [test_drop_transitions.py](../tests/test_drop_transitions.py) : dernier réemprunt puis consommation admis ; emprunt futur, vieux accès et mauvais receveur refusés | `cell_drop`, retrait liste libre et récupération du suffixe | oracle runtime + modèle nettoyage ; pas de mutation drop ce cycle | pas de destructeur utilisateur |
| SOURCE | [test_scope_exit.py](../tests/test_scope_exit.py), [test_crust.py](../tests/test_crust.py) : source externe durable admise ; `test_transfer_from_child_allocator_rejected`, `test_stack_allocator_cannot_escape` refusés | `source_close` exige zéro objet vivant | oracle stockage, pas de modèle complet de durée de vie des sources ; mutations pool seulement | sources non déplaçables |
| RESET | [test_reset_transitions.py](../tests/test_reset_transitions.py) : `test_last_reborrow_does_not_prevent_reset_in_same_or_nested_function` admis ; `test_future_direct_or_borrowed_access_rejects_reset` refusé | destruction avant `source_reset` et `source_check_empty` | modèle nettoyage indépendant et oracle pool ; pas de mutation reset ce cycle | sources possibles analysées conservativement |
| STORAGE | [test_safety.py](../tests/test_safety.py) oracle 3000 opérations ; [test_crust.py](../tests/test_crust.py) adresses stables, suffixes, réservations invalides, débordements refusés/arrêtés | alignement, tailles et capacités, live/free-list, garde terminale | oracle runtime indépendant du générateur ; aucune mutation runtime ce cycle | une plateforme, pas de croissance ni double curseur ; ASan indisponible |
| ENUM | [test_crust.py](../tests/test_crust.py), [test_provenances.py](../tests/test_provenances.py), [test_pool_requirements.py](../tests/test_pool_requirements.py) : variantes/pools corrects admis ; champs, variantes et pools incompatibles refusés | `enum_new` vérifie bras ; provenance racine publique | oracle à deux tailles de bras ; modèle de routes typées ; mutations pool | champs Int/&Int/&mut Int, match readonly, pas de changement de variante en place |
| FAILURE | [test_crust.py](../tests/test_crust.py) : capacités valides et invalides ; `tests/validate_pool_contract_c.py` : deux programmes réussis, épuisement attendu | `fail`, débordements contrôlés avant calcul/adressage | oracle des bornes ; pas de mutation capacité ce cycle | pas de simulation exhaustive des erreurs OS ni déroulement |
| FUTURE | Aucun programme valide de la fonctionnalité générale dans le sous-ensemble ; un refus syntaxique ne prouve pas sa règle mémoire | Non applicables à une fonctionnalité absente | Aucun modèle/proof/mutation ne valide la règle générale | non implémenté / non vérifié |
| DESIGN | Lecture de la spécification et des frontières du sous-ensemble ; aucun test ne prouve un choix de conception | Non applicable | Pas de preuve formelle | ne pas assimiler refus des fonctions futures à leur validation |

## Matrice des interactions et réexamen global du cycle

Chaque domaine du système actuel a été relu. « Régression » signifie que les
suites existantes du domaine sont exécutées dans le cycle ; cela ne couvre pas
le produit cartésien des règles. Les interactions nouvelles sont détaillées
ci-dessous ; les fonctionnalités futures restent N, sans tests inventés.

| Domaines | Effet recherché / contre-exemple | Preuves du cycle et limites |
| --- | --- | --- |
| B4/B4b/B4e × P8/P9 | Exigence de signature perdue sans allocation | Cas initial, contrats opaques sans corps, modèle de 40 graphes et mutations |
| P8 × S3/B4a | Paramètres réordonnés, appels imbriqués et profondeur | Route model + tests déterministes de while/argument ; profondeur générée 7 fonctions |
| P8 × T9/S4/S5 | Branche littérale, divergence, return et obligations inaccessibles | Contradictions des branches refusées ; après return ignoré ; boucles et condition testées ; pas toute équivalence logique |
| P8 × V1/V2 | Ne pas confondre allouer Int et recevoir Pool<Int> | Int admis sur tas/stack/pool ; enum impose son pool ; champs/init en régression |
| P8 × B1/B2/B3 | Le type requis n'accorde pas une mutation supplémentaire | readonly/mut testé ; emprunts et déplacements en régression globale |
| P8 × B4d/A3 | Égalité de sources et durée du stockage | Conflit type de pool/provenance d'input testé ; sources locales masquées ; durées en régression |
| P8 × T2/T6/B4c/V5 | Retour d'identité après réutilisation d'un slot | Test nouveau adresse/restitution/destruction ; autres retours/provenances en régression |
| P8 × A5/L1/L2/L3/L6 | Reset et nettoyage exactement une fois, ordre sémantique | Nouveau scénario et modèle cleanup existant ; oracle runtime ; C O0/O2/Os/UBSan |
| P8/P9 × P4/L7/E1 | Slot réutilisé, suffixe mort, épuisement | Oracle 3000 opérations, régression et trois programmes C bornés |
| I1–I5, U1, S1/S2/S6, T1/T4/T5/T7/T8/T10/T11, A1/A2/A4/A6 | Intention, portée, aliases, réception, sorties | Réexamen de spécification et suites complètes correspondantes ; aucun invariant n'est déclaré globalement établi |
| L4/L5/P2/P3/P5/P6/E2 | Règles futures | Non vérifiées ; pas de fonctionnalité ajoutée pour les tester |

Aucun changement de sémantique normative n'est autorisé par cette matrice.
Les contradictions de spécification, limites de couverture et divergences non
résolues doivent être consignées dans le rapport du cycle, sans modifier les
attentes pour obtenir des tests verts.


## Extension des preuves : champs &Int

Le profil FIELD ci-dessous complète V2/V5, T2/T6/T9/T10/T11, D3/D4,
B1/B2/B3/B4/B4a/B4d/B4e, L1/L2/L3/L6/L7, A2/A3/A5/A6 et P8/P9.
D1/D2 sont maintenant couverts partiellement pour les champs &Int, sans promotion
implicite. Le graphe général reste non vérifié ; B5 est maintenant partiellement couvert par RETURN_REF.

| Profil | Attentes et exemples admis/refusés | Préconditions et invariant | Runtime / modèle / mutations | Limites |
| --- | --- | --- | --- | --- |
| FIELD | [test_reference_fields.py](../tests/test_reference_fields.py) : lecture puis drop admis ; drop/mutation/reset avant lecture refusés ; transferts vers cible déjà durable admis ; cible locale refusée ; retours de fonction à cibles durables couverts par RETURN_FIELD | &Int immutable vers allocation nommée ; tous les usages futurs du porteur protègent ses cibles ; pas de nouveau droit mutable | Payload memcpy et offsets par variante ; modèle 32 scénarios, 19 valides/13 invalides ; quatre mutations ; [rapports](REFERENCE_FIELDS.md) | un niveau de dépendances, pas de références d'enums, cycles, promotion automatique ou destructeur utilisateur ; variante connue ou union statique |

Interactions exercées : FIELD × B4a (initialiseur suivant qui reset/consomme),
FIELD × B4d/B4e (provenances de champs substituées sans corps), FIELD × T9/T10
(union des cibles), FIELD × V4/P8/L7 (remplacement et slot réutilisé), FIELD ×
S4/B2 (prochain usage dans une boucle), FIELD × A5 (reset des cibles ou du porteur),
FIELD × L1/L2/L3 (cible détruite après dernier usage, porteur nettoyé sans
déréférencement), FIELD × A3/T6 (transfert borné). Les 66 règles ont été
reconsidérées sous les restrictions de cette extension ; les suites complètes
réexécutent les modèles existants et les autres interactions. Aucune combinaison
générale ou preuve formelle n'en découle. Les résultats exécutés et les limites
restent distingués dans le rapport de cycle.


## Extension des preuves : retours avec champs empruntés

Le profil RETURN_FIELD complète les 66 règles existantes sans prétendre les
établir. Référence : [BORROWED_RETURNS.md](BORROWED_RETURNS.md). Les règles
D1/D2 sont partiellement couverts pour les champs &Int ; les graphes généraux
restent non vérifiés. Les retours directs &Int B5 sont couverts partiellement par RETURN_REF.

| Profil | Attentes et cas admis/refusés | Préconditions et invariant | Modèles, assertions et mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_FIELD | [test_borrowed_returns.py](../tests/test_borrowed_returns.py) : cible empruntée au parent admise ; cible locale ou Int injecté par transfert refusés ; drop/reset avant usage refusés, après dernier usage admis | &Int immuable ; toutes les cibles déjà vivantes dans destination/ancêtres ; identité des champs conservée dans contrats opaques ; parent mutable suspendu pendant réemprunt partagé | vérification destination et correspondance contrat/observé ; modèle 24 routes de scopes, 12 admises/12 refusées ; cinq nouvelles mutations et quatre précédentes rejouées ; C O0/O2/Os/UBSan | pas de promotion locale, graphes transitifs ou destructeurs utilisateur ; pas d'oracle général des emprunts ni preuve formelle |

Interactions examinées : RETURN_FIELD × S3/S5/T3/T5/T6 (frontières successives),
RETURN_FIELD × B4c/B4d/B4e (identité de paramètres/champs et substitution sans corps),
RETURN_FIELD × B1/B2/B3 (réemprunt partagé et reprise du parent mutable),
avec refus d'un alias non apparenté depuis l'accès d'origine pendant ce réemprunt,
RETURN_FIELD × A3/A6 (durée de la cible distincte de celle du pool),
RETURN_FIELD × T9/T11 (unions de cibles et variantes), RETURN_FIELD × V4/V5/L6
(réaffectation, drop et identité), RETURN_FIELD × A5/L2/L3/P8/P9 (reset, nettoyage
et capacité), RETURN_FIELD × B4a (argument déjà préparé), RETURN_FIELD × S4
(prochain usage dans une boucle). Les règles futures ne sont pas ajoutées pour
augmenter les tests ; les limites et résultats sont consignés dans le rapport.


## Décision D1 : pas de promotion implicite

L'utilisateur a explicitement remplacé la proposition de promotion des cibles
par leur refus de transfert si elles ne sont pas déjà assez durables. Les 66
identifiants sont conservés. D1/D2 passent de règle future à couverture partielle
pour les champs &Int existants ; aucun graphe général n'est annoncé. Les
interactions I1/T3/T5/B4c/D3/D4/A2/A3/L2/L3/P8/P9 ont été reconsidérées :
aucun rattachement, ordre de destruction, pool ou mécanisme d'emprunt n'est
modifié par cette décision, qui correspond au comportement déjà implémenté.
Les tests refusent une cible locale même lorsque son pool est durable, y compris
après une première frontière admissible. Voir [décision et validation ciblée](NO_IMPLICIT_PROMOTION.md).

## Extension des preuves : retours directs &Int

Le profil RETURN_REF couvre partiellement B5, avec les prémisses D1/D3/D4 et
les interactions B1/B2/B3/B4a/B4c/B4d/B4e, S3/S4/S5, T2/T5/T9, U1,
V4/V5, L1/L2/L3/L6/L7, A2/A3/A5/A6 et P8/P9. Les 66 règles ont été
reconsidérées : aucun changement de placement, de transfert d'allocation ou
d'ordre de destruction n'est introduit. I1/I2/B4 restent explicites ; les règles
futures L4/L5/P2/P3/P5/P6/E2 ne sont pas implémentées par cette extension.

| Profil | Cas admis/refusés | Préconditions et invariant | Observations, modèles et mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_REF | [test_direct_borrow_returns.py](../tests/test_direct_borrow_returns.py) : parent/ancêtre et relais admis ; cible locale/paramètre transféré refusés ; drop/reset/mutation avant usage refusés, après dernier usage admis | résultat &Int en lecture ; chaque cible déjà vivante et rattachée au parent/ancêtre ; aucune promotion, aucune allocation du résultat ; toutes les alternatives protégées | contrat `reference_targets`, vérification de frontière et contrat/observé ; 24 graines de permutations et unions (12 valides/12 invalides), adresses et destructions ; cinq mutations nouvelles, neuf précédentes rejouées ; douze exécutions C O0/O2/Os/UBSan | pas de retour &mut ou vers enum, pas de sortie d'un champ via match ; modèle borné sans preuve générale des emprunts |

Interactions spécifiques : résultat conditionnel × sources distinctes × reset ;
référence retournée × champ &Int × drop des alternatives ; argument préparé ×
alias secondaire mutable/reset dans l'argument suivant ; relais × historique
antérieur de reset ; réemprunt partagé × reprise du parent mutable ; réaffectation
sans destruction des cibles ; boucles/continue et nettoyage sans destruction du
parent ; réutilisation de slot après dernière lecture. Les effets opaques restent
vérifiés sans lire les corps. Voir [rapport du cycle](DIRECT_BORROW_RETURNS.md)
pour les résultats exécutés et les limites d'instrumentation.


## Clarification : création et utilisation d'un emprunt

Décision explicite de l'utilisateur : `inspect(&data)` crée un emprunt depuis
une allocation ; `inspect(view)` et `return view` utilisent une référence
existante. Un `&` supplémentaire n'est pas aplati. Les références imbriquées
ne sont pas implémentées et sont refusées. Le profil REF_VALUE complète B4/B5
et V2/P9 pour la cohérence des champs &Int, sans nouvel identifiant normatif.

| Profil | Cas valides et invalides | Invariant et prémisses | Modèles / runtime / mutations | Limites |
| --- | --- | --- | --- | --- |
| REF_VALUE | [test_reference_values.py](../tests/test_reference_values.py) : appels/retours par nom, résultat de sous-appel, paramètres de pools et champs ; refus de &référence, propriétaire passé sans &, escalade readonly→mutable, drop/reset avant usage | pas d'emprunt implicite d'allocation ; type/mode de référence conservé, cibles et parents mutables suivis ; arguments préparés protégés ; source readonly reste readonly | 8 programmes admis exécutés, 23 cas refusés par check et compilation, 1 contrôle d'inférence seule ; modèles précédents migrés sans changer leurs oracles ; cinq mutations spécifiques + quatorze précédentes ; C optimisé et UBSan | pas de &&Int, affectation générale d'alias, retour &mut ni nouveau type ; une famille C, pas de preuve générale |

Les 66 règles ont été réexaminées : I1/T1/V3 (intention et absence de copie
d'allocation), S3–S5/D1/T5/B5 (frontières et nettoyage), D3/T9/T11 (unions de
cibles), B1–B3/B4a (exclusivité, derniers usages et ordre des arguments),
B4b–e/A1/A2/A3/A5/A6/P8/P9 (contrats et capacités des sources),
V4/V5/L1–L3/L6/L7 (identité, remplacement et destruction unique) sont exercées
par les régressions et les scénarios nouveaux. Les règles de placement futur,
collections, destructeurs utilisateur et concurrence restent hors périmètre.
Le format des pointeurs C et le runtime ne changent pas. Les résultats et
limites du cycle sont dans [REFERENCE_VALUES.md](REFERENCE_VALUES.md).


## Extension V4 : let / let mut et mutation du contenu

Décision de l'utilisateur : déclarations `let` immutables, `let mut` pour les
écritures directes ; `name = 20` et `name.set(20)` modifient le contenu d'un Int
alloué sans changer son identité. Le remplacement par un résultat alloué garde
son nettoyage après RHS. Les 67 identifiants normatifs sont conservés : V4 est
précisée, B4 distingue le mut de la variable de la capacité &mut.

| Profil | Attentes / cas admis et refusés | Prémisses et invariant | Observations, modèles, mutations | Limites |
| --- | --- | --- | --- | --- |
| LET_MUT | [test_let_mutability.py](../tests/test_let_mutability.py) : adresse stable pour = et .set ; propriétaire immutable refusé en écriture, &mut via let admis, let mut &Int refusé ; drop/reset avant usage refusés, après usage et réutilisation admis | mutation sans création/réception/destruction ; cible encore vivante après RHS ; mutabilité du nom distincte de celle du pointeur ; consommations explicites d'un nom immutable permises ; sources et contrats conservés | 33 programmes nouveaux admis et 50 refusés aux deux stages ; modèle 12 graines ×12 écritures, matrice déclarative 18 cas (5 admis/13 refusés) ; cinq mutations nouvelles et 19 précédentes rejouées ; C O0/O2/Os/O2-UBSan | .set sur variable et littéral Int ; références imbriquées, retour &mut et affectations générales d'alias hors périmètre ; pas de preuve générale |

Réexamen des 66 règles : I1/I2/V1/V3/T1 (intention, source et absence de copie
implicite), V2/V4/V5/L1–L3/L6/L7/P8 (initialisation, identité, destruction et
slots), B1–B5/B4a–e/D1/D3/D4 (capacité, derniers usages, contrats, provenances
et ordre d'évaluation), S3–S5/T2–T11/U1 (fonctions, branches, imports, boucles
et retours), A1–A6/P9/E1 (pools, source mutable, reset et épuisement) restent
interactifs. Les tests vérifient un RHS qui lit la cible avant l'écriture et
un RHS qui la consomme ou reset son pool ; les contrats opaques doivent
conserver son historique après l'écriture. Une mutation de ce dernier suivi
est détectée même lorsque le backend spécialisé refuserait encore le code.
Les variantes de placement et autres règles futures restent non implémentées.
Voir le [rapport et les limites](LET_MUTABILITY.md).


## Extension B5 : retours d'emprunts mutables

Décision explicite de l'utilisateur : `-> &mut Int` retourne la capacité
exclusive, sans transfert d'allocation ni promotion. L'exemple utilise
`let mut vue = borrow_mut(&mut nombre)`. Les 67 identifiants sont conservés ;
B5 reçoit le profil RETURN_MUT en complément des cycles précédents.

| Profil | Cas admis/refusés | Invariant et prémisses | Observations / modèles / mutations | Limites |
| --- | --- | --- | --- | --- |
| RETURN_MUT | [test_mutable_borrow_returns.py](../tests/test_mutable_borrow_returns.py) : mutation via résultat, reprise parent après dernier usage, relais, unions, enfants partagés, passage direct en argument ; refus des autres lectures/écritures, drop/reset avant usage et cibles locales | chaque candidat a une capacité &mut d'entrée et vit déjà dans parent/ancêtres ; un prêt exclusif par binding et cible, parents suspendus tant que le descendant le requiert ; adresses et source conservées | 28 programmes admis exécutés et 58 refusés aux deux stages ; modèle 24 graines, 1–4 relais, permutations et unions, 12 valides/12 invalides ; 5 mutations spécifiques et 24 précédentes rejouées ; C O0/O2/Os/UBSan | retours Int uniquement ; pas de référence imbriquée, projection mutable de champ, destructeur utilisateur ou preuve formelle |

Réexamen global : B1/B2/B3/B4/B4a–e/B5 (capacité, type, arguments, dernier usage
et contrat opaque), D1/D2/D3/D4/T5/T9/T11 (durabilité et unions), S3/S4/S5
(scopes, boucles, continue, return annulant un appel), V3/V4/V5/U1/L1–L3/L6/L7
(aucune copie, identité, usage explicite et nettoyage unique), A1–A6/P8/P9/E1
(source, reset, slot réutilisé et épuisement) sont exercés ou réexaminés.
Le suivi de dernier usage a aussi été corrigé pour V4/U1 : une écriture de
contenu sur un Int alloué n'est pas une fin de binding et constitue un usage.
Les règles futures de collections, FFI, placement et concurrence restent hors
périmètre. Les preuves et limites sont dans [MUTABLE_BORROW_RETURNS.md](MUTABLE_BORROW_RETURNS.md).

## Extension P9/B1 : références mutables stockées

Décision utilisateur : un champ &mut Int conserve la capacité exclusive sur sa
cible jusqu'au dernier usage du porteur ou d'une référence vers lui. Les
identifiants normatifs restent inchangés ; MUT_FIELD complète FIELD et RETURN_FIELD.

| Profil | Cas admis/refusés | Invariant et prémisses | Observations / modèles / mutations | Limites |
| --- | --- | --- | --- | --- |
| MUT_FIELD | [test_mutable_reference_fields.py](../tests/test_mutable_reference_fields.py) : aliases partagés du porteur, lecture projetée, relais, transferts, retours conditionnels, reprise du parent ; refus des accès d'origine/drop/reset prématurés, champs aliasés et entrée readonly | capacité mutable d'entrée ; cibles déjà durables à chaque frontière ; une capacité de champ par porteur et cible, conservée via les aliases et projections partagées | 24 sources admises exécutées, 43 refusées aux deux stages ; modèle graine 381, 24 scénarios (12/12) ; 6 mutations spécifiques et 29 précédentes détectées ; suites globales 729/729 ; C O0/O2/Os/O2-UBSan ; [rapport et artefacts](MUTABLE_REFERENCE_FIELDS.md) | Int uniquement, champs non réaffectables, projections en lecture, contrats conservatifs ; aucun destructeur utilisateur ni preuve formelle |

Interactions réexaminées pour les 66 règles : I1–I5/V1–V5 (intention, types,
mutabilité, identité), S1–S6/T1–T11/U1 (scopes, réceptions, branches et boucles),
D1–D4/B1–B5/B4a–e (durabilité, capacités, contrats et arguments), L1–L7/A1–A6/
P8/P9/E1 (sources, nettoyage, reset, slots, épuisement). Les règles de placement,
collections et autres fonctionnalités futures conservent leur statut antérieur.
Les interactions exécutées ne couvrent pas toutes les combinaisons possibles.

## Extension P9/B1/B2 — projections mutables dans un bras

| Profil | Cas admis et refusés | Invariant | Observations | Limites |
| --- | --- | --- | --- | --- |
| MUT_MATCH | [Tests](../tests/test_mutable_match.py) avec écriture projetée, alias partagé, projection hors bras, appels successifs, reset et drop | accès exclusif au porteur pendant le bras, puis protection des cibles jusqu'au dernier usage du porteur ou d'une référence vers lui | 9 sources admises et exécutées, 19 refusées par les deux stages, modèle à deux frontières, 3 injections détectées, 8 exécutions C, 739 tests globaux et 67 tests ciblés sous UBSan | écritures Int par `.set()` et appels Void avec projections nommées (MATCH_CALL). L'analyse refuse les projections de champs dont les ensembles de cibles peuvent se recouvrir |

S4 et S5 délimitent le réemprunt. V4 et V5 encadrent l'écriture sur place.
D1–D4, T9–T11 et B4–B5 encadrent les cibles obtenues par transfert ou appel.
L1–L7, A2, A5 et P8 gardent leur rôle dans le nettoyage et la réutilisation.
[Rapport du cycle](MATCH_MUTABLE.md).

## Extension P9/B4 — appels avec projections du bras

| Profil | Cas admis et refusés | Invariant | Observations | Limites |
| --- | --- | --- | --- | --- |
| MATCH_CALL | [Tests](../tests/test_mutable_match_calls.py) avec appels successifs, aliasage refusé, restauration de la projection, variante impossible et divergence | l'appel réemprunte la projection et la rend au bras. Le porteur continue de protéger la cible | 4 sources admises exécutées, 11 refusées par les deux stages, 3 injections dédiées et 6 rejouées détectées, 4 exécutions C, 745 tests globaux et 73 sous UBSan ciblé | appels Void et arguments limités aux noms des projections du bras |

S4–S5, B1–B5, D1–D4, T9–T11, V4–V5, L1–L7, A2 et A5 sont réexaminées
dans [le rapport](MATCH_MUTABLE.md#appels-void-dans-un-bras).

| Extension de MATCH_CALL | Invariant | Validation ciblée |
| --- | --- | --- |
| Résultat Int dans une déclaration du bras (S4, V3, B4, P9) | copie indépendante, projection réutilisable au retour, porteur réservé pendant le bras | copie avant écriture, rejet de l'accès d'origine et de la liaison hors du bras, type et arité dans une variante impossible |
| Retour &mut Int reçu par `let mut` dans le bras (B1, B2, B4, B5, S4, P9) | le parent reprend après le dernier usage du résultat, la réservation du porteur couvre le bras | retour relayé, écriture après dernier usage, rejet de lecture, écriture et appel prématurés, portée locale, variante impossible |
| Résultat &mut Int reçu après le match (S4, B1, B2, B4, B5, P9) | réservation du porteur et durée de vie des cibles jusqu'au dernier usage du résultat ou d'un descendant | lecture du porteur avant/après, reset et drop, retours relayés, variantes conditionnelles, injection du prêt du porteur, 4 exécutions C, 756 tests globaux et 84 sous UBSan ciblé |
| Retour d'une projection via un paramètre porteur &mut (B1, B2, B4, B5, D1, P9) | le contrat transporte les cibles et le porteur jusqu'au dernier usage chez l'appelant | lecture du porteur avant/après, durée de vie et reset, variantes connues, réindexation via relais, inspection du contrat, 762 tests globaux, 90 ciblés sous UBSan et une injection détectée |
| Réservations stockées et transitives (B1–B5, D1–D4, T9–T11, P9) | chaque descendant protège les porteurs et cibles possibles, chaque transfert vérifie leur durée de vie | stockage et retour opaque, chaîne, transfert refusé si le porteur ne survit pas, union des porteurs |
| Contrats d'ordre des resets (S4, S5, B4a, B4d, A5) | aucun usage invalide après reset sur le même chemin et aucune invalidation d'un emprunt futur ou d'un argument préparé | ordre direct et composé, branches, jonction de l'appelant, autre emprunt actif, argument préparé, retour de boucle, 771 tests globaux, 99 ciblés sous UBSan, 2 injections détectées et 8 exécutions C |

## Tableaux de taille fixe

| Règle | Invariant et interactions | Évidence du cycle |
| --- | --- | --- |
| E2, E4 | Un indice valide précède l'accès C. Le contrôle de la ligne précède l'évaluation de la colonne et de la valeur à écrire. Le calcul d'un indice peut avoir des effets de sources. | Cas exécutés pour les indices négatifs et la borne supérieure, rejet statique des constantes invalides, mutation de la borne détectée et cas de reset via un appel dans un indice. |
| E3 | Initialisation ordonnée et complète. Une répétition évalue sa valeur une fois, y compris pour zéro. | Trace exécutée, mutation d'ordre détectée, retour contextuel d'un tableau vide et accès au tableau vide rejeté. Couverture partielle pour les autres contextes de typage. Les tableaux Int locaux async couvrent aussi la répétition suspendable, le contexte vide et len statique. |
| E5 | Aucune copie implicite de ligne. La case garde son type et une valeur initialisée. Le passage de valeurs et les transferts conservent le type et la longueur. | Exécution des retours et des copies à travers fonctions, branches et boucles. Rejets pour des types ou des opérateurs incompatibles. Modèle par liste de 90 opérations. Replace et swap de cases Int dans une tâche async, avec indices suspendables, contrôle avant effet et respect des prêts. Copie explicite et swap de lignes Int exercés pendant un prêt disjoint. Replace de ligne Int prépare la nouvelle ligne, rend l’ancienne indépendante et respecte le dernier usage du prêt dans la partie droite. Déplacements explicites de tableaux Int entre liaisons, bloc, if et break async exercés avec contrôle de forme et d’emprunt. Les paramètres async de tableau Int reçoivent une valeur indépendante préparée dans l’ordre des arguments. Un retour explicite de tableau Int par await extrait la valeur avant réemploi du slot. Le relais et la compatibilité de forme sont exercés. Await d’un handle dans une tâche async extrait aussi le tableau avec sa forme, et le match couvre Ok et Err. Le join synchrone restitue aussi un tableau Int avec sa forme, y compris dans un match à valeur. |
| E6, E7 | Les emprunts de tableaux et les références stockées protègent des cibles durables à travers les usages, les remplacements et les appels. | État initial du cycle ; voir les preuves du cycle courant ci-dessous. |

Voir [FIXED_ARRAYS_VALIDATION.md](FIXED_ARRAYS_VALIDATION.md).


### Tableaux fixes d’octets dans les cadres async

| Règles | Invariant | Évidence et limites |
| --- | --- | --- |
| E2–E5, AS2, AS8–AS10 | La forme et le type d’élément sont conservés jusque dans le stockage C et les résultats de contrôle. | Tableaux u8 imbriqués préparés avant lancement, copie indépendante, lecture et écriture typées, pas mémoire d’un octet, remplacement de case, swap, transfert dans une boucle annotée, retour littéral, await et join. Indices suspendus et garde dynamique exercés. Mélange avec Int à forme identique refusé. Mutations du pas et du type au break détectées. Couverture partielle des expressions de transfert et des types de feuilles. |
| E6, AS12, AS15, MT6 | Un octet emprunté conserve sa source, y compris après l’extraction d’un résultat. | Prêt local transmis à un enfant, mutation et déplacement refusés avant dernier usage. Retour d’une case d’un paramètre tableau emprunté par await, handle et join relayé en synchrone. Mutation de provenance détectée. Retour d’une vue vers un tableau du cadre refusé. Couverture partielle des emprunts mutables scalaires u8 et des liaisons locales de tableau emprunté. |

Les exécutions à O0 et O2 sous UBSan fatal et leurs mutations sont consignées
dans [le rapport async](cycles/ASYNC_DESIGN_CYCLE.md#tableaux-fixes-u8-dans-les-fonctions-async).

### Tranches partagées de Vector en async

| Règles | Invariant | Évidence et limites |
| --- | --- | --- |
| VE5, AS8–AS10, B4a | Le descripteur conserve ses bornes, son pas et son sens à travers les suspensions. La source préparée reste protégée pendant le calcul des bornes et de l’indice. | `&[Int]` et `&[u8]` locaux, sous-tranches, indexation, capture et retour par `await` ou `join`. Oracle par listes sur deux sens de placement et trois bornes. Bornes dynamiques hors limites et indexation d’une tranche vide arrêtées par les gardes C. Une réaffectation pendant le calcul des bornes conserve le descripteur préparé et protège sa source. Mutations du sens et de la sauvegarde détectées. |
| AS2, AS11–AS13, AS15, MT6 | L’emprunt protège la source dès la capture et jusqu’au dernier usage du résultat. La terminaison libère les captures seulement utilisées pour le calcul. | Contrats synchrones de lancement et de `join`, choix entre deux sources avec échec de lancement simulé, source d’un indice rendue accessible après `join`, origine élargie à la reprise d’une boucle. Sortie d’une vue vers une collection locale et modification prématurée refusées. Mutations de provenance, de boucle et de borne détectées. |
| VE5, TX16, B4, AS12 | Une tranche d’octets peut servir au remplacement UTF-8 ou fournir un `&u8` qui conserve son origine. Le descripteur de tranche a un type distinct de `Int`. | Remplacement avec tranche relayée et sous-tranche, retour d’une référence d’octet à travers `await` puis `join`, croissance admise après le dernier usage. Captures `&Int` et `&mut Int` visant une tranche refusées. Le prêt `&Int` d’une case de tranche reste ouvert dans les corps async. |

Voir [le rapport de cycle](cycles/ASYNC_DESIGN_CYCLE.md#tranches-partagées-de-vector-en-async)
pour les configurations, contre-exemples et résultats exécutés.

| Règles | Invariant | Évidence et limites |
| --- | --- | --- |
| B1–B2, B4a, AS12, AS15, VE5 | Une tranche partagée laisse lire via le même `&mut Vector<T>`. Elle interdit les écritures et les nouvelles captures mutables jusqu’au dernier usage. L’accès par le propriétaire d’origine reste distinct. | Test synchrone avec retour par contrat et lecture pendant la préparation d’un argument. Test async avec retour par `await`, tâche enfant sur un autre thread et capture partagée de la même source. Deux programmes natifs et six refus vérifiés sous UBSan à O0 et O2. Six mutations détectées. |
| AS2, AS12–AS13, AS15, MT5–MT6, VE5 | Le lancement synchrone conserve le parent de chaque capture. Une capture mutable exclut les accès pendant l’exécution. La tranche partagée issue du `join` autorise la lecture via ce même parent et garde toutes ses provenances possibles. | Lancement direct et via contrat, transfert de handle, échec de lancement simulé, résultat issu de deux sources, refus de lecture pendant l’exécution et d’écriture avant le dernier usage, ordre des arguments, sortie de bloc et `drop` de la source. Quatre mutations détectées. |
| B1–B2, B4, AS15 | `&*v` et `&mut *v` réempruntent le vecteur. Un appel en lecture via le même parent peut coexister avec des captures partagées. | Deux tâches en lecture, appel synchrone avec le parent, puis tâche exclusive via un contrat. Références imbriquées, changement de mode et écriture avant la fin du second prêt refusés. Quatre mutations détectées. La construction autonome d’une liaison par `let alias = &*v` reste distincte. |
| VE5, G12, B1–B2, AS8–AS9, TX16 | Les moitiés mutables locales restent disjointes malgré les suspensions. Un réemprunt partagé réserve sa moitié et les ancêtres nécessaires. | Séparation Int et u8, subdivision de la moitié droite, écritures, garde avant le RHS, placement ascendant et descendant, relais de vue par `await` et reprise de la croissance après la dernière lecture. Trois mutations détectées. |
| B3, D1, T3–T5, AS10–AS13, MT6, VE5 | Le résultat partagé d’une séparation retient le vecteur qui contient ses éléments. Une tâche exportée ne peut emprunter une allocation détruite ou déplacée à la sortie. | Retours de tranche et d’octet, bloc, if, break, affectation à un parent, transfert d’une tâche inactive et d’un handle. La borne est libérée au `join` et le vecteur reste protégé. Contre-exemple de lecture après destruction reproduit sur une ancienne version. Variantes de sortie d’itération et de branche refusées et mutations détectées. |
| B1–B2, AS2, AS12–AS15, MT1–MT6, VE5 | Une capture `&mut [T]` réserve la moitié concernée dès la création. Une tâche sur l’autre moitié peut avancer indépendamment. | Deux workers synchronisés par un rendez-vous atomique, depuis `main` et depuis un cadre async, avec lancement direct et contrat de handle. Réemploi après drop inactif, retour partagé par `await` et `join`, échec de lancement simulé et cible locale refusée au transfert. Quatre mutations détectées. Les retours mutables et les paires comme résultats async restent ouverts. |

### Emprunts locaux de tableaux et paramètres empruntés

| Règle | Invariant et interactions | Évidence du cycle |
| --- | --- | --- |
| E3 | Le type d'un paramètre ou d'une destination détermine la forme de `[]`. | Exécution du passage d'un tableau vide, de l'écriture et du remplacement d'une ligne vide. Annotation synchrone de tableaux Int et de références vides, passage à une tâche et relais par await sous UBSan. Longueur incompatible et indexation refusées. Mutation d’accès au champ C inexistant détectée. Propagation du type attendu aux lignes vides d’un littéral imbriqué. Projection et relais de ligne sous UBSan, ligne vide de longueur attendue non nulle refusée. Mutation qui omet la propagation détectée. Le contrat de retour fournit aussi le contexte à un littéral imbriqué transféré, directement ou via une variable locale annotée. Omission du contexte de retour détectée. Arguments imbriqués vides typés par la signature dans les contrats et l’analyse des sources. Variantes Int, références partagées et références mutables transférées, longueur et transfert vérifiés. Omission du contexte de l’argument détectée. La signature type aussi le littéral temporaire prêté en partagé ou mutable. La longueur incompatible et la conservation du prêt au-delà de l’instruction sont refusées. Omission du contexte temporaire détectée. Type de receveur propagé aux branches de if, en affectation et retour explicite. Les deux branches exécutées sous UBSan, branche de longueur différente et transfert manquant refusés. Omission du contexte de branche détectée. Type du receveur transmis aux break d’une boucle avec reprise par continue. Liaison annotée et retour explicite, deux sorties exécutées. Longueur et transfert vérifiés, omission du contexte de break détectée. Contexte transmis aux bras d’un match sur enum et sur résultat de join. Ok et Err sous UBSan, branche de longueur incompatible et transfert manquant refusés. Omission du contexte de match détectée. Transfert direct d’un littéral depuis un bloc enfant typé par le receveur. Référence vers le parent admise, cible locale refusée et omission du contrôle de durée de vie détectée. |
| E6 | Un emprunt de case protège le tableau entier jusqu'au dernier usage. Un réemprunt conserve la réservation héritée. | Programmes acceptés et refusés pour la fin dans la partie droite, la reprise de boucle, le réemprunt et le déplacement d'un tableau emprunté. `mut_ref()` d’un tableau de références conserve son type et les mises à jour de cases traversent un relais de fonctions. Deux cases mutables de tableaux distincts peuvent être capturées via une fabrique de tâche. Deux cases du même tableau sont refusées. Une tâche ne peut emporter une case locale hors de son bloc. Mutation de la portée détectée. |
| E6 et B4a | Un argument emprunté protège le tableau pendant les arguments suivants. La copie temporaire prêtée à l'appel ne peut être retenue dans une liaison. | Exécution des passages partagé et mutable, appel avec copie temporaire et rejet du conflit dans l'argument suivant. |
| E6 et E7 | Durabilité des références lors des sorties et provenance par case. | Limite du cycle initial, levée dans le cycle courant ci-dessous. |

### Cycle courant des tableaux et références stockées

Les lignes historiques ci-dessus décrivent les cycles précédents. Le tableau
suivant décrit l'extension courante. Les écarts restants sont consignés dans
FIXED_ARRAYS_VALIDATION.md.

| Règle | Invariant et interactions | Évidence courante | Limite |
| --- | --- | --- | --- |
| E2 et E4 | Contrôle avant accès et ordre des effets | Indices négatifs, indices imbriqués, bornes dynamiques, garde immuable, borne statique sur let immuable, effet de reset dans un indice, mutation de borne | Tailles extrêmes non couvertes |
| E3 et E5 | Copies explicites et conservation du type, y compris pour zéro | Littéraux ordonnés, répétition partagée, tableaux vides typés, copie mutable refusée, modèles par listes | mut() exclu explicitement du prototype |
| E6, B4a et D1 | Cibles et parents durables pendant les appels et les transferts | Réemprunts locaux, temporaire, arguments ordonnés, retours par fonction et boucle, provenances multiples | Réaffectation vérifiée pour les types et modes conservés ; chemins plus complexes encore partiellement couverts |
| E7 et B4 | Suspension jusqu'au dernier usage et distinction des cases | Réemprunt de référence stockée, échange dynamique, remplacement dynamique, ancienne capacité rendue, remplacement par un réemprunt d'une autre case. Fabrique async relayée, réemprunts mutable et partagé d’une capacité mutable stockée, join et EAGAIN. Case voisine accessible, accès concurrent et swap de la case réservée refusés. Omission du lien de réemprunt détectée. Indice dynamique via relais avec deux pools possibles, rejets sur les deux cases et les deux pools, contrôle des bornes et sélection native pour lignes simples et imbriquées. Omission d’une origine détectée | Pas de modèle indépendant des durées de vie des tableaux de références |
| E7 et B4 | La relation de réemprunt survit à une jonction | Programme accepté et variante refusée après remplacement conditionnel entre deux cases | Couverture générée des jonctions encore partielle |
| E7 et D1 | Les tableaux de références transférés gardent des cibles durables | Sorties de branches et boucles, remplacement d'un receveur ancêtre, cibles locales refusées, reprise par continue | Conteneurs de références suivis récursivement ; profondeur et combinaisons générées encore limitées |
| E7 et contrats | Provenances des résultats, exigences de sources et postconditions par case | Retour de tableau et de référence, relais, appels opaques privés des corps et des tables d'inférence, remplacement via alias et ligne projetée. Capture partagée par une fabrique async relayée, avant ou après remplacement de la case. Join, drop, reset et mutation de l’ordre de résolution exercés | Interactions de grande taille non couvertes |
| E7, B1, B2 et B4 | Une ligne prêtée ne suspend pas les capacités des autres lignes | Refus d'emprunter la cible mutable d'une ligne non prêtée ; modification d'une ligne conservée par deux appels | Projection dynamique conservatrice ; pas de modèle indépendant des durées de vie |
| E4, B4a et A5 | La destination reste valide après les effets de la partie droite | Contrat d'écriture via conteneur et via résultat &mut Int ; reset de la cible refusé même sans usage suivant | Chemins choisis ; pas de preuve formelle |
| E6, V4 et D1 | Réaffecter un emprunt change la cible de la variable et conserve les anciens réemprunts | Let mut obligatoire, type/mode identiques, cible locale et temporaire refusées, anciens réemprunts utilisables, conteneurs et resets, paramètres réaffectés, branches et continue/break, autoréemprunt de boucle | Contrôles statiques conservatifs ; pas de preuve générale de convergence |
| E4, E6 et E7 | Une référence stockée vers une ligne garde son type, ses bornes et l'emprunt du tableau entier | Lectures/écritures, copie partagée, replace/swap, retours relayés et contrats opaques, refus du local, indices évalués une fois, modèle de 40 opérations graine 20261106 | Lignes de valeurs ou de références ; voir le cycle récursif ci-dessous, sans modèle général complet des durées de vie |
| E7, reset et enums | Un emprunt de champ conserve aussi la réservation du porteur | Références stockées après appel, résultat mixte case/champ, accès au porteur, drop et resets refusés avant dernier usage | Modèles historiques sans tableaux de références |

### Cycle des lignes contenant des références

| Règle / profil | Invariant, prémisses et interactions | Évidence exécutée | Limites |
| --- | --- | --- | --- |
| E7_TREE — E4, E6, E7, B1–B3 | Les emprunts intérieurs restent actifs avec leur capacité, même quand seule une référence extérieure est nommée | Tests de lecture et écriture, réemprunt mutable, référence d'origine suspendue, accès distinct après dernier usage, contrôle des indices avant effets ; mutation supprimant les prêts intérieurs détectée | Modèle synchrone, types du prototype |
| E7_TREE_CONTRACT — B4, B5, E7 | Le contrat conserve le conteneur et chaque référence intérieure ; les modifications atteignent le stockage réellement visé | Retour et relais opaques, mise à jour via alias et shadowing, remplacement de référence de ligne et retour de l'ancienne, contrat readonly forgé refusé ; emprunt de champ inline installé par relais dans une case ou une ligne injectée ; mutations de contenu et propagation détectées | Pas de preuve formelle de complétude des contrats |
| E7_TREE_PROJECT — E4, E7, B4, D1 | Une ligne retournée conserve ses positions dans le conteneur source | Contre-exemple où verify_program acceptait un reset que compile_source refusait, correction du remappage, refus aux deux stages et mutation détectée | Projections ambiguës réunies de manière conservative |
| E7_TREE_DROP — A2, A5, B1–B5, D1 | Drop/reset ne détruisent aucune cible ni aucun porteur encore utilisé par un descendant | Pools distincts, dernier usage par chemin intérieur, porteur enum et cible, effet de reset dans la partie droite, cibles dynamiques ; modèle indépendant de 12 fenêtres de drop, profondeurs 1 à 3 | 6 cas admis exécutés et 6 refusés ; aucune preuve générale pour toutes les profondeurs |
| E7_TREE_EFFECT — B4, D1, T5–T11, E7, A2/A5 | Consommer le conteneur extérieur ne fait pas perdre les modifications de ses lignes empruntées | Transfert explicite, remplacement du pointeur après écriture, relais et argument temporaire ; allocations distinctes dans le même pool, drop prématuré refusé aux deux stages ; mutations spécifiques détectées | Contrats conservatifs, pas de preuve complète de tous les effets transitifs |
| E7_TREE_FLOW — S4, S5, T5–T11, D1, E7 | Transferts, branches et reprises conservent toutes les cibles possibles | Résultats de branche et loop avec receveur, continue/break, retour local refusé, cibles conditionnelles et union des sources | Convergence et chemins arbitraires restent partiellement couverts |
| E7_TREE_VALUES — E3–E7 | Copy partagé, replace et swap conservent le graphe de destinations sans dupliquer une capacité mutable | Modèle indépendant par indices : 24 opérations, graine 20261107, plus modèles des cycles précédents | Ce modèle compare les valeurs, pas toutes les durées de vie |

La suite globale courante passe : 909 tests distincts. Les 90 tests ciblés
passent également sous UBSan à -O2 (101 invocations acceptées et 194 refusées).
Quinze mutations sont détectées : 8 acceptations indues, 6 faux refus et
1 comportement runtime incorrect. La mutation de propagation a d'abord survécu
au scénario redondant ; le remplacement de pointeur expose son effet nécessaire.
Les 9 tests des diagnostics de réservation passent sous PYTHONHASHSEED=0 et 1.

Le rapport FIXED_ARRAYS_VALIDATION.md décrit les deux écarts confirmés entre
verify_program et compile_source, les corrections, les modèles et les limites.
Les sources, groupes et résultats exécutés sont identifiés dans
validation/fixed-array-current-{global,suite,mutations}.json. Les substitutions
sont rejouables avec validation/run_fixed_array_mutations.py. Aucun modèle
indépendant complet des durées de vie ni preuve générale de sûreté n'est revendiqué.


## Conception async/multithread et retrait de reset — 4 novembre 2026

Référence : [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md).
Rapport : [ASYNC_DESIGN_CYCLE.md](cycles/ASYNC_DESIGN_CYCLE.md).
Les lignes P distinguent les scénarios exécutés des limites connues.
Les profils synchrones historiques ne constituent pas une preuve pour
l’extension async. PR1 est vérifié sur le profil par défaut, avec un
profil historique séparé pour les tests qui exercent reset.

| Règle | Comportement et invariant visé | Interactions | Scénarios à vérifier / limites | Statut |
| --- | --- | --- | --- | --- |
| AS1 | async fn, .await et yield explicites | S1–S5, I5 | Déclarations, yield et .await exécutés, y compris dans les if à comparaison Int et les matchs de handle. Suspension refusée dans fn ordinaire. Court-circuit de && et || avec attente et effets sur l’opérande droit vérifié. while et loop suspendables avec break, continue et résultat Int, tâche ou handle exercés. État mémoire transporté entre itérations encore restreint. | P |
| AS2 | Création inactive et capture immédiate | B4a, AS15, AS16 | Capture &str d’une liaison immuable issue d’un littéral, via découpe et alias dans une fabrique synchrone. Le sous-ensemble initial refusait les captures dynamiques. Leur prise en charge actuelle est détaillée dans AS15. Mutation confondant type et provenance détectée. Retours synchrones &str et &u8 reconnus par contrat lorsque toutes les cibles possibles se ramènent à des arguments statiques. La première vérification limitée au stockage statique refusait les provenances mixtes. La mutation ignorant les cibles est détectée ; les captures dynamiques actuelles relèvent d’AS15. Capture char issu de char_at, relais async et utf8_len après yield sur les quatre largeurs UTF-8. Confusions char/u8/Int refusées. Mutation tronquant char à un octet détectée. Liaisons locales char, réaffectation après yield, if et résultat de loop vérifiés. Branches et break de type incompatible refusés. Mutation omettant la sortie lexicale du type détectée. Capture u8 depuis un indice de &str et relais async par paramètre nommé. Valeur du frame observée après yield sous UBSan fatal. Confusion u8/Int et emprunt Int sur u8 refusés. Mutation remplaçant la valeur relayée par zéro détectée. Liaisons u8 annotées ou inférées, réaffectation après yield et résultat de boucle exercés. Mélange u8/Int dans les break refusé. Mutation omettant le nettoyage lexical du type détectée. Captures Bool, Int, &Int, &mut Int et -> Int préparées de gauche à droite dans les appels synchrones et async linéaires. Argument suspendu après capture et invalidation du receveur transféré testés. Copie Bool avant changement du receveur, relais entre tâches et rejets de confusion Bool/Int exercés. Mutation du contrôle du type détectée. Liaison Bool locale annotée ou inférée, mutation après yield et sortie de bras. Réutilisation du nom en Int vérifiée. Omission du nettoyage du type détectée. Une fabrique et un relais synchrones transmettent une ligne Int injectée en lecture ou en écriture. Le join restitue le prêt de case. Accès incompatible refusé avant spawn et après join jusqu’au dernier usage. EAGAIN et omission de l’origine tableau exercés. Capture directe d’un tableau plat de références partagées. Lecture après yield, accès concurrent partagé, drop et reset des cibles, remplacement du tableau et transfert hors bloc exercés. Omission des prêts des cibles détectée. Le retour de tâche via une fabrique et un relais synchrones conserve le tableau partagé et ses cibles après remplacement. Le drop de la cible remplacée est admis, le drop des cibles capturées et le remplacement après capture sont refusés. Mutation de la reconstruction sur l’état d’entrée détectée. | P |
| AS3 | Instance stockable, non Copy, transfert explicite | T1–T11, D1 | Tâche scalaire nommée non Copy, consommée par drop ou await ; transferts explicites entre receveurs et scopes testés, injection descendante en async et restitution par <- testées. Renommage, spawn et drop depuis un descendant exigent un transfert explicite à chaque niveau. Sorties de boucle synchrone par break <- et branches if ou match synchrones transférant une tâche ou un handle. Match d’enum consommé, partagé et mutable, et match du Result de join exercés. Provenance des résultats alloués jointe, pools locaux refusés et échec de lancement testé sur les deux branches de if. Paramètres synchrones de tâche transférée exercés pour captures scalaires et allocations Int transférées. Paramètre de tâche avec capture mutable transféré à une fonction qui lance la tâche, puis handle relayé et joint. | P |
| AS4 | Démarrage par await et consommation unique | S4, B1–B5 | Attente d’un appel direct ou d’une tâche nommée Int/Void, y compris dans les deux bras d’un match de handle. Reprise du bras choisi et consommation unique vérifiées. Attente directe d’une tâche calculée par bloc, if ou loop. Résultats Int, &mut Int, <- Int et Void vérifiés, dont union des captures retournées et réemploi du slot. Attente Void calculée admise comme instruction ; abandon implicite d’un Int ou Result refusé. Résultat Bool par await d’une tâche inactive, relais et condition. Confusions Bool/Int refusées, mutation du résultat détectée. Spawn et join Bool exercés sous RT5. Résultats Bool attendus dans if et match, tâche choisie avant await, et rejet d’un Int dans un bras. Omission du contexte Bool détectée. Inférence dans une liaison non annotée à partir des bras continuants, y compris via un Bool local à un bras. Jonction Bool/Int refusée et mutation du contrôle détectée. Boucle async à résultat Bool, avec ou sans annotation ou retournée directement. Break après await et reprise par continue exercés. Mélange Bool/Int et annotation incompatible refusés. Les conditions infèrent les opérandes Bool issus d’un if, d’une boucle ou d’une tâche calculée. Évaluation gauche à droite sous suspension et mutation de l’ordre vérifiées. | P |
| AS5 | Création depuis fn ordinaire et retour de tâche | B4, D1, AS7 | Retour nominal <- définition async depuis fn synchrone, avec captures scalaires ou empruntées suivies par contrat. Deux formes de retour et relais testés, y compris les captures transférées depuis un pool injecté ou une allocation paramètre. Pool local refusé. Capture d’un &Int détaché d’un champ partagé relayée par contrat, avec destruction ou consommation du porteur avant spawn. La capture prise avant réaffectation garde l’ancienne cible ; après réaffectation conditionnelle, les deux cibles possibles sont protégées. Mutation du suivi détectée par réemploi du slot. | P |
| AS6 | Type généré propre à la définition async | I5, P8 | Deux états C distincts de même signature et tailles différentes exécutés sous UBSan ; fonctions linéaires Int/Void. | P |
| AS7 | Super pool et injection automatique des pools d’états | I2, A1–A3, P8 | Super pool C initialisé avant main. Les appels Crust synchrones et async passent par les fabriques du type de tâche. L’oracle de réutilisation appelle la fabrique C générée pour un pool de capacité un. Borne conservatrice depuis les emplacements synchrones et les états parents ; directive async_pool_sizes ; cycles explicitement bornés. Les créations indirectes à travers les auxiliaires et méthodes contribuent au graphe et aux bornes par contrat ; cycles configurés et huit parents de trois enfants exercés. Omission de cette contribution détectée après renfort d’un premier test qui la masquait. Voir ASYNC_CAPACITY_CYCLE.md et NATIVE_SYNC_CALLS_CYCLE.md pour les preuves et restrictions. | P |
| AS8 | État persistant et suivi statique | B1–B5, E2–E7 | Captures Int, &Int et &mut Int et temporaires scalaires conservés à travers les reprises. Le pointeur de capture est relu après yield depuis le thread lancé. Les provenances des vues réaffectables dans les boucles sont élargies jusqu’à stabilisation ; l’état généré est émis une seule fois. Les répétitions de validation ne répètent pas les créations de tâche dans le C. | P |
| AS9 | Stockage stable à travers suspension et changement de thread | B1–B5, P3 | ABI C vérifiée lors de reprises sur threads distincts. Un enfant emprunte le champ Int de l’état parent et le modifie après yield. Mutation remplaçant l’adresse par une copie détectée. | P |
| AS10 | Résultat extrait puis nettoyage terminé avant retour d’attente | L1–L7, T1–T11 | Retour &str statique après réutilisation du type de frame enfant. Attentes directe et sur handle, join bloquant, secours sur EAGAIN et conservation de la longueur avec NUL incorporé vérifiés sous UBSan. Mutation annulant la longueur détectée. Résultat &u8 statique via await direct, attente de handle et join, avec deux cibles distinctes entre Ok et secours sur EAGAIN. Mutation substituant l’adresse détectée. Les vues &str et &u8 statiques extraites d’un join peuvent être capturées à nouveau, y compris via des alias immuables. Retour char relayé par await direct, await de handle et join bloquant. Point de code complet observé sous UBSan, échec de lancement externe et mutation tronquant le résultat exercés. Retour u8 après yield puis relais par await direct, await de handle et join bloquant. Valeur exacte, branche de secours et échec de lancement externe exercés sous UBSan fatal. Mutation annulant l’octet au join bloquant détectée. Handle u8 transféré entre deux fonctions synchrones, résultat retourné puis recapturé par un autre worker. Succès et secours sur EAGAIN exercés. Mutation lisant le statut à la place de l’octet détectée. Extraction du résultat avant nettoyage. Une capture -> Int modifiée par le worker est détruite et son slot redevient disponible avant le retour du join. Le drop depuis le worker désarme aussi le nettoyage de fin de tâche. Retour transféré d’un Int par attente directe testé sur deux relais. Adresse et occupation du slot vérifiées jusqu’à la destruction côté receveur. Résultat transféré via handle.await exercé en match direct, résultat nommé, joker et Err simulé. Join bloquant exercé avec match direct ou nommé, joker, drop, passage à une fonction et Err simulé. Retour de l’Int extrait via contrat synchrone exercé avec capture entrante, pool injecté et allocation de secours sur Err. Déplacement du Result entier entre noms et blocs testé dans les deux contextes, ainsi que par break dans les deux contextes. En synchrone, deux sources possibles et nettoyage sur continue exercés. Expressions if testées en synchrone et en async, avec retour anticipé et suspension du receveur async. Match async restituant le Result depuis Ok ou Err exercé, y compris avec sujet nommé. Paramètres et retours synchrones de Result<A<Int>,runtime::Error> par transfert vérifiés sur trois fonctions. Signature async du même type vérifiée à la capture, au drop inactif et au retour par attente directe. Join bloquant et attente suspendue d’un résultat imbriqué exercés avec Ok(Ok), Ok(Err), Err, joker et drop. Le Result extérieur est aussi restitué par if, match et break <- en synchrone et en async. Ses signatures par transfert sont exercées avec les trois issues, y compris par attente directe après yield. | P |
| AS11 | Pas de référence retournée vers un état détruit | D1, B5, L2 | Retour direct ou réemprunt d’un paramètre &Int ou &mut Int admis après yield. Retour d’une référence vers un local refusé. Relais par attente et par liaison suivis jusqu’aux paramètres du premier appel, y compris après bloc, if ou loop qui choisit une tâche emprunteuse. Vues &str et &u8 retournées depuis les captures &String ou &mut String avec provenance conservée chez l’appelant ; retour depuis capture détenue refusé. Retour après join sur un String local refusé même lorsque son pool est injecté. Agrégats encore ouverts. | P |
| AS12 | Provenances du résultat déduites et conservées | B4–B5, D1, T5 | Retour dynamique &str et &u8 par attente directe, attente d’un handle async et join bloquant. Les captures UTF-8 qui peuvent contribuer au retour restent réservées après join, y compris via un contrat synchrone. Capture seulement lue libérée après join, réaffectation conditionnelle conservée, reset historique ciblé et mutation détectée. La sélection de provenance est relayée par await d’un appel direct ou d’une tâche nommée construite par appel. Projection également vérifiée via un handle lancé et attendu, avec union des provenances des bras Ok et Err. Projection via une tâche calculée par if, match, bloc ou loop. Les break imbriqués sont séparés. Mutation effaçant la projection du contrat détectée. Int indépendant ; Option<char> issu de String.pop et les résultats typés de replace_byte et replace_bytes restent indépendants après destruction du String et réemploi du slot, y compris à travers une fonction de join et une autre tâche ; résultat &Int ou &mut Int d’une tâche inactive suivi jusqu’à sa dernière instruction d’usage dans son bloc, avec conservation de l’exclusivité d’origine. Reprises et sorties break/continue testées. Union des paramètres effectivement retournés et composition par relais avec permutation des arguments et nouvelle capture d’un résultat emprunté ; mutations du suivi détectées. Résultats de handle suivis dans les corps async. Les vues retournées depuis des captures &String et &mut String conservent les octets chez l’appelant ; relais attendus ou lancés, résultat calculé, contrats de lancement et de join, handle reçu par transfert et union des deux sources d’un octet conditionnel exercés. La capture non contributrice redevient modifiable. Les payloads &str et &u8 conservent aussi les prêts vers les String locaux au cadre ; le Result nommé et la valeur extraite ont des réservations distinctes. Deux match successifs et sortie de vue du bras exercés, mutation après dernier usage admise, drop précoce refusé. Join synchrone avec &Int ou &mut Int exercé. Réemprunt partagé issu d’une capture exclusive testé en synchrone, y compris sa recapture et son retour par un deuxième worker. Contrats synchrones relayant un résultat de join avec origine exclusive vérifiés, y compris via un handle reçu par transfert. Mutation qui supprime la réservation détectée. Identité de l’Int restitué après join suivie à travers les contrats de création de handle et de retour. Les retours directs distinguent les pools protégés avant join et ceux du résultat après join. L’analyse suit aussi les liaisons de tâche et les relais par await, y compris après lancement. Les résultats de bloc, if, match et boucle sont aussi suivis, avec union des origines sur les branches et break. Les expressions non résolues conservent une union conservatrice. Un relais synchrone qui joint le worker conserve aussi l’ancienne cible du champ sur Ok et la cible de secours sur Err. Agrégats ouverts. | P |
| AS13 | Frontière de scope et durée des pools | A2–A3, D1 | Sortie de tâche avec cible empruntée ou pool de capture transférée du parent exercée. Sortie avec cible ou pool local refusée. Capture d’un champ inline via deux réemprunts mutables et un relais synchrone. Transfert enfant → parent accepté si les porteurs survivent et refusé si un porteur intermédiaire est local, même si le résultat de la tâche est scalaire. Omission du contrôle de ces porteurs détectée. | P |
| AS14 | Destruction avant démarrage | L1–L7, AS10 | Drop et fin de scope nettoient les instances inactives. Réemploi d’un slot de capture -> Int après drop et échec simulé du lancement. Omission du nettoyage détectée. Capture Int importée dans un bras async puis rendue à une tâche Void : destruction unique à await ou au drop inactif. Retour explicite de l’import vers le parent vérifié. Int détenu rendu par bloc, if ou break <- async, avec restitution obligatoire sur continue et réemploi du slot après join. Break <- sans receveur émet un avertissement ; la restitution marquée est contrôlée à la sortie, après les derniers usages du prêt. Renommage explicite d’un Int détenu dans la frame, ordre de destruction conservé et mutation d’ordre détectée. | P |
| AS15 | Captures incompatibles interdites dès création | B1–B4a | Vue &str validée depuis un tableau u8 local et partagée entre deux workers. Écriture refusée après le premier join, puis admise après le second. Mutation omettant la seconde réservation détectée. Vues &str et &u8 d’un String local réservées dès création pour une tâche sans retour de vue. Relais à travers une attente directe et un enfant lancé sur un thread. Abandon de l’enfant refusé, même quand le parent retourne une vue. Mutation supprimant l’obligation d’attente détectée. Mutation et drop avant join refusés, libération après join, EAGAIN ou drop inactif exercée. Mutation supprimant la dépendance détectée. Réservation UTF-8 maintenue dans les contraintes jusqu’au join. Reset historique aliasé refusé via deux contrats synchrones, admis après join. Mutation supprimant la vérification au join détectée. Captures de paramètres synchrones &str et &u8 et relais via alias immuable exercés. Réaffectation de paramètres mutables &str et &u8 avant capture et retour de la tâche vérifiée. Reset historique de l’ancienne source admis après remplacement certain, celui de la nouvelle source refusé. Les deux sources possibles sont protégées après remplacement conditionnel. Deux mutations de propagation détectées. Les réaffectations entre littéral et emprunt gardent la provenance courante. Après création, remplacer la vue laisse le prêt initial réservé jusqu’au join. La jonction où toutes les branches rétablissent un littéral libère la source empruntée, et une mutation omettant cette preuve est détectée. Les branches de if préservent la provenance d’un paramètre UTF-8 même quand l’autre bras retourne un littéral. Les vues statiques calculées par if ou match UTF-8 sont capturables directement ou par alias mutable. Le match sur enum utilisateur est aussi exercé via une fabrique synchrone avec deux variantes, une vue statique ou empruntée, et contrôle du drop avant join. Une découpe du résultat conserve la preuve. Deux appels synchrones successifs propagent la preuve calculée à partir des arguments évalués. Les break d’un loop expression réunissent les vues possibles après continue. La sortie avec vue locale ou type incompatible est refusée. La mutation qui omet les chemins empruntés du résultat est détectée. Le réemprunt partagé explicite &* d’un &u8 conserve la réservation depuis une fabrique synchrone et dans un relais async. Le drop est refusé avant join et pendant l’usage de la vue retournée. Deux mutations du réemprunt détectées. Un bras emprunté garde sa réservation jusqu’au join et la mutation qui efface la preuve de retour est détectée. La désactivation de la preuve à la jonction est détectée. Le retour d’une tâche reconstitue la réservation d’un paramètre mutable canonique. Drop avant join et reprise par continue avec deux sources empruntées exercés. Mutations du contrat et du point fixe détectées. Contraintes d’alias d’un paramètre &str propagées, mutation de sa provenance détectée. Découpe et emprunt d’octet projetés depuis le paramètre synchrone, avec reset aliasé refusé jusqu’au join. Une fabrique synchrone restitue la tâche ou le handle avec sa capture UTF-8 projetée sur le stockage de l’appelant. Reconstitution de la réservation vérifiée par mutation. Un enfant ne peut pas recevoir une liaison Bool comme &Int ou &mut Int. Lecture et écriture sur un Int local à travers yield exercées. Mutation rétablissant la confusion détectée sur les deux modes. Captures mutables directes concurrentes et lecture ou capture partagée après un argument mutable refusées. Réemprunts d’un &mut Int ordinaire testés. Argument suspendu qui tente un emprunt incompatible après préparation de la capture refusé. Deux captures partagées du même champ issues du même writer admises dans un appel, accès via writer refusé. Projections ouvertes. | P |
| AS16 | Effets de capture distincts des effets du corps | B4, L6, AS2 | La capture mutable réserve immédiatement la cible. Le corps ne s’exécute ni au drop inactif ni en cas d’échec de lancement simulé ; le join réussi rend visible la mutation. | P |
| RT1 | Main toujours synchrone | S2, RT5 | main synchrone peut lancer et joindre une tâche Int/Void ; async main refusé. | P |
| RT2 | Runtime générique et interface scheduler générée | AS6–AS10, MT7 | Super pool et callbacks de reprise, extraction et nettoyage intégrés. Interface C interne de lancement et attente exercée sur join, await, fermeture et erreur de lancement. Contournement du callback à la fermeture détecté par mutation. Installation publique et politique de reprise ouvertes. | P |
| RT3 | Scheduler par défaut, remplacement explicite | RT2, RT4 | Ordonnanceur pthread automatique. Injection testée via les points d’entrée C internes. Installation directe dans main avant lancement validée, non implémentée. | P |
| RT4 | Spawn délègue au scheduler ; une seule exécution par instance | AS9, MT1–MT8 | Politique actuelle : un nouveau thread par lancement (permise mais non imposée par RT4). runtime::spawn depuis main et depuis un corps async linéaire, avec création de thread vérifiée par oracle pthread. Transfert direct d’une tâche calculée par appel, boucle, if ou match de join selon le contexte. If async conserve l’union des captures, y compris à travers yield ; match de join teste Ok et Err. spawn_blocking est propagé jusqu’au callback distinct du scheduler dans les deux backends ; voir SPAWN_BLOCKING_CYCLE.md pour les tests et limites. | P |
| RT5 | Handle consommé par join bloquant ou await suspendant | AS4, AS10, MT6 | Join bloquant et await suspendant intégrés pour Int, Bool et Void, avec consommation unique. Bool conservé dans Ok direct et Result nommé, y compris après suspension. Mutation du type détectée. Oracle de disponibilité, succès et échec simulé du lancement. Attente d’un handle choisi par if dans un corps async, résultat nommé ou directement analysé par match, capture mutable retenue sur Ok. Spawn et await chaînés : lancement unique vérifié après suspension forcée, mutation qui relance détectée. Join synchrone sur handle temporaire issu de spawn ou if, avec retour alloué par contrat et réemploi du slot. Effet blocking_join transmis par contrat : accepté derrière des auxiliaires dans un bloc natif, refusé dans un état async, y compris via un relais ; succès et LaunchFailed exercés (NATIVE_SYNC_CALLS_CYCLE.md). | P |
| RT6 | Pas d’annulation ; erreurs métier dans T | AS10, MT3 | Échec EAGAIN simulé pour join et await. Deux captures transférées détruites une fois, réemploi dans deux pools de capacité un, capture mutable intacte. Omission du nettoyage détectée. Result métier imbriqué testé sous AS10. runtime::Error et le motif LaunchFailed sont intégrés aux matchs et signatures propriétaires couverts ; les valeurs autonomes sont intégrées aux liaisons, appels et retours sync/async, boucles et drop. Voir RUNTIME_ERROR_VALUES_CYCLE.md : 19 binaires et 27 refus par niveau, quatre mutations ciblées détectées après renforcement des oracles. Les formes générales de Result restent ouvertes. | P |
| RT7 | Chaque handle doit être attendu explicitement ; obligation transférable ; drop/abandon refusés | AS14, MT3, MT5, U1 | Contrôles sync/async et tests de chemins dans `test_handle_obligations` ; voir HANDLE_OBLIGATIONS_CYCLE.md. Les anciens oracles d’abandon ne testent plus une opération Crust admise ; ils restent des tests C internes historiques. | P — cas exécutés et limites dans le cycle |
| MT1 | Emprunt mutable réservé jusqu’à terminaison établie | B1–B5, AS2, RT5 | Capture directe de &mut Int via transfert de la tâche, yield et join exercée sous UBSan. Lecture, mutation et destruction avant join refusées ; accès autorisé après join. Emprunts de Vector<Int> et String vers les tâches, mutation après suspension et relais par enfant exercés. Lecture scalaire d’octet et char_at sur String dans le corps async. Le résultat copié reste utilisable après mutation ou drop. La réservation du receveur préparé protège l’évaluation suspendue de son indice. Vues locales immuables &str et &u8 issues du String du cadre, alias et relais attendu, suspension et dernier usage vérifiés. Retour vers une collection détenue du cadre refusé. Vues issues de blocs, if et boucles : réunion des sources possibles, dernier usage et refus de sortie vers une source locale détruite. Résultat UTF-8 d’une tâche calculée attendu avec maintien des prêts. Liaisons locales de vues réaffectables : remplacement sans altérer les alias ni les captures enfant, jonctions par if et sorties break, contrôle du scope source, continue avec provenance rétablie. Modèle fini de 16 combinaisons et deux mutations détectées. Résultats UTF-8 de handles : prêts locaux conservés dans le Result et dans le payload, rematch, sortie du bras, handle calculé, copie indépendante d’octet et drop prématuré exercés. Omission de la conservation détectée. Vues UTF-8 transportées par loop/while : élargissement statique et revérification jusqu’au point fixe, derniers usages incluant la reprise, sorties break et while sans itération. Boucles imbriquées, aliases successifs, copie d’octet et nettoyage de tâche inactive en pool de capacité un exercés. Les deux mutations supprimant la revérification ou la vivacité de tête sont détectées. Deux lecteurs du Vector conservent leurs réservations après un premier join. Mutation du mode détectée. Réemprunts par nom ou explicites exercés, y compris d’un résultat async avec maintien de sa cible après le dernier usage du porteur. Capture détachée d’un champ partagé issu d’un writer : lecture et drop du porteur pendant le worker admis, writer et accès direct bloqués jusqu’au dernier usage du résultat. Capture directe d’un champ Int inline depuis une fonction synchrone. Le porteur et son pool restent protégés, un champ frère reste accessible et le résultat conserve le prêt. Une fabrique synchrone et un relais conservent le champ Int inline dans le contrat. Mutation du champ frère admise, écriture de la cible avant spawn et avant dernier usage refusée. Retour sur porteur local et reset hérité refusés. EAGAIN exercé sous UBSan. Omission de la projection dans le contrat détectée. Capture indirecte par un champ partagé avant ou après remplacement, avec relais et alternative conditionnelle. Vérification du drop et du reset sur le pool réellement capturé, puis du prêt restitué par join. Mutation de la résolution après remplacement détectée. Une chaîne de deux champs mutables est exercée avec retour de tâche et de prêt. Drop et reset de chacun des trois objets sont refusés avant spawn et avant dernier usage du résultat. Deux champs inline distincts passent par les paramètres scalaires d’une fabrique. Le second champ redevient accessible au join tandis que le résultat réserve le premier. Capture double de la même case et accès prématurés refusés. EAGAIN et omission de la reconstruction du prêt exercés. Les chaînes hétérogènes restent à approfondir. | P |
| MT2 | Lectures partagées et réservations multiples | B1–B5, RT5 | Deux tâches lisent le même Int avec l’appelant sous UBSan. Écriture, drop et emprunt mutable refusés après un seul join et écriture admise après les deux. Deux mutations du vérificateur détectées. Deux workers partagent aussi une cible issue du même writer via un champ détaché. Le premier join, y compris sur Err, ne rend pas le writer accessible. Deux résultats de join nommés prolongent la réservation au-delà des deux joins jusqu’au dernier usage. | P |
| MT3 | Preuve par chemin avant destruction de dépendances | S4–S5, L1–L4, RT6–RT7 | Perte de handle avec capture locale refusée. Retour anticipé du bras Err accepté après attente de l’autre enfant et refusé sans cette attente. Les seuls chemins continuants des matchs de handle et des if à comparaison Int participent à la jonction. Boucles async avec nettoyage à chaque itération. Reprises stables et états de sortie distincts de l’entrée. Attente d’un worker extérieur sur deux sorties break exercée, sortie non jointe et test faux de while incompatibles refusés. Break, continue et return avant attente d’un worker local refusés. Contrats et jonctions plus générales ouverts. | P |
| MT4 | Enfant empruntant un état parent stable | D1, AS9, MT3 | Emprunts des captures et des Int locaux du parent conservés jusqu’au .await. Accès prématurés refusés et mutation visible dans l’état parent. Spawn d’un enfant empruntant un Int local du parent dans une boucle, mutation visible après await et réemploi du slot à l’itération suivante. Transfert du handle hors bloc vérifié en synchrone et async. Cible de bloc refusée à chaque remontée. Tableau Int fixe du parent stocké dans son état. Capture d’une case partagée ou mutable, écriture disjointe, indice dynamique vérifié, et conservation du prêt par le résultat emprunté exercés. Pour un tableau imbriqué, une différence constante sur une coordonnée prouve la disjonction. Le contrôle d’un indice précède l’évaluation suspendable de l’indice suivant. Les paramètres de tableau partagé ou mutable peuvent recevoir une ligne depuis une autre tâche async. Une réservation de ligne couvre ses descendants et laisse les lignes disjointes accessibles. Réemprunt de ligne et de case exercés. Retour de &Int ou &mut Int depuis une ligne empruntée, directement ou par relais, avec réservation de la ligne jusqu’à l’attente, puis des chemins de résultat possibles jusqu’au dernier usage. Retour depuis une ligne locale refusé. Depuis une fonction synchrone, une case ou une ligne Int peut être capturée avec prêt du tableau jusqu’au join ou au drop de la tâche inactive. Sortie du tableau et drop du handle actif refusés. Les lectures, écritures et nouvelles captures directes de projections constantes disjointes restent disponibles avant join. Une capture via une vue de ligne de provenance connue compose le chemin de la vue et celui de la case. Les emprunts ordinaires conservent la règle E6. Une coordonnée dynamique conserve la protection des cases compatibles. Un join synchrone peut restituer une case inline, avec protection dans le résultat nommé et le bras Ok, puis libération au dernier usage. Le bras Err libère le prêt. Un résultat mixte peut désigner une case inline ou une allocation de pool. Les deux possibilités restent protégées dans le résultat et son bras Ok. Une référence de case issue d’un join peut être recapturée par son nom ou par réemprunt explicite. Une lecture partagée issue d’une vue mutable suspend aussi cette vue. La recapture d’un résultat mixte conserve séparément le chemin inline et la provenance du pool, jusque dans le résultat du deuxième join. Sortie sans attente et transfert au-delà de la durée de vie du tableau refusés. Transmission d’un tableau plat de références partagées du parent à l’enfant. Await direct et await d’un handle, yield du parent, EAGAIN sur l’enfant, rejet du type incompatible et sortie sans attente. Omission du prêt enfant détectée. Transmission exclusive d’un tableau plat de références mutables, écriture indirecte après yield, visibilité après join, rejets de lecture, écriture et échange pendant le prêt. Mutation du mode détectée. Réemprunt d’une référence stockée par un enfant, sélection dynamique et prêt conservé par le résultat de await. Mutation qui omet le prêt du résultat détectée. Projection d’une ligne inline vers un enfant partagé ou mutable. Bornes et composition du chemin jusqu’au join exercées. Omission du préfixe détectée. Tableau Int imbriqué prêté depuis le synchrone, relayé par await, échangé et copié par ligne. Résultat projeté après join. Mutation du pas mémoire détectée. Modèle indépendant par listes sur trois formes non carrées pour remplacement et échange de lignes. Capture depuis le synchrone et depuis l’état d’une tâche, bornes dynamiques et mutation de la largeur échangée vérifiées. | P |
| MT5 | Contrat de handle conserve cibles et sources | B4, D1, A2–A3 | Handle avec capture UTF-8 transmis et retourné par contrat, puis attendu. Abandon transitif refusé pour une capture dynamique et admis pour un littéral. Reset aliasé historique refusé. Mutation supprimant la précondition détectée. Transfert de handle entre blocs synchrones avec conservation de ses captures. Renommage, transferts entre blocs async et résultat de boucle, avec vérification de la durabilité et union des captures possibles. Retour de handle par contrat synchrone exercé avec captures empruntées ou transférées, relais, erreur de lancement et pool de capacité un. Paramètres synchrones de handle transféré avec capture Int détenue et source relayée exercés. Une capture de tableau passe par les contrats synchrones de relais, lancement et attente. Si le paramètre async est déclaré comme emprunt de tableau, un join dans la fonction synchrone peut utiliser le résultat emprunté et le relayer à l’appelant. Provenance projetée conservée avec un retour conditionnel sur un pool de secours. Paramètre async scalaire &Int ou &mut Int pouvant désigner une case inline ou une allocation. Même relais exercé avec les deux stockages. Contrat projeté disponible en vérification opaque du script. Les conflits pendant l’évaluation des arguments restent protégés. Capture mutable relayée via des paramètres de tâche et de handle, puis résultat partagé relayé via deux contrats. Accès et alias prématurés refusés dans les deux ordres d’arguments. Arguments calculés par if, loop et match gardent toutes les captures actives pendant les arguments suivants. Contrats de tâches et handles choisis par if, loop ou match : union des deux pools de capture et du résultat alloué, vérifiée à travers deux fonctions. Handle lancé avant réaffectation d’un champ partagé, retourné par deux fonctions. Le contrat protège la cible capturée, même après drop du porteur. Succès, EAGAIN et refus du recyclage prématuré vérifiés. | P |
| MT6 | Result conserve les emprunts retournés | B4–B5, AS12, RT5 | &Int et &mut Int transportés dans le Result de .await en contexte async. Écriture prématurée refusée avant match et dans Ok. Err simulé libère la cible sur ce chemin. Join synchrone testé avec match direct, Result nommé, drop et Err simulé. Résultat &Int ou &mut Int d’un tableau plat de références, transmis par await puis join. Projection constante précise, indice dynamique conservateur. Mutation qui garde toutes les cases pour un indice constant détectée. Retour et relais synchrones après création directe puis join, en partagé et en mutable. Indice dynamique et cible de secours sur EAGAIN conservés. Mutation de la projection dans le contrat détectée. Composition fabrique distincte, transfert de tâche et join interne vérifiée. Un remplacement avant capture change la cible du résultat. Omission de la mise à jour détectée. Capture d’un tableau de références à lignes inline, chemin imbriqué conservé par une fabrique et un join synchrone. Bornes, projection partagée et mutable et mutation d’une coordonnée exercées. Lignes elles-mêmes référencées capturées en partagé et mutable. Réservation des lignes intermédiaires, bornes et résultat relayé par fabrique et join. Omission de la réserve intermédiaire détectée. Chemins mixtes partagés et mutables lus sous UBSan. Mutation directe et réemprunt mutable à travers un lien partagé refusés, retrait du contrôle détecté. Résultat partagé issu d’une capacité mutable garde la réservation. Agrégats ouverts. | P |
| MT7 | Métadonnées de pools sûres en concurrence | P8–P9, L1, AS7, RT7 | Tickets atomiques pour états de tâches. Curseur, index et liens de slots de données protégés par un mutex dans le C multithread. Drop de capture Int concurrent et 16 000 cycles natifs à quatre threads sous UBSan. Les fronts de croissance et les classes de régions sont protégés par un verrou pris avant celui des slots. Oracle C à deux threads sur une réserve de 257 octets et recyclage concurrent de régions. Mutation détectée par débordement de curseur. ThreadSanitizer indisponible dans l’environnement. Suppression du verrou détectée. L’oracle RT7 exerce aussi quatre récupérateurs concurrents pour un seul slot abandonné, sur 32 cycles. Vecteurs et régions partagés entre tâches ouverts. | P |
| MT8 | Transfert et partage déduits structurellement | B1–B5, P9, E7, D1 | Int transféré au thread via pointeur stable, puis détruit dans son pool d’origine. String capturé par ->, modifié après yield puis détruit dans son pool. Deux Strings du même pool lancés sur deux workers, relais synchrone de handle, échec EAGAIN et drop inactif exercés. Mutation du nettoyage détectée. Vector<Int> et Vector<u8> capturés par -> via un relais synchrone, croissance après yield, longueurs et réemploi du pool vérifiés. Lecture Int et borne runtime exercées, mutation des valeurs ajoutées détectée. Lectures et écritures indexées Int/u8, indice suspendu évalué avant le RHS, absence de mut et confusion u8/Int exercées. Mutation de lecture u8 détectée. Le relais parent async vers enfant lancé conserve le nettoyage du Vector et refuse l’abandon du handle. Retour scalaire après attente et drop de l’enfant inactif réutilisent le slot. Mutation de l’obligation d’attente détectée. Retour détenu de String et Vector<Int> par join synchrone avec type, contenu et adresse conservés. Résultat ignoré et échec de lancement libèrent le slot. Les contrats synchrones acceptent le Result typé de String et Vector, transmettent les provenances et refusent le mauvais type de payload. Mutation du type à la réception détectée. Result de String relayé par une tâche, enveloppé par un second join et extrait deux fois. Succès, EAGAIN interne/externe, capture par transfert du Result et jonction conditionnelle exercent la conservation du type et du pool. Mutation du type imbriqué détectée. Réception détenue après await direct et attente de handle, Result nommé ou match immédiat, avec type du contenu et nettoyage conservés. Relais et mutation après réception exercés pour String et Vector<Int>, y compris EAGAIN interne. Mutation du type du Result détectée. Collection reçue après await puis transmise par bloc, if ou break de loop. Réaffectation de collection détenue par move, await, bloc, if et loop. RHS lu avant destruction, type conservé, nettoyage unique et retour de la même allocation par await exercés. Mutation omettant la destruction détectée. Mélange String/Vector entre les bras refusé. Les autres collections restent ouvertes. Déduction structurelle pour objets et types externes ouverte. | P |
| PR1 | Retrait de reset, nettoyage par drop et scope | A5 historique, L1–L7, P8–P9 | CLI et API Python refusent reset par défaut ; réutilisation par drop et nettoyage en fin de scope exécutés ; C par défaut sans fonctions de reset et oracle direct des slots exécuté sous UBSan. Le profil historique exige une option explicite. | P |


## Data stacks et régions grandissantes — 4 novembre 2026

Référence normative : [GROWING_REGIONS.md](GROWING_REGIONS.md).
Rapport de cycle : [GROWING_REGIONS_CYCLE.md](cycles/GROWING_REGIONS_CYCLE.md).
G2–G12 ont une couverture partielle dans le compilateur ou dans le C émis.
G1 reste N. Les preuves historiques des pools fixes ne
constituent pas des preuves des régions ou des deux fronts.

| Règle | Comportement et invariant visé | Interactions | Scénarios à vérifier / limites | Statut |
| --- | --- | --- | --- | --- |
| G1 | Réservation anticipée sans avancer la construction ni déplacer la valeur | P3, T1–T11, D1, A2–A3 | Remontées rectilignes, branches de if et de match nominal et suffixes de boucle qui se terminent par break transféré, avec Int sur data stack ; descripteurs de String et Vector, structures et bras d’enum réservés dans leurs pools ; région annotée anticipée dans une classe active ou créée si les temporaires ont le même gabarit, ouverture à froid avec retour au placement ordinaire en cas d’échec, front descendant anticipé avec un seul Vector temporaire non annoté et plage dédiée anticipée si les temporaires occupent les fronts nécessaires ; effets de construction testés. Match non consommant avec région de String et même pool sur les deux bras, sources différentes et manque de place exercés. | P |
| G2 | Croissance au sommet et restauration seulement après nettoyage | P4, L1–L5, S4–S5 | Restitution du curseur réservé par le front, sous modèle C ; placement de scope et transferts ouverts. | P |
| G3 | Deux curseurs opposés, un seul front permis | P1, P5, P6 | Deux fronts C actifs, adresses stables et ordre logique des Vector descendants exercés, y compris subdivision de tranche. TX21 impose les vues String en ordre physique croissant. String utilise un front montant ou une région, puis une plage dédiée si le front montant est occupé. Les vues de Vector<u8> peuvent utiliser le sens descendant. | P |
| G4 | Collision = espace épuisé, contrôles alignement et calculs | P1, P5, E1 | Ajustement exact, alignement, collision et demandes de taille extrême testés. Capacité logique impaire avec coexistence région et fronts exercée sous UBSan à O0 et O2. Sans alignement de la borne de région, accès Cell mal aligné reproduit. | P |
| G5 | Région sous-stack distincte du slot bloc et du descripteur | P8, G3 | Curseur interne et capacité fixe par région. Descripteurs de String et Vector intégrés, dont réservation avant construction et réemploi après nettoyage. | P |
| G6 | `#(directive, stack_region_max_size=1M)` avant scope, limite par région et non par stack | P2, I1–I4, G7, U1 | Syntaxe catégorisée obligatoire, héritage et limites après transfert exercés à O0/O2 avec UBSan ; 3 mutations détectées. M/G binaires provisoires ; blocs annotés async encore refusés. [Cycle directives](cycles/DIRECTIVES_CYCLE.md). | P |
| G7 | Héritage remplaçable ; limite conservée au transfert | P2, T1–T11, D1, A2–A3 | Héritage et substitution lexicaux exécutés par le test des annotations, avec isolation de l’appel et restauration après sortie de bloc. Observateur remis en conformité avec Compiler.statements. Transfert de String sans changement de stockage. | P |
| G8 | Régions de même gabarit gérées comme slots de pool | P4, P8–P9, G6–G7 | Le modèle C vérifie la préférence du curseur, le réemploi d’un trou à la limite et le retrait du suffixe de l’index ; classes dans une réserve commune, recyclage des classes vides et repli dédié testés. À la limite, la réservation de transfert compte les trous dans le pool de descripteurs et dans la classe de régions. Elle laisse le nombre nécessaire de places aux temporaires. Deux mutations détectées. Un programme Crust avec construction et push_str littéral réutilise ces trous avant le transfert. Le cas avec vue empruntée exerce le placement ordinaire. | P |
| G9 | Stack courante puis dédiée, sans heap caché ni dépassement de borne | I2–I3, P7, A2–A3 | Placement C sur front ou classe compatible, puis plage dédiée ; limite et adresses vérifiées. String utilise un front montant ou une région et se replie sur une plage dédiée lorsque le front montant est occupé. Vector peut exploiter les deux fronts. | P |
| G10 | Destruction avant réemploi ; aucune récupération de valeur vivante | L1–L7, P4, P8, PR1, MT7 | Le runtime refuse une fermeture avec front vivant et un faux descripteur ; nettoyage de contenu et intégration scope ouverts. | P |
| G11 | Réservation distincte de engagement ; performances à mesurer | P1–P2, G8–G9 | Mesures sur macOS arm64 du mmap, des défauts de page, du RSS, du recul et de la réutilisation avec ou sans régions. Comparatif mutex global et mutex par datastack de 1 à 8 threads, avec bandes distinctes. Fermeture et restitution inter-thread exercées sous UBSan. ASan bloqué sur un témoin minimal avec les deux Clang. Seuils et free_pages exercés sur les deux datastacks sous UBSan, y compris restitution autour d’une région transférée et sorties async. Mesure intégrée de la restitution fixe sur un programme de 300 itérations. Débit régional intégré à mesurer. [Rapport](G11_DATASTACK_BENCHMARK.md). | P |
| G12 | Stabilité ne dispense pas de vérifier les emprunts et sources | B1–B5, D1, E7, AS9, MT1–MT8 | Modèle de croissance et témoins Rust instrumentés sous UBSan : vecteur par await et spawn/join, String par spawn_blocking/await, entrée de HashMap après transfert, croissance et réemploi. Emprunts portés par le résultat et durée de vie du pool contrôlés par des refus. HashMap async par valeur et captures possédées de runtime::thread validées sous UBSan, avec stabilité, refus de durée de vie et réemploi après échec de lancement. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#g12--stabilité-emprunts-et-provenance) | P |


## Structures et méthodes — 5 novembre 2026

Référence normative : [STRUCTURES_METHODS.md](STRUCTURES_METHODS.md), et I6
dans [LANGUAGE_RULES.md](LANGUAGE_RULES.md). Rapport :
[STRUCTURES_METHODS_CYCLE.md](cycles/STRUCTURES_METHODS_CYCLE.md).
La consignation initiale classait ST1–ST18 et ME1–ME4 au statut N. Les lignes ci-dessous donnent la couverture partielle actuelle.
I6 est un objectif examiné au niveau de la conception (A), sans preuve générale.
Les exemples de conception restent des obligations dont les preuves sont
indiquées par les lignes ci-dessous. Les cas de déplacement de champ et de nettoyage partiel ont été retirés
par la décision finale ST15 ; ils ne sont pas des objectifs d'acceptation.

| Règle | Comportement et invariant visé | Interactions | Scénarios à vérifier / limites | Statut |
| --- | --- | --- | --- | --- |
| I6 | Rapprocher intention et code lisible ; signaler les implicites et notations fragiles | I1–I5, ME2–ME4 | Objectif de conception ; aucune preuve générale intention/code ni évaluation de génération IA. | A |
| ST1 | Structure complète et champs directement contenus dans un slot | V1, P8, D1 | Construction, transfert et destruction d'une structure plate avec un seul slot dans `test_foundation_rules.py`. | P — structures imbriquées dans un seul slot, défauts et initialisation nommée des champs terminaux vérifiés |
| ST2 | Pool.new construit T, type inféré ou annotation vérifiée | I2, A1–A4, P8 | Transfert, réemploi du slot, C identique avec annotation compatible, type incompatible refusé avant génération dans `test_foundation_rules.py`. | P — Pool<Int> et structures plates, annotation des liaisons d'allocations |
| ST3 | Int=0, défaut récursif ; aucune référence par défaut | V1, B1–B5 | `Pool<Int>.new()` donne 0 ; champs Int omis initialisés à zéro et défaut de référence refusé dans `test_foundation_rules.py`. | P — défaut récursif Int, refus d’une référence imbriquée sans cible |
| ST4 | Champs nommés, omissions avec défaut et arguments gauche → droite | B4a, ST1–ST3 | Ordre écrit, doublons, noms inconnus et reset pendant l’évaluation testés dans `test_foundation_rules.py`. | P — champs Int et références Int directs ou nommés par chemin, ordre écrit et omissions imbriquées avec défaut. Backend Rust : new(), new({}), champs contextuels et nominaux, défauts récursifs et refus d’un A<T> omis. Construction directe du littéral immédiatement consommé vérifiée dans le C généré. |
| ST5 | Mutation Int en place exige accès mutable | V4, B1–B5, L1–L6 | Adresse stable, écriture imbriquée via &mut, prêt global et reset du porteur dans `test_foundation_rules.py`. | P — champs Int directs et imbriqués, prêts de champs Int et du porteur |
| ST6 | Réservations indépendantes de champs Int distincts | B1–B5, L6 | Appel avec deux prêts mutables disjoints, mêmes champs conflictuels, alias partagés et destruction prématurée dans `test_foundation_rules.py`. | P — champs terminaux Int |
| ST7 | Réservations par chemin imbriqué et englobants | B1–B5, E7 | Chemins Int imbriqués disjoints, accès au porteur refusé dans `test_foundation_rules.py`. | P — emprunt de sous-structure et cibles indirectes à couvrir |
| ST8 | Contrat des cibles de champs retournées | B4–B5, D1 | Union de chemins via relais opaque, retour en tableau fixe et mise à jour de cases injectées dans `test_foundation_rules.py`. | P — champs terminaux Int |
| ST9 | Emprunt de l’argument compatible avant exploitation du contrat | B4a, B4, ST6–ST8 | Appel avec &mut vers le porteur refusé pendant un prêt partagé de champ dans `test_foundation_rules.py`. | P — porteur et retours de champs Int |
| ST10 | Réaffectation de champ référence sans destruction de ses cibles | B1–B5, D1 | Copie de l’ancienne cible, adresse stable, union des cibles au retour et cible locale refusée dans `test_foundation_rules.py`. | P — porteurs directs et emprunts locaux, champs partagés et mutables réaffectés par contrat, relais, jonction et durée de vie vérifiés ; réemprunt du champ mutable réaffecté vérifié en résultat direct et tableau fixe ; sélection de plusieurs porteurs propagée par relais, avec affectation directe ou via appel, et porteurs locaux distingués dans un même pool, y compris sous masquage lexical |
| ST11 | Réemprunt mutable réserve le champ de capacité | B1–B5, ST7 | Deux champs disjoints réempruntés, frère accessible, même chemin et drop/reset prématurés refusés dans `test_foundation_rules.py`. | P — champs &mut Int et projections &mut vers structures. Deux champs projetés sont admissibles dans les deux ordres, deux projections du même champ sont refusées. |
| ST12 | Contrat conserve cible et réservation du champ mutable | B4–B5, ST8–ST11 | Retour conditionnel par relais, tableau retourné, frère Int accessible et réservations du porteur et de la cible dans `test_foundation_rules.py`. | P — retour direct ou en tableau après réaffectation du champ couvert, reset interprocédural des cibles de champs frères encore conservatif. Un appel retournant le premier de deux réemprunts nominaux libère le champ frère et conserve la réservation du champ retourné. |
| ST13 | Référence partagée retournée détachée du stockage du porteur | B4–B5, D1 | Drop et réemploi du slot du porteur, retour direct et en tableau fixe, cible externe protégée et copie &mut refusée dans `test_foundation_rules.py`. | P — champs &Int de porteurs empruntés ou consommés, relais et réemploi de slot. Lecture scalaire explicite via un champ imbriqué avant et après réaffectation, y compris via contrat. Drop, reset et réemprunt mutable prématurés refusés. Réemprunt explicite partagé suivi jusqu’à sa cible initiale après réaffectation, destruction et réemploi du porteur. Après réaffectation conditionnelle, les deux cibles possibles restent protégées par le contrat relayé. |
| ST14 | Référence vers champ inline conserve le porteur | B4–B5, D1, A2–A3 | Drop du porteur et retour après transfert du porteur refusés dans `test_foundation_rules.py`. | P — champs terminaux Int |
| ST15 | Extraction non Copy et initialisation partielle interdites | T1–T11, L1–L6, ST1 | Déplacement d’un champ &mut direct refusé, transferts entiers et réemprunts exercés dans `test_foundation_rules.py`. | P — initialisation imbriquée par champs terminaux testée, variantes conditionnelles à couvrir |
| ST16 | Remplacement complet : construire avant détruire | V3, L1–L6, P8 | Deux adresses, réemploi de l’ancien slot, diagnostic avec capacité un et emprunt futur refusé dans `test_foundation_rules.py`. | P — remplacement direct par constructeur transféré |
| ST17 | Copiabilité déduite récursivement, copie explicite | E3, E7, MT8 | Champs Int imbriqués indépendants, référence partagée conservée et champ &mut imbriqué refusé dans `test_foundation_rules.py`. | P — types de champs actuellement pris en charge |
| ST18 | Copie locale sur la data stack destinataire ; Pool.copy explicite ou copy via pool d’origine pour une allocation de pool | I2, B4, P8, E3, ST17, D1 | Slots distincts, pool destinataire explicite, origine conditionnelle et capacité dans `test_foundation_rules.py`. Copie locale indépendante, réemploi, transfert de bloc, continue/break, retour et copie d’un paramètre emprunté via deux appels. | P — copie locale exercée à O0/O2 avec UBSan bloquant ; références partagées conservées, drop/reset prématurés et champs non Copy refusés ; deux mutations ciblées détectées. Copie de pool existante rejouée. Voir STORAGE_DESIGN_CYCLE.md pour la portée exacte et les formes restantes. |
| ME1 | Signature du receveur dans impl, règles des fonctions héritées | B4, V4, L1–L6 | Contrats qualifiés, trois modes de self et résolution des effets après if, match et loop dans `test_foundation_rules.py`. | P — méthodes de structures et homonymes intégrés distingués par type pour les receveurs nommés, dont join et split_at_mut. Arité par type, contrat de retour et découpe native du vecteur vérifiés. Les deux homonymes sont également vérifiés dans un bras de match mutable sur une projection, avec retour du prêt hors du match et relais par contrat. |
| ME2 | Emprunt automatique du receveur sans consommation implicite | I1, I6, B1–B5, V4 | Lecture, mutation et réemprunt via relais ou résultat directement en argument dans `test_foundation_rules.py`. | P — receveurs nommés, réservations d’arguments testées |
| ME3 | Nom méthode distinct de chaque champ du type | I6, ME1–ME2 | Collision champ/méthode et doublon de méthode refusés, nom partagé entre types accepté dans `test_foundation_rules.py`. | P — structures |
| ME4 | Receveur consommé explicite : (-> valeur).methode() | I1, I6, T1–T11, ME1 | Consommation explicite, absence de flèche, usage après transfert et réemploi du slot dans `test_foundation_rules.py`. | P — receveurs nommés |


## UTF-8, str, char et String — 5 novembre 2026

Référence normative : [UTF8_STRINGS.md](UTF8_STRINGS.md).
Rapport de cycle : [UTF8_STRINGS_CYCLE.md](cycles/UTF8_STRINGS_CYCLE.md).
TX1–TX20 ont une couverture partielle. Le rapport sépare les essais
natifs exécutés des scénarios encore ouverts.
Les preuves des tableaux/pools historiques ne vérifient pas l'invariant UTF-8.
Les points ouverts sont signalés ; le premier cas de Vector reste seulement
proposé et n'est pas ajouté comme décision normative.

| Règle | Comportement et invariant visé | Interactions | Scénarios à vérifier / limites | Statut |
| --- | --- | --- | --- | --- |
| TX1 | str minuscule, vue UTF-8 et littéraux statiques | I2, D1, L2 | Retour et appels, données C statiques, longueur explicite et octet nul interne dans `test_foundation_rules.py`. | P — vues statiques |
| TX2 | u8 distinct du char Unicode indépendant | ST17, E3 | Octet de continuation lisible ; passage et retour de u8 ; coercions Int et emprunt/valeur refusées. char circule indépendamment de sa vue dans des paramètres et retours. Tableaux fixes de u8 avec constantes bornées, appels et réemprunts. Les contextes async u8 (capture, liaison annotée, retour, écriture de Vector et replace_byte) acceptent un littéral borné ; une variable Int reste refusée sans conversion. Exécutions natives des valeurs et refus des bornes hors 0–255. | P — tableaux d’octets et vues statiques ; littéraux contextuels exercés à O0/O2 avec UBSan fatal |
| TX3 | byte_len et utf8_len explicites | E1, G4 | été = 5 octets ; largeurs de char 1 à 4 comparées au modèle indépendant. | P — byte_len et utf8_len testés depuis Crust |
| TX4 | Découpe textuelle empruntée explicitement sur frontières UTF-8 | B1–B5, D1, E2, I6 | Quatre formes de bornes, retour de fonction, ordre des effets, vues sans copie et mutations des deux gardes ; bornes invalides refusées ou diagnostiquées. Découpe statique async avec deux bornes suspendables, vérifiées dans l’ordre. Vue statique produite par if, loop et match de handle. Chemins Ok et Err exercés, branche Int refusée et mutation du contrôle de type détectée. | P — stockage statique, tableaux d’octets et String ; politique d’échec validée par le brouillon 07. try_slice synchrone : oracle de 144 plages, contrats à plusieurs sources, drop/reset, identité des vues ascendantes et descendantes, O0/O2 UBSan et trois mutants détectés. UTF8_TRY_SLICE_CYCLE.md : 124 régressions et les deux modèles UTF-8 passent ; alias de Result et remplacement de provenance exercés. Extension async exercée : captures de Result, bornes suspendables, relais await, join synchrone et attente de handle async, provenance conditionnelle et exclusion des captures utilisées seulement comme bornes. Voir la deuxième étape du cycle : 147 régressions passent, puis huit régressions ciblent le contrôle U1 corrigé ; quatre mutants async détectés. Aucune preuve générale ; reset aliasé dans une borne ou un argument vérifié par contrat et mutation |
| TX5 | Index simple retourne u8 ; &index donne &u8 | E2–E3, B1–B5 | Valeur, emprunt partagé et réaffectation de la vue ; ordre des effets ; invalidité littérale refusée ; garde native avant accès dynamique. Lecture async après suspension du receveur et de l’indice. Octet de continuation restitué par join, garde dynamique et mutation inversant les effets exercées. Emprunt statique &u8, réaffectation du receveur et relais à une tâche qui déréférence après yield. Mutation supprimant la lecture et capture d’une cible dynamique exercées. | P — vues statiques et emprunts à [u8; N] ou String |
| TX6 | char_at depuis index en octets avec erreur typée | TX1–TX5, E1 | 522 valeurs scalaires et tous leurs octets de continuation ; texte vide, indice négatif et fin ; mutations des gardes détectées ; match typé, transferts et réemploi de pool exécutés. Match direct async sur vue statique, indice suspendable et trois issues vérifiées. Résultat de décodage nommé, copié et réaffecté, puis lu après yield. Capture par valeur et relais async vérifiés après réaffectation du résultat original et drop du String décodé. Familles incompatibles refusées aux appels. Err(_) sur les deux familles est admis aussi en synchrone ; Option et Result restent distincts, retrait du support du joker détecté par mutation. Retours des deux familles via await direct, attente de handle et join. Statut de décodage distinct de l’échec de lancement, mutation du statut interne détectée. Changement de famille refusé et mutation du contrôle détectée. Mutation ignorant l’indice détectée. | P — match instruction et expression des résultats UTF-8 ; reset aliasé dans une borne ou un argument vérifié par contrat et mutation |
| TX7 | from_str exige exactement une valeur scalaire Unicode | TX1–TX3 | Vide, texte multiscalaire et conversion réussie pour chaque scalaire du modèle ; mutation du contrôle de longueur détectée ; match et passage du char par fonction exercés. Match direct async de char::from_str avec texte vide, scalaire unique et plusieurs scalaires. | P — match instruction et expression des résultats UTF-8 |
| TX8 | from_utf8 valide les octets et produit une vue sans copie | B1–B5, D1 | Validation C comparée au décodeur strict de Python ; identité de la vue ; résultat local, dernières utilisations et écritures conflictuelles vérifiés. | P — tableaux fixes et tranches de Vector<u8> en ordre logique, vue sans copie vérifiée par adresse, retour avec provenance, refus de mutation et modèle Python sous UBSan ; autres formes de stockage grandissant à vérifier |
| TX9 | String encapsule Vector<u8> et garantit UTF-8 valide | G1–G12, ST1 | Construction vide et ajouts UTF-8 dans le stockage d’octets grandissant ; intégration au Vector générique ouverte. | P |
| TX10 | Slot de String et stockage grandissant associé nettoyés | P8, G1–G12, L1–L7, PR1 | Placement par annotation, transfert, destruction du stockage avant restitution du slot et réemploi exécutés. Nettoyage et sous-vues testés en contexte synchrone. | P |
| TX11 | push encode un char complet après contrôle de capacité | G4, G12, B1–B5 | Encodeur partagé vérifié sur les largeurs 1..4 ; append complet, limite exacte et dépassement exercés dans le C. Receveur async réservé avant un argument char suspendu : autre String modifiable, lecture et mutation du même String refusées ; mutation retirant la réservation détectée. | P |
| TX12 | Vue &str explicite depuis String sans copie | B1–B5, D1, TX4, AS8, AS11 | Vue et octet retournés par contrat, identité C, mutation après dernier usage, refus de mutation, transfert, destruction et reset précoces. Dans un cadre async : vue locale immuable et octet, alias, relais attendu et tâche calculée ; résultats de bloc, if et boucle conservant toutes les sources possibles. Mutations et drop précoces refusés, slots détenus réutilisés après join, sortie vers String local détruit refusée. Liaisons réaffectables, alias conservés, branches, break et dernier usage au sein du scope source exercés. Projection vers l’appelant depuis &String ou &mut String, relais et contrats synchrones, handle transféré et octet à deux sources exercés. Point fixe des provenances de vues à la reprise de loop/while, avec continue explicite ou implicite, modèle concret de zéro à trois itérations et deux mutations détectées. Ces cas ne couvrent pas toutes les projections d’agrégats ni les corrélations entre origines. | P |
| TX13 | push_str copie le texte source après contrôle complet | B4a, G4, G12 | Copie du &str, accès mutable, capacité et identité du contenu testés ; copie depuis un autre String admise, alias du receveur refusé. Argument &str conservé pendant push_str async, y compris bloc/if/boucle : auto-emprunt refusé, copie vers autre String admise. Réservation dès le début de l’évaluation d’un argument suspendu : mutation et lecture concurrentes du receveur refusées, effets sur une source distincte admis. Mutation omettant la réservation détectée. Une vue du parent dont le dernier usage est dans un bloc enfant expire avant la réservation suivante ; usage de vue dans l’argument ou après l’ajout protégé. | P |
| TX14 | pop retire un char complet et retourne Option<char> | L1–L7, G10, TX2, AS8–AS12 | None sur vide, Some indépendant, match expression, modèle de 120 transitions sur front et région, suffixe réutilisé et emprunt bloquant. En async : résultat conservé après yield, captures et retours Option<char>, join via contrat, destruction puis réemploi de slot, échec de lancement, résultat ignoré et modèle Unicode de six textes. Condition dans un argument et réaffectation de résultat exercées. Les confusions de famille et la mutation sous emprunt sont refusées ; omission du contrôle d’emprunt et omission runtime de troncature détectées. | P |
| TX15 | replace_byte validé avant mutation, erreur sans changement | TX5, G12, B1–B5, AS2, AS8, AS12 | Continuation remplacée si résultat valide ; ancien u8, erreurs typées et contenu inchangé comparés au modèle. Corps async : receveur réservé pendant les arguments suspendus, indice sauvegardé avant le second argument, résultat ignoré exécuté une fois. Result<u8,ByteReplaceError> et payload u8 conservés par yield, await, join et contrat synchrone ; indépendance après drop du String et réemploi du slot. Sept transactions comparées au décodeur UTF-8 Python. Sujet direct de match calculé par if, bloc, loop ou match imbriqué : type et évaluation unique exercés sur les deux chemins ; mauvais type de branche, mauvais pattern et vue active refusés. Mutations du prêt, de la sauvegarde et de la validation détectées. | P ; O0/O2 avec UBSan fatal ; reset aliasé historique dans une borne ou un argument vérifié par contrat et mutation. Remplacement groupé async : voir TX16. |
| TX16 | replace_bytes valide le bloc entier à taille constante | TX15, E1, B4a, G12, AS2, AS8, AS12 | En synchrone, tableau fixe ou tranche relayée, intervalle vide, bornes, erreurs UTF-8, adresse stable et vue active protégée. En async, tranche directe de Vector<u8> et emprunt de tableau fixe u8, y compris ligne projetée, copie temporaire et tableau vide. Indice et bornes suspendus sauvegardés dans l’ordre. Destination et source réservées avec accès appropriés. Dix transactions Python sur deux orientations de la source vérifiées nativement, erreur sans écriture et remplacement atomique du bloc. Result<(),ByteReplaceError> distinct du résultat u8 à travers captures, await, join et contrats ; réemploi du pool source avant usage du résultat, échec EAGAIN et match typé. Réutilisation après dernier usage de vue, argument toujours protégé avant break. Mutations du type, de l’indice, du prêt source et de la fin de prêt détectées. | P — O0/O2 UBSan fatal. Les liaisons de tranche dans les corps async restent ouvertes. |
| TX17 | Aucun &mut u8 ou écriture par index sur String | TX9, TX15–TX16, ME2 | Écriture brute et &mut d’octet refusés sur String ; lecture et emprunt partagé exécutés. | P |
| TX18 | Garantie UTF-8 sans garantie du sens ; décalage impose nouveau String | G12, ST16, I6 | Changement du nombre de scalaires à taille fixe et conservation d’adresse vérifiés ; insertion et décalage hors de l’API. | P |
| TX19 | String non Copy ; duplication dans stockage indépendant | ST17–ST18, TX9–TX13 | Copie de String refusée ; duplication explicite et destruction indépendante exécutées ; intégration aux agrégats ouverte. | P |
| TX20 | print accepte &str et char sans conversion implicite | I6, B4, ME2 | Affichage de &str et de char dans `test_foundation_rules.py`, y compris le scalaire nul. Affichage de char dans un bras async et directement après await. Affichage de littéraux et de vues statiques capturées après yield, avec NUL incorporé. Mutation tronquant la vue au NUL détectée. Liaison locale et découpe statique relayées après yield. Bornes suspendables évaluées de gauche à droite. Frontière UTF-8 invalide refusée par le compilateur ou le runtime selon la provenance de la borne. Confusion avec Bool refusée et mutation du format d’affichage détectée. | P — affichage explicite des vues statiques et empruntées, y compris String |

## Fondamentaux, allocations typées et vecteurs

Voir [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md) et le
[rapport de cycle](cycles/FOUNDATIONS_CYCLE.md).

| Règle | Invariant | Interactions et preuves | Statut et limite |
| --- | --- | --- | --- |
| F1 | Taille statique finie, indirections explicites | H1, ST1–ST18 | P — cycles de champs directs refusés ; cycles via &Structure admis dans les déclarations, parcours de références locales vérifié sous UBSan, protection transitive et mutation ; enums récursifs locaux via &Enum vérifiés sous UBSan, variante terminale, match imbriqué, jonction de cibles et mutation ; fonctions avec chaînes locales de structures vérifiées sous UBSan et mutations du contrat de séparation des pools et de la provenance de retour ; résolution de méthodes homonymes sur projection de champ ou de bras typé et propagation des effets de pool ; retour scalaire de match imbriqué et contrainte de séparation des pools vérifiés ; paramètres partagés à chaînes de structures acycliques et propagation interfonction du chemin terminal vérifiés sous UBSan et par mutation ; paramètres partagés ou transférés d’enums acycliques vérifiés sous UBSan, spécialisation par variante et mutations des chemins inaccessibles ; paramètres mutables acycliques vérifiés sous UBSan avec mise à jour contractuelle, emprunt détaché et mutation ; retours transférés d’agrégats acycliques vérifiés sous UBSan, relais, réutilisation de slot et variantes ; retours directs partagés ou mutables vers des agrégats acycliques vérifiés sous UBSan, provenance imbriquée, séparation des pools, exclusivité et retour de projection de match avec plusieurs porteurs possibles, y compris dans une case de tableau ou dans un champ d’agrégat retourné, et en résultat d’une expression match mutable ; remplacement d’un champ partagé typé, propagation interfonction, protection du nouveau chemin et détection de cycle d’allocations vérifiés sous UBSan et mutations ; mises à jour conditionnelles et vérification par champ de la couverture des chemins de sortie ; champs &mut T locaux vers agrégats sans champs mutables et projection mutable de match vérifiés sous UBSan et par mutation ; contrats acycliques de projection mutable avec relais et porteurs alternatifs vérifiés sous UBSan et mutation ; réemprunt direct d’un champ mutable typé et relais vérifiés sous UBSan et mutation ; réservations par champ distinct et réemprunt retourné après mise à jour et reset de l’ancienne cible à travers un appel vérifiés sous UBSan et mutation ; chaînes de champs &mut typés, retour direct ou stocké de réemprunt exclusif sur plusieurs niveaux, préfixe partagé détaché avec suffixe réservé, retourné directement ou stocké dans un agrégat transféré, et détachement après traversée mutable et liens partagés vers un porteur de capacité mutable vérifiés sous UBSan et mutation ; disposition de taille fixe pour cycles déclarés via A<T> vérifiée dans le C et par mutation ; stockage et nettoyage de champs A<T> locaux avec conservation des emprunts de leurs enfants vérifiés sous UBSan et mutation ; projection empruntée des champs propriétaires dans match et jonction des cibles vérifiées sous UBSan et mutation ; signatures récursives et contrats propriétaires restent ouverts |
| F2 | Exhaustivité et mode de liaison cohérent | B1, B2, réemploi du slot, provenance des références, variantes possibles aux appels et jonction des valeurs dans `test_foundation_rules.py` | P — match consommant ou par emprunt avec résultats Int, tableaux, allocations transférées et emprunts. Les expressions de match par emprunt admettent aussi les appels dans les constructions locales, les appels Void directs, les remplacements explicites de receveurs, les conditions et les boucles. Les matchs par emprunt sans résultat admettent également les remplacements explicites et les sorties de boucle. Les appels de méthodes Void, les réemprunts reçus dans le bras et les résultats Int et &mut Int au stockage ou à la cible d’un champ via une méthode sur projection typée, avec composition des chemins réservés ou détachés dans les relais sont vérifiés sous UBSan et mutation. Les appels directs hors projections restent restreints dans cette forme. Un retour anticipé est contrôlé par le contrat de fonction et exclu de la jonction des bras continuants, avec nettoyage et réemploi vérifiés sous UBSan ; extraction consommante de champs A<T>, extraction et destruction explicite des champs propriétaires (anciens motifs ignorés désormais refusés), jonction de pools et emprunt transporté vérifiés sous UBSan et par mutation Complément brouillon 01 : contrôles de motifs propriétaires et consommation explicite, O0/O2, emprunts et réemploi ; trois mutations détectées. Couverture partielle et contre-exemples encore ouverts dans [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). |
| F3 | Aucun usage après invalidation sur un chemin atteignant la jonction | S4, S5, S5a, T9, T10, profils FLOW et LOOP_RESULT. Masquage, remplacement avant break et continue, et contrat de retour après affectation de références dans `test_foundation_rules.py` | P — formes de contrôle existantes, reprise et sortie après remplacement d’un champ propriétaire imbriqué de même pool vérifiées sous UBSan et par mutation |
| F4 | Évaluation conditionnelle et invalidation ordonnée | B4a, B2, transferts de pool, nettoyage des temporaires et réemploi des slots dans `test_foundation_rules.py` | P — opérateurs dans les conditions et expressions Bool, déclaration, argument, retour et déplacement possible vérifiés sous UBSan ; comparaisons comme valeurs et conditions parenthésées suivies d’un accès par méthode ou indice vérifiées ; mutations du court-circuit et du résultat de comparaison détectées ; jonction conservatrice ; construction de tableau de références avec reset dans un élément ultérieur et projection de ligne après évaluation de l’indice vérifiées sous UBSan et mutation |
| F5 | Résultat Int32 représentable ou diagnostic avant opération dangereuse ; as exact par type, try_from faillible | V3, B4a, emprunt mutable, pool, C sous UBSan et modèle de division ; AS1, contrats, U1, L6 | P — as u8→Int et identités Int/u8 à O0/O2 sous UBSan ; 256 octets comparés à un oracle indépendant ; Int→u8 refusé même constant. u8::try_from vérifié sur -2..257 et les extrêmes Int32, relais, drop, réemploi, await/join et mutants ciblés. Voir INTEGER_CONVERSIONS_CYCLE.md. Autres types entiers non couverts. |
| H1 | Adresse stable et nettoyage unique auprès du pool d'origine | T1, D1, A3 | P — annotation locale A<T> vérifie toutes les sources, adresse stable et retour au pool d’origine testés ; signatures transférées A<T> et origine contrôlées par contrat ; stockage dans des agrégats locaux avec transfert explicite, nettoyage des enfants dans leurs pools d’origine, réemploi et mutation vérifiés ; projection empruntée dans match et par champ, remplacement local direct, via emprunt à porteurs alternatifs ou dans un enfant projeté avec jonction, et réemploi du slot vérifiés sous UBSan et mutation ; une boucle préserve les cibles d’emprunt successives même si le pool du champ reste identique ; construction locale en fonction et restitution du champ par contrat vérifiées avec relais, jonction de pools, nettoyage implicite et mutation du contrôle de sources ; paramètres partagés ou transférés d’agrégats propriétaires acycliques vérifiés avec lecture imbriquée, consommation, relais et contrainte de sources ; restitution du même agrégat avec identité des champs conservée vérifiée sous UBSan et par mutation ; paramètres mutables d’agrégats acycliques vérifiés pour la mutation sur place, l’exclusivité et le refus du remplacement sans contrat ; retour d’agrégat neuf à champs A<Int> vérifié avec relais, pools alternatifs et mutation ; retour neuf imbriqué vérifié avec relais, réemploi et remplacement local après réception ; agrégat reçu par transfert puis incorporé comme enfant d’un résultat neuf vérifié avec relais, adresse stable et pools imbriqués alternatifs, y compris dans un même champ alternant agrégat transféré et agrégat neuf ; remplacement direct de A<Int> par une allocation de pool injecté via &mut vérifié avec relais et jonction conditionnelle ; remplacement d’un champ direct par un agrégat neuf ou transféré vérifié avec pools des descendants et relais ; remplacement d’un champ imbriqué via projection mutable et relais vérifié pour un porteur unique ; porteurs alternatifs vérifiés avec remplacement par appel, conservation des anciens pools et destruction unique du remplaçant ; effets chevauchants séquentiels et sur sorties distinctes vérifiés avec composition des inventaires ; jonction chevauchante avant sortie commune et propagation par relais vérifiées ; retour neuf d’un type récursif A<T> vérifié pour une valeur finie avec relais et nettoyage récursif ; paramètres récursifs A<T> partagés ou transférés vérifiés pour projection bornée, restitution et destruction ; projection partagée à la demande au-delà de la première répétition vérifiée sous UBSan et par mutation ; extraction consommante récursive jusqu’à la feuille vérifiée par nettoyage, réemploi et mutation ; mutation en place via paramètre récursif vérifiée avec relais, adresse stable et exclusivité ; restitution d’un enfant récursif extrait par match vérifiée avec relais, adresse stable et protection des descendants ; composition de deux extractions récursives avec alternative neuve vérifiée par identité, réemploi et mutation ; installation d’un enfant extrait dans un résultat neuf ou via un paramètre mutable vérifiée avec adresse stable et protection du pool descendant ; remplacement depuis un bras de match mutable vérifié avec relais et variante inapplicable ; remplacement au-delà du premier type répété vérifié pour un chemin de variantes découvert à la demande et propagé par relais |
| H2 | Emprunt du handle ou de sa cible, cible toujours initialisée | B1, B2, V4, H1 | P — vref et mut_vref sur A<Int>, A<Point>, A<Vector<Int>> et A<String> vérifiés sous UBSan, avec appels, drop, reset et mutation ; ref et mut_ref du handle typé avec emprunt et remplacement de A<Point>, relais, mauvais type refusé et mutation détectée, adresse stable et conflits testés ; remplacement via &mut A<Int> local direct ou réemprunt explicite, ordre et provenance inter-pools testés ; reprise du parent après dernier usage, retour par contrat, resets et réemploi des slots sous UBSan, mutation du rattachement détectée ; signatures &A<Int> et &mut A<Int> testées ; remplacement via paramètre : alternatives de provenance déduites et relayées dans le résumé, mutation de la branche inchangée détectée ; application du contrat et C vérifiés pour &mut A<Int>, via relais et appel depuis un enfant, identité, nettoyage, réemploi et reset conditionnel sous UBSan ; extension aux structures et enums sans champs empruntés, String, Vector<Int> et Vector<u8> vérifiée sous UBSan via relais, identité et reset ; variantes et emplacement unique après jonction vérifiés ; champs empruntés des remplaçants transférés vérifiés sous UBSan via relais, reset, drop, exclusivité et durée de vie, mutation détectée ; champs créés ou modifiés dans le corps résumés par cible, relayés et vérifiés sous UBSan avec exclusivité, refus d’une cible locale et mutation du résumé ; vecteurs de handles transférés avec inventaire inchangé vérifiés sous UBSan via relais, extraction, resets et mutation d’indice ; vecteurs neufs à inventaire déterminé résumés et relayés, cases neuves et transférées vérifiées sous UBSan, resets, adresse et mutation d’ordre ; vecteurs reçus puis transformés vérifiés sous UBSan par suppression suivie d’un ajout et relais, adresse, resets et mutation de suppression ; remplacement littéral par indice et voisin inchangé vérifiés sous UBSan ; inventaire neuf conditionnel résumé par ensemble de provenances, deux branches et mutation de pool détectée ; affectation directe depuis un enfant via réemprunt vérifiée sous UBSan, adresse, réemploi, contrôle de durée de vie, jonction et mutation du nettoyage ; jonction après appel Void ou Int vérifiée sous UBSan avec mutation du pointeur de nettoyage ; ordres de réception incompatibles refusés selon T9 ; restitution T6–T8 vérifiée après remplacement, cohérence contrat/C et mutation du marqueur détectée ; remplacement par appel à travers continue, break et retour testé avec deux pools, trace et mutation du résultat ; inventaires sans provenance vérifiable ouverts ; combinaison de reset et remplacement dans un même contrat historique non couverte |
| H3 | Modes de receveur et type d'élément explicites | ME1–ME4, H2 | P — vequals sur A<Int>, structures et enums à champs Int compare le contenu, vérifié sous UBSan avec rejet d’un autre type et mutation du tag ; String, Vector<Int> et Vector<u8> comparés sur le préfixe initialisé ; ordre logique entre fronts opposés vérifié en C à -O0 et -O2 avec UBSan et mutation détectée ; refus de types différents et de reset avec emprunt encore utilisé ; receveurs consommants -> A<Point> et -> Point distingués par contrat, relais, adresse stable et réemploi sous UBSan, marqueur muté détecté ; ordre de vequals et protection du receveur pendant les effets de l’argument vérifiés sous UBSan et mutation ; couverture des autres types de receveurs et des cases de handles partielle |
| VE1 | Cases homogènes et initialisées avant lecture | V2, H1, VE4 | P — Vector<Int> et Vector<u8> construits vides, ajoutés et lus depuis Crust ; Vector<A<Int>> local avec push explicite ; remove de handles avec transfert explicite et emprunts de cases &A<Int> et &mut A<Int>, disjonction d’indices littéraux et remplacement par emprunt vérifiés ; Vector<&Int> local avec push, indexation, déréférencement et remove vérifiés sous UBSan, durée de vie, ordre, adresse et nettoyage ; provenance par case après remove littéral vérifiée avec mutation ; paramètre &Vector<&Int>, retour de &Int relayé et reset selon le dernier usage vérifiés sous UBSan avec mutations ; retour de case littérale relayé et reset du pool voisin vérifiés sous UBSan avec mutation ; contrainte de reset interne relayée sur la case littérale vérifiée sous UBSan et avec mutation ; indice dynamique et inventaire inconnu traités par union ; indexation et remove d’un vecteur vide diagnostiqués à l’exécution sous UBSan avec mutation ; contrat de retour sans cible sur vecteur vide, arrêt après effets et alternative valide vérifiés sous UBSan avec mutation ; paramètres transférés avec destruction du vecteur, retour relayé de la référence, réemploi et décalage conditionnel vérifiés sous UBSan et par mutation ; construction et retour du vecteur entier puis relais vérifiés sous UBSan, pools du porteur et des cibles, vecteur vide, cible locale et mutation ; ordre des cases d’un vecteur construit puis retourné et relayé vérifié sous UBSan, reset après extraction et mutation d’ordre ; aller-retour d’un vecteur transféré sans modification vérifié sous UBSan, mutation du suivi des modifications détectée ; paramètre mutable de Vector<&Int> et effets relayés vérifiés sous UBSan, avec contrôle du reset, de la durée de vie et mutation ; Vector<&mut Int> local avec push par transfert et remove littéral explicite vérifié sous UBSan, exclusivité, adresse, reset, retour du prêt et mutation ; réemprunt partagé ou mutable par index vérifié sous UBSan, protection du porteur, reprise au dernier usage et mutation ; réemprunts mutables simultanés sur des cibles disjointes vérifiés sous UBSan et par mutation, chevauchement ou disjonction inconnue refusés ; écriture déréférencée avec ordre indice puis valeur, arrêt hors limites avant la partie droite et dernière utilisation vérifiés sous UBSan et par mutation C ; paramètres partagés et mutables de Vector<&mut Int> pour lire ou écrire les cibles, relais, reset et mutation de contrat vérifiés sous UBSan ; retour relayé d’un réemprunt de case, réservation du porteur et accès disjoint vérifiés sous UBSan et par mutation ; construction, transfert et retour du vecteur entier vérifiés sous UBSan, ordre, exclusivité, reprise du prêt parent, durée de vie et mutation ; push et try_push via emprunt injecté vérifiés sous UBSan, relais, exclusivité et reprise du parent, refus de cible courte, mutation de contrat ; ordre après push inconditionnel via relais vérifié sous UBSan, extraction puis reset du pool libéré et mutation ; remove dynamique local et via paramètre injecté vérifié sous UBSan, réservation du porteur en cas de chevauchement abstrait et mutation ; pop via paramètre mutable et relais vérifié sous UBSan, Some et None, réservation du porteur et mutation ; replace dynamique via emprunt injecté vérifié sous UBSan, restitution exclusive, restauration sur Err et mutation Ajout Copy dans les corps async Int/u8 : réservation du receveur pendant un argument suspendu, lectures et écritures du même vecteur refusées ; mutation du contrôle détectée. |
| VE2 | Une responsabilité par handle, destruction avant récupération | D1, L2, H1, VE1 | P — push de A<Int> vérifié dans Crust, transfert exclusif, destruction auprès de deux pools, durée de vie et reset ; transferts du vecteur entre scopes testés ; paramètres partagés ou mutables et retours d’emprunt de case testés ; transfert par fonction et retour conditionnel de vecteurs vérifiés ; push local depuis un handle injecté vérifié avec reset direct ou par relais, contrôle de sources distinctes à l’appel et réemploi natif du slot ; replace, try_push et remplacement de case par emprunt depuis un handle injecté vérifiés avec contrôle des sources à l’appel et réemploi des slots ; push, try_push, replace et remplacement par emprunt d’un vecteur reçu par transfert puis consommé vérifiés sous UBSan, avec reset et mutation de durée de vie ; restitution après insertion d’un handle reçu par transfert vérifiée via relais, resets, adresse et mutation sous UBSan ; restitution après insertion ou remplacement d’un handle neuf issu d’un pool injecté vérifiée sous UBSan, via relais, avec resets et mutation ; construction et retour d’un vecteur neuf depuis Pool<Vector<A<Int>>> vérifiés sous UBSan avec deux pools d’éléments, relais, resets et mutation ; transfert inter-vecteurs injectés vérifié avec remove ou pop, relais, pools distincts et mutation ; cases d’un vecteur neuf vérifiées après relais, reset du pool d’une autre case et mutation de l’ordre ; ordre préservé après push inconditionnel d’un vecteur reçu via relais, reset du pool disjoint et mutation ; remplacement littéral déterminé préserve les cases voisines via relais, vérifié sous UBSan, resets et mutation ; jonctions de remplacements de même forme vérifiées par case sous UBSan, mutation et modèle sur 440 jonctions ; contrôle des identités entrantes ou neuves par case vérifié avec mutation sur un même pool, identités mortes retirées avant jonction de longueurs avec régression UBSan et mutation ; décalage après remplacement puis remove littéral vérifié via relais, UBSan, mutation et modèle sur 1 211 états ; push à travers un emprunt mutable vérifié via relais, durée de vie du pool, reset, UBSan et mutation du contrat ; ajouts variables par branche, boucle et try_push via emprunt vérifiés sous UBSan, capacité et mutation ; replace et écriture de case via un paramètre emprunté vérifiés sous UBSan, relais, resets et mutation ; remove et pop via un paramètre emprunté vérifiés sous UBSan, relais, cases restantes, resets et mutation ; contraintes internes par indice et résultats non Copy hors match restent ouverts |
| VE3 | Provenance préservée lors du réarrangement ou de l'extraction | V4, H1, VE1, VE2 | P — pop local de Vector<&mut Int> vérifié sous UBSan, Option consommée, None, abandon sans destruction, exclusivité et mutation ; replace local par transfert vérifié sous UBSan, Ok, Err, match immédiat ou différé et mutation de l’exclusivité ; indice calculé pour remove avec une seule case et replace sur vecteur vide vérifié sous UBSan, bornes, reset et mutation ; constantes immuables utilisées comme indices de replace et remove et pour la disjonction, vérifiées sous UBSan et par mutation ; pop local de Vector<&Int> avec Option<&Int>, Some, None, adresse stable, reset et retour de la référence relayé vérifiés sous UBSan et par mutation ; replace local de Vector<&Int> avec Result<&Int,&Int>, succès et restitution sur indice invalide vérifiés sous UBSan avec reset et mutation ; interfaces des résultats contenant des emprunts encore ouvertes ; remove, pop et replace Copy testés via fonctions ; indices, emprunts actifs, modèles et résultats Option ou Result typés couverts ; remove A<Int> vérifié dans Crust, adresses et provenance par case ; pop A<Int> via match consommant testé ; replace A<Int> via match consommant testé, provenance par bras et retour du handle de Err via contrat ; retour d’un handle injecté via remove, Some de pop et Ok de replace vérifié sous UBSan avec identité, drop, réemploi et refus de reset ; sélection de la case littérale vérifiée pour un autre handle du même pool et pour une autre case locale, avec mutation détectée ; remplacement par emprunt direct de case et retour après relais du vecteur vérifiés sous UBSan, avec mutation détectée ; retour de prêt de case littérale via deux appels vérifié sous UBSan et par mutation de l’indice ; égalité de pool pour drop après remove propagée par deux appels, vérifiée sous UBSan et par mutation ; contrainte d’égalité du nouveau pool après remplacement par emprunt direct ou renvoyé par appel vérifiée sous UBSan et par mutation ; remove et pop d’un vecteur reçu par transfert vérifiés sous UBSan via relais, avec contrôle de reset et mutation d’identité ; indices de remove et de pop après suppressions et relais vérifiés sous UBSan, reset du pool disjoint, mutations d’indice et modèle de liste sur 10 158 états ; restitution d’un vecteur injecté modifié refusée même si l’inventaire est inconnu, contre-exemple de reset et mutation détectée dans les deux modes ; restitution après remove littéral ou pop vérifiée via relais, deux pools, mutation et modèle de composition sur 7 786 états ; restitution après suppression dynamique ou divergente vérifiée sous UBSan avec refus des resets dangereux et mutation ; historique perdu après effet opaque, contraintes internes par indice, alias à cibles multiples et résultat local de pop non Copy extrait immédiatement et nettoyé sous garde, None/Some, jonction, drop et mutation vérifiés ; match différé consommant après modification du vecteur vérifié sous UBSan avec identité, réemploi et mutation du discriminant ; bras _ seul testé sur Some et None, réemploi dans le bras et mutation de la destruction ; déplacement local et transferts descendants successifs du résultat vérifiés sous UBSan avec réemploi, contrôle du parent direct et mutation ; retour du résultat entier via receveurs imbriqués vérifié sous UBSan avec contrôle du pool et mutation du bilan ; retour sans nouveau receveur vérifié sur Some et None avec adresse stable et mutation de la restauration après consommation ; résultats if et else if vérifiés sous UBSan sur deux pools, None, match et drop avec mutation de la garde ; résultat de boucle vérifié sous UBSan avec break Some et None, nettoyage sur continue, réemploi et mutation ; retour Option<A<Int>> à travers deux fonctions vérifié sous UBSan par contrat, adresse, drop, reset et mutation de provenance ; paramètre Option<A<Int>> transféré vérifié sous UBSan sur Some et None y compris None établi statiquement dans un corps de fonction, relais, réemploi, contrôle du scope direct et mutation de la protection pendant les arguments ; résultat local de replace vérifié sous UBSan avec match différé, modification du vecteur, provenance par bras, reset du pool disjoint, transfert bloc et jonctions if/loop vérifiées avec mutation de provenance ; paramètre et retour de Result par contrat vérifiés via relais, reset disjoint et mutation des bras ; reset disjoint de pools injectés vérifié après drop ou fin du scope du vecteur local, mutation du suivi des insertions ; bras _ résiduel ou unique vérifié pour les matchs immédiats et nommés de handles, réemploi et mutation du nettoyage ; expression de match immédiat de replace vérifiée sous UBSan avec transfert du handle sélectionné et adresse stable ; retour direct de pop, replace et remove en fin de bloc vérifié avec mutation du bilan ; annotations exactes des Option et Result non Copy vérifiées avec mutation du contrôle de type Complément brouillon 01 : contrôles de motifs propriétaires et consommation explicite, O0/O2, emprunts et réemploi ; trois mutations détectées. Couverture partielle et contre-exemples encore ouverts dans [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). |
| VE4 | Aucune publication partielle ou hors borne | VE1, G4, B2 | P — try_push local de Vector<&mut Int> vérifié sous UBSan, Ok et Err avec région C ramenée à une case, réservation du porteur jusqu’au match et mutation ; try_push local de Vector<&Int> vérifié sous UBSan sur Ok et à capacité exacte, longueur inchangée sur Err, restitution de l’emprunt, refus de reset et mutation ; try_push Copy et try_extend d’un &[u8; N] ou d’une tranche directe de Vector<u8> ; seuil de région, échec sans publication, restitution et front descendant exercés ; lecture externe synchrone bornée vérifiée en C avec tubes POSIX ; try_push A<Int> en match consommant vérifié à capacité exacte ; lecture synchrone read_fd depuis Crust via contrat, succès, EOF, capacité, erreur et emprunt actif vérifiés sous UBSan, mutation de publication ; réservation du vecteur pendant l’évaluation du descripteur vérifiée par transfert et reset aliasé avec mutation du contrat ; reset dans un argument également vérifié par contrat sur remove, indexation, replace et push ; résultat local de try_push vérifié sous UBSan en succès et à capacité, avec drop, match, réemploi et mutation de garde ; paramètre et retour de Result<(),A<Int>> vérifiés sur Ok et Err à capacité Complément brouillon 01 : contrôles de motifs propriétaires et consommation explicite, O0/O2, emprunts et réemploi ; trois mutations détectées. Couverture partielle et contre-exemples encore ouverts dans [OWNED_RESULTS_CYCLE.md](cycles/OWNED_RESULTS_CYCLE.md). |
| VE5 | Tranches disjointes, emprunt parent suspendu | B2, VE1 | P — tranche partagée d’octets directe ou nommée, réaffectation et dernier usage ; mutation, drop, reset et sortie de source locale refusés si la vue reste utilisée ; paramètres et retours &[u8] via contrats, deux provenances, index borné par la tranche, copie de u8 ou emprunt de case ; tranches Int, contrats et indexation vérifiés ; split_at_mut Int et u8, liaison locale, partition C et suspension statique du parent testées ; paramètres et retours mutables Int et u8, réemprunts disjoints et doublon refusé ; réemprunt explicite partagé des moitiés Int/u8 vérifié avec retour UTF-8, écriture disjointe et mutation de provenance ; chaîne de réemprunts partagés et retour de sous-tranche vérifiés, front descendant, garde et mutation de décalage ; retour groupé des deux moitiés et cases non Copy ouverts ; écriture d’une case de tranche Int vérifiée par contrat après évaluation du RHS, avec reset aliasé refusé et mutation détectée ; subdivision d’une tranche mutable et retour d’une moitié vérifiés sous UBSan avec trois zones disjointes et mutation d’orientation ; retour groupé Int/u8 vérifié via contrat, relais, refus du reset et mutation de la disjonction ; jonction if locale et retour conditionnel vérifiés sur deux provenances avec mutation du C ; paire reçue via break, reprise continue, refus du stockage local et mutation d’ordre vérifiés ; choix par match consommant, partagé ou mutable vérifié sous UBSan et par mutation du C ; sortie de bloc d’une paire vérifiée avec stockage durable et mutation du contrôle de durée de vie |
| VE6 | Initialisation sur place avant emprunt | V2, B2, VE1, AS9 | P — Vector<Int/u8> sync/async, défaut zéro, retours et relais &mut Int/u8, yield/await/join, capacité, dernier usage et réemploi ; voir ASYNC_VECTOR_PUSH_NEW_CYCLE.md ; autres types et expressions générales ouverts |
| GR1 | Placement borné, pas de collision ni de changement d'adresse | G1–G12, H1 | P — deux fronts depuis Vector et limite de région conservée après transfert ; classes annotées et fronts non annotés dans la même plage, collision, repli dédié et récupération différée vérifiés |
| GR2 | Récupération après nettoyage, sans déplacer d'objets vivants | L2, G1–G12, VE2 | P — suffixe et adresses sur les deux fronts ; Vector<A<Int>> détruit ses éléments avant récupération et rend leurs slots aux pools d’origine ; front opposé stable, région partagée et mutations détectées sous UBSan ; autres éléments non Copy non couverts |
| TX21 | Octets contigus et toujours UTF-8 | TX1–TX20, GR1, VE1 | P — String emploie le noyau Vector avec octets contigus en ordre croissant ; régions côté haut, stabilité et réemploi vérifiés sous UBSan ; stack dédiée sans annotation si le front montant est occupé, mutations de placement détectées |
| TX22 | Concaténation et transfert explicite de la responsabilité | TX13, TX21, H1, AS2, AS8–AS12 | P — merge exécuté entre deux pools ; alias, transfert manquant et réusage refusés. Corps async : source consommée puis détruite une fois avant la suspension suivante, slot source réutilisé, adresse de destination conservée. Argument obtenu par await, bloc, if ou loop transférés ; source rattachée explicitement au bloc. Destination retournée hors du pool source détruit, contenu comparé à six concaténations Python. Succès, EAGAIN et contrat de join exercés à O0/O2 avec UBSan fatal. Mutations du nettoyage et de la réservation détectées. |


## Complément — directives catégorisées, brouillon 06

Profil **DIRECTIVES** : `tests/test_growth_annotations.py`, méthodes de
`test_foundation_rules.py` et `test_owned_results.py` contenant les directives.
Vingt méthodes ciblées exécutées à O0 et O2 avec UBSan fatal ; trois mutations
syntaxiques/numériques détectées. Héritage lexical, blocs expressions,
transferts et réemploi exercent P2/G6/G7 avec T6, P3/P4 et U1.
La résolution des type features était non implémentée lors de ce cycle ;
sa première implémentation et ses limites sont désormais décrites dans
[TYPE_FEATURES_CYCLE.md](cycles/TYPE_FEATURES_CYCLE.md). Les preuves de directives seules
ne couvrent pas I5/B4/B5 ou ME1/ME2/ME4 pour les features.
Détails, régression et limites : [DIRECTIVES_CYCLE.md](cycles/DIRECTIVES_CYCLE.md).

Régression complémentaire U1 du cycle DIRECTIVES : 181 méthodes historiques
(main, appels/arguments et expressions conditionnelles) réussies après migration
des fixtures vers l’usage explicite des propriétaires ; 34 méthodes inchangées
(runtime de croissance et usages propriétaires) réussies dans l’exécution initiale.
Les traces de destruction/réemploi restent vérifiées. Cette migration ne change
pas U1 et ne constitue pas une preuve générale du suivi des usages.

## Type features — brouillon 06, première résolution statique

Référence normative : [TYPE_FEATURES.md](TYPE_FEATURES.md). Preuves et limites :
[TYPE_FEATURES_CYCLE.md](cycles/TYPE_FEATURES_CYCLE.md). Les statuts sont partiels ; le
catalogue des méthodes builtin et les interactions async restent à compléter.

| Règle | Comportement et invariant | Interactions | Preuves exécutées | Statut / limites |
| --- | --- | --- | --- | --- |
| TF1 | Une méthode structurelle, signature complète et mode de receveur conforme | I5, ME1 | `test_type_features` : déclarations/modes/résultats ; modèle indépendant de 81 combinaisons, 9 admises et 72 refusées ; mutation du résultat détectée | P — méthodes de structures ; catalogue builtin restant |
| TF2 | Signatures contraintes, stockage concret ; arguments résolus indépendamment | B4, P8, ME2 | Refus de champs/collections/pools/annotations abstraits ; Console/Journal admis simultanément ; mutation du cache détectée | P — projections et signatures imbriquées à étendre |
| TF3 | Exigences directes et indirectes garanties par la signature | B4e, ME2 | Alias, branche fausse, expression, relais équivalent/non équivalent, fonction non appelée ; mutations de contrôles abstrait et indirect détectées | P — contrôles abstraits distincts des vérifications mémoire concrètes |
| TF4 | Résolution statique conservant modes, effets et contrats concrets | B1–B4, L6, P8, ME4 | Receveurs partagés/mutables/consommants ; nettoyage unique, réemploi, reset historique après lecture et refus avant futur usage ; catalogue vérifié sans type abstrait résiduel | P — 21 programmes natifs sous UBSan O0/O2, pas de preuve générale |
| TF5 | Résultat concret et origine conservés, pas de promotion implicite | B2, B5, T6, A2, A3 | Retour partagé/mutable/propriétaire, deux relais, branches, adresse conservée, pool trop court refusé, cible réservée jusqu’au dernier usage | P — cas concrètement instanciés ; récursion et async non couverts |

Régression de ce cycle : 173 méthodes réussies, puis 36 des cas de méthodes et
structures réexécutés avec injection d’une feature et d’un relais générique
inutilisé. Quatre mutations ciblées détectées. Le contre-exemple de `Vector.len`
était ouvert à l'issue de ce premier cycle ; il est corrigé dans le complément
ci-dessous. Le brouillon 06 n'est pas pour autant entièrement implémenté.

### Complément builtin et retours concrets

Preuves : [BUILTIN_FEATURES_CYCLE.md](cycles/BUILTIN_FEATURES_CYCLE.md).

| Règles | Invariant / interactions | Preuves exécutées | Limites |
| --- | --- | --- | --- |
| TF1, TF4 | Signature complète des méthodes intégrées ; pas de neutralisation des effets | `test_builtin_features` : 36 signatures selon un modèle source indépendant, 2 admises / 34 refusées ; mutation ignorant les signatures détectée | P — catalogue plus large que les opérations exercées ; `char.utf8_len` restant |
| TF3 | Les opérations déjà transformées par le parseur exigent la garantie abstraite | `try_slice` et `char_at` non garantis refusés sur nom et retour de fonction ; mutation du contrôle détectée | P — pas de preuve exhaustive de toutes les formes d'AST |
| TF4, TF5, B5 | Origines, réservation mutable, dernier usage et source conservés | `&String`, `&mut Vector<Int>`, tableau, `push_new`, résultat de découpe, pool à deux relais ; drop/mutation/reset historique prématurés refusés ; mutation d'origine détectée | P — cas concrets seulement, pas de preuve async générale |
| TF4, TX, VE, P8 | Nettoyage, identité du slot et résultat UTF-8 invalide atomique | `merge` nettoie une fois, réemploi à même adresse ; constructeur de pool garde sa source ; mauvais remplacement conserve `é` | P — exemples déterministes, pas toutes les méthodes du catalogue |

32 méthodes type features réussies sous UBSan fatal à O0 et O2 ; module builtin
seul : 18 programmes natifs et 57 refus. Régressions ciblées : 173 méthodes,
puis 32 découpes/conversions. Quatre mutations ciblées détectées.
L'indépendance des types concrets dans les signatures de méthodes utilisant
elles-mêmes une feature était un écart TF2 reproduit ; correction ci-dessous.

### Contraintes imbriquées et premières interactions async

Preuves : [NESTED_FEATURES_CYCLE.md](cycles/NESTED_FEATURES_CYCLE.md).

| Règles | Invariant / interactions | Preuves exécutées | Limites |
| --- | --- | --- | --- |
| TF1, TF2, TF3 | Seul le receveur est spécialisé ; autres arguments contraints indépendants ; signatures complètes | Left/Right dans la même méthode par deux relais ; autre feature et argument mutable ; contraintes récursives équivalentes ; signature restrictive refusée ; mutations de substitution et de garde détectées | P — pas de relation d'égalité de types ajoutée ; pas de preuve universelle |
| TF5, B5 | Le résultat contraint garde son propre type et son origine | Wrapper renvoie Target via deux relais ; destruction prématurée refusée ; trois feuilles incorrectes refusées même sans usage de méthode ; mutation d'exigence résultat détectée | P — résultats concrets testés ; récursion exécutable non ajoutée |
| TF4–TF5, AS8, AS11–AS12 | Captures dès la création, transferts, effets et emprunts après join préservés | `test_async_type_features` : quatre programmes natifs, huit variantes refusées ; Vector Int/u8 indépendants, String empruntée et consommée, réemploi à même adresse | P — capture de structure encore refusée, contre-exemple archivé ; pas de TSan |

État final : 42 méthodes sous UBSan fatal à O0/O2 ; 173 méthodes de régression
et 36 réexécutées avec injection d'une feature. Sept mutations détectées.
Les nouveaux cas synchrones et async représentent 10 programmes natifs et
19 variantes refusées. Le lot 06 et l'objectif global ne sont pas clos.

## Brouillon 04 — nouvelle référence normative et obligation d'attente

La version intégrée de [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md)
remplace les anciens énoncés incompatibles, notamment l'abandon de handle.
Le [cycle des obligations](cycles/HANDLE_OBLIGATIONS_CYCLE.md) distingue cette
intégration documentaire de l'implémentation et des validations exécutées.

| Règles | Obligation actuelle | Preuves / état d'implémentation | Statut |
| --- | --- | --- | --- |
| RT7, MT3, MT5 | Attendre chaque handle, par chemin ; transfert de l'obligation ; aucun drop ni abandon implicite | `test_handle_obligations` : 10 exécutions natives, 34 refus à O0/O2 ; modèles sync/async de 18 configurations ; deux mutations d'abandon détectées ; 44 méthodes d'interaction réussies ; régression async : 264 méthodes initialement réussies et 11 migrées puis réexécutées avec succès | P |
| AS10, RT6 | Échec de lancement nettoyé avant Err et réemploi du slot | Simulation EAGAIN avec nettoyage unique et adresse réutilisée ; mutation omettant le nettoyage détectée ; motif runtime::Error::LaunchFailed et signatures propriétaires intégrés ; valeur d’erreur autonome conservée après destruction, recapturée et relayée ; voir RUNTIME_ERROR_VALUES_CYCLE.md | P |
| AS14 | Destruction d'une instance inactive toujours possible | Drop admis, fin de scope avec avertissement, corps non exécuté dans le nouveau lot | P |
| AS7 | Borne statique ou capacité explicite par nom qualifié ; récursion comptée ; async_pool_sizes | Directive et bornes conservatrices implémentées dans le sous-ensemble actuel : 9 méthodes O0/O2 + 1 méthode de dépassement Int32, 13 exécutions natives par niveau dont un épuisement contrôlé, 12 refus, modèle de quatre configurations parents/enfants, quatre mutations détectées. Régression : 274 méthodes async + 22 features réussies initialement et 1 diagnostic migré réussi séparément ; 239 méthodes synchrones réussies initialement, puis 28 conditionnelles après migration U1 de 4 cas. Voir ASYNC_CAPACITY_CYCLE.md ; Select et namespaces déclarés restent ouverts | P |
| RT2–RT4 | Délégation spawn/spawn_blocking ; installation directement dans main ; réveils conservés et équité ; migration entre polls | spawn_blocking délègue à un callback distinct ; modèle de 8 configurations, progrès d’un pair pendant un blocage et nettoyage à l’échec exécutés à O0/O2. Cinq mutations détectées, 14 méthodes rejouées avec les deux modes ; voir SPAWN_BLOCKING_CYCLE.md. Installation publique, réveils et équité générale restent ouverts | P |
| RT5 | runtime::Handle<T>, join synchrone ou await async, Result<T,runtime::Error> | Motif runtime::Error::LaunchFailed et résultats propriétaires imbriqués intégrés ; valeurs d’erreur autonomes intégrées dans les contextes testés (RUNTIME_ERROR_VALUES_CYCLE.md) ; contrats synchrones et captures async de six Result sans emprunt intégrés (PLAIN_JOIN_CONTRACTS_CYCLE.md) ; retours async et imbrications de ces six charges intégrés (NESTED_PLAIN_RESULTS_CYCLE.md) ; runtime::Handle<T> et autres formes générales restant à intégrer | P |
| RT8 | Bloc synchrone runtime::thread avec captures transférées et résultat inféré | Parsing, états typés, premières captures et résultats raccordés ; 29 exécutions Crust natives, 40 refus et quatre mécanismes de mutation détectés dans NATIVE_BLOCK_LOWERING_CYCLE.md. Les auxiliaires Int/u8/char/Void sont maintenant appelables depuis les états : 14 exécutions, 17 refus, contrats opaques pendant check, ordre des arguments, nettoyage des pools internes et join transitive. Quatre mutations ciblées détectées, dont un cas renforcé après survie initiale. Les paramètres et résultats &Int, &mut Int et &mut u8 sont raccordés : ordre des prêts préparés, résultats conditionnels, derniers usages, drop scalaire et capture par enfant. Voir SYNC_BORROW_CALLS_CYCLE.md (109 méthodes de régression O2, 16 ciblées O0, cinq fautes détectées). Les paramètres/résultats propriétaires Int, String et Vector<Int/u8> sont raccordés dans SYNC_OWNED_CALLS_CYCLE.md. Pools directement dans les états, autres signatures, types et captures généraux restent ouverts. Voir aussi NATIVE_SYNC_CALLS_CYCLE.md. | P |
| MT9 | Garde synchrone liée au thread ; garde async conservable pendant suspension et migration ; libération après fin des emprunts | Primitives internes sync/async et nettoyage Select exercés dans MUTEX_RUNTIME_CYCLE.md : six sondes C, migration et réveil, régressions liées. Contrôle statique des gardes non raccordé ; constructeurs expressément reportés | P |
| SL1 | Select possède les branches ; ordre des éligibles ; attente unique ; perdantes conservées puis détruites | Mécanisme C interne, réveils par branche et rétention testés dans SELECT_RUNTIME_CYCLE.md ; callbacks de nettoyage aux suspensions générés et exercés dans SUSPENDED_CLEANUP_CYCLE.md. Source et contrats non raccordés ; arbitrage des handles perdants en attente. | P |

Les oracles C du registre d'abandon restent historiques et ne constituent
plus une preuve d'acceptation de l'abandon au niveau du langage.

Complément RT8 — [frontière native](cycles/NATIVE_THREAD_BOUNDARY_CYCLE.md) : cinq
méthodes runtime, dix sondes C à O0 et O2 (neuf sorties normales et un SIGABRT
attendu pour suspension interne interdite), sept méthodes de parsing,
six fautes ciblées détectées et 68 méthodes de régression O2 réussies.
Lors de ce premier cycle, seuls le parsing et l’ABI étaient raccordés ; les
contrats/génération restaient ouverts et le programme minimal était refusé.
Le cycle NATIVE_BLOCK_LOWERING_CYCLE.md ci-dessous apporte depuis les premières
exécutions de bout en bout ; les journaux de refus antérieurs sont historiques.

### Complément RT5/RT6 — Valeurs d’erreur

Le cycle [RUNTIME_ERROR_VALUES_CYCLE.md](cycles/RUNTIME_ERROR_VALUES_CYCLE.md) trace les
interactions exécutées avec U1, drop, branches, boucles, captures et contrats.
Le statut reste P : les résultats généraux et le runtime public sont incomplets.
Les deux mutations initialement survivantes et les quatre scénarios historiques
de boucle migrés vers U1 y sont documentés, avec les traces finales.

### Complément RT5/RT6/U1 — Contrats de résultats simples

[PLAIN_JOIN_CONTRACTS_CYCLE.md](cycles/PLAIN_JOIN_CONTRACTS_CYCLE.md) trace la prise en
charge des six charges Int/Bool/u8/char/()/runtime::Error dans les signatures
synchrones, les annotations et les captures async, ainsi que l’harmonisation
des analyses. La table indépendante couvre 24 configurations de type,
lancement et contexte ; les autres cas portent le lot à 32 exécutions natives
et 38 refus. Quatre mutations ciblées détectées. La vérification U1 des résultats
de boucle async et les lectures ajoutées à deux tests historiques sont détaillées.
Le statut reste P. Le retour async d’un Result simple est un écart reproduit
dans validation/open-async-plain-result-return.crust et son log.


### Complément RT5/RT6 — Retours async et imbrication des résultats simples

[NESTED_PLAIN_RESULTS_CYCLE.md](cycles/NESTED_PLAIN_RESULTS_CYCLE.md) actualise l’écart
`open-async-plain-result-return` ci-dessus. Son ancien log de refus est conservé.

| Règles | Invariant et portée | Preuves | Limites / statut |
| --- | --- | --- | --- |
| AS4, RT5, RT6 | Await inactif rend T ; attente d’un handle ajoute une enveloppe ; chaque statut reste indépendant | Six charges primitives, profondeurs 2 et 4, capture async et suspension ; chaîne de profondeur 7 ; échec injecté à chacun des quatre niveaux ; trois mutations de statut détectées | P — enveloppes runtime::Error autour de ces six charges ; pas tous les Result<T,E> |
| RT5, U1, B5 | Les contrats gardent le type, y compris profondeur et charge ; usage explicite des résultats imbriqués | Contrats sync/async, retours directs, if/loop, copies, réaffectations et drop ; types incompatibles et liaison après drop refusés ; mutations de garde de type et d’usage détectées | P — couverture déterministe, pas de preuve universelle |
| AS2, AS10, AS11, P8 | Les résultats simples ne prolongent pas les captures ; attente avant libération et réemploi | Capture possédée détruite une fois, succès et échec de lancement ; même adresse réutilisée ; capture mutable réservée jusqu’au join, drop de la cible permis avant lecture du résultat simple ; reset historique prématuré refusé | P — trois exécutions et trois conflits de capture ; reset n’est pas réintroduit |
| RT5 / C généré | Copie typée par niveau, statuts séparés et déclarations indépendantes de l’historique du compilateur | UBSan fatal O0/O2 ; compilation peu profonde identique avant/après programme profond ; signature profonde sans instance runtime ; régressions résultats/emprunts/tableaux/ABI | P — Clang arm64 ; ni preuve formelle ni TSan |

Le nouveau module contient 11 méthodes : 52 exécutions natives et 23 refus
attendus par niveau d’optimisation. Cinq mutations ciblées sont détectées.
Les commandes, traces terminales et limites sont consignées dans le rapport.
L’objectif global et les autres lignes N/P demeurent ouverts.

Écart RT5/RT6 voisin reproduit après ce lot :
`validation/open-async-business-result-envelope.crust` et son log montrent
que l’enveloppe `Result<Result<u8,IntegerConversionError>,runtime::Error>`
reste refusée comme retour async. C’est une composition normative valide
à implémenter ; elle n’est pas classée comme programme invalide.


### Complément RT5/RT6/V3/TX/U1 — Enveloppes des résultats métier

[BUSINESS_RESULT_ENVELOPES_CYCLE.md](cycles/BUSINESS_RESULT_ENVELOPES_CYCLE.md)
actualise l’écart `open-async-business-result-envelope` ci-dessus. Le log de
refus historique est conservé ; le programme s’exécute désormais.

| Règles | Invariant et interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| RT5/RT6, V3, TX | La charge métier conserve son type et son statut indépendamment des erreurs de lancement | Conversion u8, char_at, char::from_str, pop, replace_byte et replace_bytes ; une/trois enveloppes, deux issues métier, lecture sync/capture async ; refus de lancement à chaque niveau | P — six familles existantes sans emprunt, pas tous les Result<T,E> |
| U1 | Le résultat faillible extrait doit être utilisé | Défaut d’acceptation de Ok(inner) inutilisé reproduit puis corrigé ; voisin avec drop accepté ; mutation détectée | P — cas de résultats testés, pas preuve universelle |
| AS2/AS12, B5, RT5 | Une représentation C commune n’autorise pas une conversion entre types Crust ou l’effacement d’une provenance | Création sync de tâche : huit mauvais types de charge et deux mauvaises valeurs runtime::Error refusés ; résultat de slice emprunté incompatible refusé, voisin valide exécuté ; mutation du contrôle de type détectée | P — chemins de création sync et captures du lot ; signatures empruntées générales encore ouvertes |
| RT5/TX, L6 | Résultats calculés indépendants du stockage source ; copie, retours, branches, drop | Résultats de String utilisés après drop de la source ; contrats sync/async, réaffectations et alias ; anciennes vérifications UTF-8/transaction/réemploi rejouées | P — exécutions ciblées sous UBSan fatal |

Le module final compte 58 exécutions natives et 16 refus attendus par niveau
O0/O2. La première campagne de mutation a révélé un chemin non exercé ; la
matrice a été élargie à l’extraction directe synchrone. Voir le rapport pour
les traces, classifications et résultats finaux. Les autres lignes N/P et
l’objectif global restent ouverts.

### Complément VE3 × AS8 — Remove dans les corps async

[ASYNC_VECTOR_REMOVE_CYCLE.md](cycles/ASYNC_VECTOR_REMOVE_CYCLE.md) corrige
`validation/open-async-vector-remove.crust`. Aucune modification normative.

| Règles | Invariant / interactions | Preuves exécutables | Limites / statut |
| --- | --- | --- | --- |
| VE3/VE1, GR1/GR2, AS8 | Extraction de la bonne valeur, ordre et longueur conservés, même sur le front descendant | Quatre combinaisons Int/u8 × deux fronts, orientation réelle vérifiée dans le C ; 64 opérations selon deux listes Python indépendantes ; mutations d’indice, décalage et longueur détectées | P — éléments Copy Int/u8 ; handles/emprunts async non couverts |
| B1/B2, F4/B4a, AS2/AS15 | Réservation du receveur pendant l’indice suspendu ; aucune réutilisation d’une vue invalidée | Trois indices aliasants refusés et voisin disjoint exécuté ; dernière utilisation de vue, trois continuations interdites ; mutation de réservation détectée | P — formes du lot |
| F3, AS8/AS10, D1/P8 | Continue/break et extraction avant nettoyage ; réemploi seulement après join | Boucle avec vue locale, yield, continue et break ; capture possédée, compteur de deux destructions et adresse réutilisée sur succès/EAGAIN | P — scénarios exécutés, pas preuve générale de nettoyage |
| VE3/VE4, F5/B5 | Indice hors limites diagnostiqué avant l’accès ; largeur et mutabilité conservées | Six arrêts contrôlés, Int/u8 × trois indices invalides ; u8=255 par await/join, mauvais types/arity/receveurs et réusage après drop refusés | P — UBSan fatal, pas analyse exhaustive de bornes |

Douze méthodes, 15 exécutions natives réussies, six arrêts contrôlés et
15 refus attendus par passage complet. Quatre mutations détectées ; voir
le rapport pour les traces O0/O2 et régressions. L’écart suivant, conservé dans
`validation/open-async-vector-push-new.crust`, est maintenant corrigé pour
Int/u8 ; voir le cycle ci-dessous. Les autres obligations des sept brouillons
restent ouvertes.

### VE6 / AS9 — emprunts de nouvelles cases, yield, await et join

Preuves : [ASYNC_VECTOR_PUSH_NEW_CYCLE.md](cycles/ASYNC_VECTOR_PUSH_NEW_CYCLE.md),
`tests/test_async_vector_push_new.py` et ses journaux dans validation/.
Aucune règle normative modifiée ; couverture exécutable partielle.

| Règles | Invariant et interactions | Preuves exécutables | Limites |
| --- | --- | --- | --- |
| VE6/V2, VE1/GR1 | Case initialisée avant exposition, bonne adresse sur les deux fronts | Zéro puis écriture, voisins intacts, orientation C vérifiée ; listes indépendantes graines 817/810 ; mutations du défaut et de l’adresse détectées | P — Int/u8, autres types ouverts |
| B1/B2/B4a, AS2/AS9/AS15 | Vecteur et parent réservés jusqu’au dernier usage | Captures inactives, yield, deux relais, branches/boucles/continue/break ; accès prématurés refusés ; mutation de réservation détectée | P — formes exécutées ; expressions générales d’emprunts ouvertes |
| F5/B5, AS8, RT6 | Type et provenance conservés par await/join et contrats | Pointeur u8 dédié, joins sync/async, relais synchrone, réemprunt partagé avec ancêtre mutable ; mutation de provenance détectée | P — return match synchrone corrigé dans REFERENCE_EXPRESSIONS_CYCLE.md ; forme dans un cadre async encore ouverte |
| D1/P8, VE4, AS10 | Source durable, réemploi après attente, pas d’exposition hors capacité | Sources possédées, drop après copie, même slot réutilisé ; drop prématuré/échappement refusés ; deux arrêts de capacité avant usage | P — scénarios déterministes, pas de preuve générale de nettoyage |

Quinze méthodes : 24 exécutions normales, deux arrêts contrôlés et 31 refus
attendus par passage. Quatre mutations détectées. UBSan fatal ; l’essai ASan
est inconclusif (délai également reproduit avec un programme C vide).
L’écart `validation/open-join-element-match-expression.crust` est maintenant
corrigé par le cycle suivant. Les obligations générales des sept brouillons
restent ouvertes.

### B5 / D1 — emprunts produits par les expressions conditionnelles synchrones

Preuves : [REFERENCE_EXPRESSIONS_CYCLE.md](cycles/REFERENCE_EXPRESSIONS_CYCLE.md),
`tests/test_reference_expressions.py`, journaux reference-expressions-*.
Pas de changement normatif. Quatorze méthodes : trente exécutions natives
normales et 63 refus attendus par passage, dont deux du profil reset historique.

| Règles | Invariant / interactions | Preuves exécutables | Limites |
| --- | --- | --- | --- |
| B5, B1/B2, D1 | Toutes les provenances et ascendants restent protégés jusqu’au dernier usage | Deux pools, branches imbriquées, if dans boucle, porteur de match mutable, refus de drop et accès précoces | P — expressions synchrones ; retours if async ajoutés dans ASYNC_REFERENCE_RETURNS_CYCLE.md |
| F5/B5, E6, VE6 | Une seule référence, du bon type, vers la branche choisie | Int/u8, pool/tableau dans les deux ordres, références de structures, modèle à trois valeurs graine 1771 | P — scénarios finis, pas preuve de toutes les dispositions |
| D1/D2, P8, PR1 | Pas de promotion de cible locale, nettoyage après usage | Cibles locales refusées avant fermeture du bras ; réemploi des pools après drop ; reset public refusé | P — reset historique testé séparément, pas réintroduit |
| B4a, AS8, RT6 | Condition puis seul bras sélectionné, provenance après join et contrat | Effets observables, join succès/EAGAIN, secours distinct, retours anticipés | P — intégration synchrone avec tâches |

Trois mutations sont détectées par les assertions de sortie/refus ou UBSan ;
une quatrième déclenche une garde interne du compilateur sur un programme
valide. L’oracle de sortie seul n’est pas crédité de cette quatrième détection.
Le contre-exemple `validation/open-async-reference-if-expression.crust` a ensuite
été corrigé dans ASYNC_REFERENCE_RETURNS_CYCLE.md. Le résultat conditionnel
reçu par liaison locale dans un cadre async reste ouvert.
Les journaux et limites précises figurent dans les rapports de cycle.

Écart AS2/RT5/RT6 suivant reproduit :
`validation/open-async-vector-value-result.crust` capture et retourne
`Result<(),u8>`, déjà accepté dans le voisin synchrone exécuté. La signature
async reste refusée. Le log conserve ce refus et la sortie du voisin valide.
Les dernières régressions UTF-8 et ABI du cycle métier ont chacune exécuté
15 méthodes avec succès après les corrections.


### Complément AS2/RT5/RT6/U1 — Résultats scalaires de vecteurs

[ASYNC_VECTOR_RESULTS_CYCLE.md](cycles/ASYNC_VECTOR_RESULTS_CYCLE.md) corrige le refus
`open-async-vector-value-result` ci-dessus. Son ancien log reste historique.

| Règles | Invariant et interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| AS2/AS4, RT5/RT6 | Captures et retours gardent le type complet et distinguent le résultat métier des erreurs de lancement | Huit familles : options Int/u8, replace Int/u8, try_push Int/u8, capacité et lecture ; deux variantes chacune ; observation sync/async, join direct et imbriqué ; quatre refus de lancement injectés | P — valeurs produites en synchrone ; méthodes productrices async encore ouvertes |
| U1, L6, V3 | Usage explicite, invalidation après drop, forme du motif et largeur de la charge | Copie, if/loop, réaffectation, retours directs, valeur refusée -23/255 ; mauvais types et usages après drop refusés ; mutations ciblées | P — pas tous les conteneurs/enums |
| RT6 / C | Statuts et valeurs copiés dans le bon champ C sans alias de pointeurs incompatible | Trois représentations communes déplacées dans l’en-tête partagé ; UBSan fatal O0/O2 ; contrôles ABI/tableaux/emprunts et régressions des résultats précédents | P — Clang arm64, pas ASan/TSan ni preuve universelle |
| Croissance bornée, PR1 | Résultat indépendant de la source après drop ; capacité et lecture gardent leur issue | Saturation réelle d’une région 1M, try_push/try_extend refusés ; EOF, Io et CapacityExceeded distincts ; source Vector détruite avant capture du résultat | P — production synchrone et transport async testés ; reset demeure absent du prototype |

Le module final comporte 11 méthodes : 56 exécutions natives et 13 refus
attendus. O0 est couvert par les dix premières méthodes puis la méthode de
join direct ; O2 exécute le module complet. Les traces et mutations sont
précisées dans le rapport. L’objectif global demeure ouvert.

Le prochain écart est matérialisé dans
`validation/open-async-vector-result-producer.crust` et son log : une opération
`try_push` directement dans le corps async reste refusée, malgré les signatures
et les résultats désormais pris en charge. C’est un programme valide à
implémenter, pas un exemple négatif de la sémantique.

### Complément VE3/VE4 × AS2/AS8 — Opérations de vecteurs dans les corps async

[ASYNC_VECTOR_OPERATIONS_CYCLE.md](cycles/ASYNC_VECTOR_OPERATIONS_CYCLE.md) corrige
le manque de production directe signalé au paragraphe précédent. Aucun
changement normatif ; `reset()` reste retiré selon PR1.

| Règles | Invariant / interactions | Preuves exécutables | Limites / statut |
| --- | --- | --- | --- |
| VE3/VE4, AS4/AS8, RT5/RT6 | Pop, remplacement et insertion gardent statut et valeur ; l’échec ne publie pas de nouveaux éléments | Huit familles et deux issues, états avant/après yield, ancienne valeur ou entrante refusée, région 1M réellement saturée, extension atomique, EOF/Io/capacité | P — Int/u8 ; conteneurs propriétaires et empruntés non couverts par ce lot |
| F4/B4a, AS2/AS15 | Receveur réservé avant les arguments ; instantané de chaque argument avant le suivant, même suspendu | Deux arguments suspendus, indice modifié par l’argument suivant, appels aliasant refusés et appel disjoint exécuté ; deux mutations détectées | P — opérations et formes du lot, pas tout appel arbitraire |
| B1/B2, VE5, AS12/MT6 | Dernier usage de vue libère la réservation ; join précède l’accès et le drop chez l’appelant | Réemploi après dernière lecture, trois continuations conflictuelles refusées, slice/byte renvoyés par await, auto-extension refusée, trois accès avant join refusés | P — pas preuve générale d’analyse de vivacité |
| AS10, D1, P8, H1 | La capture possédée est détruite une fois ; le résultat scalaire survit au réemploi | Succès et EAGAIN injecté, pool d’un slot, adresse réutilisée et compteur indépendant d’entrées du destructeur | P — deux allocations Vector du scénario, pas tous les graphes de nettoyage |
| U1, F5, VE1 | Résultats faillibles explicitement utilisés et types conservés | drop d’expression exécuté une fois, quatre usages manquants refusés, sept types/receveurs incompatibles refusés ; mutation du contrôle U1 détectée | P — formes scalaires testées |
| VE3/VE4, AS8 | Séquences de mutations conformes au modèle de liste indépendant | 56 opérations générées, graines 37/91, valeur et longueur observées après chaque transition ; mutations de charge et de statut détectées | P — 56 transitions, pas exploration exhaustive |

Le lot final comporte 15 méthodes, 35 exécutions natives et 21 refus attendus
par passage complet. O0/O2, UBSan fatal, cinq fautes injectées détectées.
Les logs, régressions et limites sont détaillés dans le rapport de cycle.

Contre-exemple F2 distinct conservé dans
`validation/open-read-error-residual-pattern.crust` : `Err(_)` après une variante
précise de ReadError est encore refusé par le parseur. Ce refus n’est pas
normatif. Les erreurs générales, les handles publics, scheduler, threads,
Select, mutex et autres écarts consignés restent à implémenter ; l’objectif
global n’est pas atteint.

### Complément F2 — Couverture résiduelle des erreurs

[RESIDUAL_ERROR_PATTERNS_CYCLE.md](cycles/RESIDUAL_ERROR_PATTERNS_CYCLE.md) corrige
le contre-exemple ReadError signalé ci-dessus. Le log initial reste historique.

| Règles | Invariant / interactions | Preuves | Limites / statut |
| --- | --- | --- | --- |
| F2, VE4, TX4 | Err(_) après une variante précise conserve le type et couvre seulement les erreurs restantes | Succès, EOF, Io, capacité en sync/async ; décodage Empty/MultipleChars/succès ; découpe OUT/CUT/vue ; trois mutations détectées | P — familles builtin, pas enums arbitraires |
| F2/F3, AS8 | Les corps résiduels s’exécutent une fois et peuvent fournir une valeur après suspension | Compteur et yield dans le bras ; régressions sur transferts, vues, propriétaires et retours précoces | P — chemins exécutés, pas preuve de toute duplication AST |
| F2/B5 | Exhaustivité et type exact demeurent requis | Cinq refus : Ok absent, doublons, deux formes de bras inaccessibles, famille incompatible | P — ensembles finis des tests |

Six méthodes nouvelles, 19 exécutions natives et cinq refus par passage.
La liaison générale `Err(error)` de ReadError en async reste ouverte :
`validation/open-async-read-error-binding.crust` et son log reproduisent ce
manque, distinct de la correction du wildcard. Voir le rapport pour les traces,
options de validation et limites.

### Complément F2/B5/AS8 — Valeurs d’erreurs builtin

[BUILTIN_ERROR_VALUES_CYCLE.md](cycles/BUILTIN_ERROR_VALUES_CYCLE.md) corrige le
refus de `Err(error)` signalé ci-dessus. Aucune règle normative nouvelle.

| Règles | Invariant / interactions | Preuves exécutées | Limites / statut |
| --- | --- | --- | --- |
| F2/B5, RT5/RT6 | Le type d’erreur et sa variante sont conservés ; l’erreur de lancement reste distincte de l’erreur métier | Sept types, treize variantes ; contrats sync, captures, await direct et handle, join et enveloppes imbriquées ; EAGAIN injecté | P — valeurs builtin Copy ; pas enums arbitraires, ni emprunts de ces valeurs |
| F2, VE4, TX4, F5 | Err extrait le statut et non la charge de succès | Treize issues d’opérations, erreurs UTF-8 et vecteur, capacité réelle 1M ; liaison après variante précise, match exhaustif ; trois mutations d’extraction détectées | P — APIs et variantes du lot |
| B1/B5, AS10/AS12, D1/P8 | Une erreur sans emprunt ne retient pas le Result ni son stockage source | Copie puis drop du Result et yield, drop du vecteur/String puis réemploi du slot, lecture de l’erreur après join | P — chemins exécutés, pas tous conteneurs |
| B5/F5, F2, V3 | Pas de conversion silencieuse entre erreurs, entiers, emprunts ou autres types | Matrice de 42 paires nominales incompatibles ; captures async et contrats sync ; annotations/retours/motifs incompatibles, usage après drop et matchs incomplets refusés | P — 61 refus dans le module final ; deux mutations de garde détectées |
| AS8/F4 | Les résultats de contrôle et les erreurs calculées se matérialisent une fois | If, loop, réaffectation, copie, drop, yield, sujet calculé avec compteur ; résultat transporté dans les champs C dédiés | P — pas preuve de toute combinaison de contrôle |

Le module final comporte 14 méthodes, 60 exécutions natives et 61 refus
attendus par passage complet. Les passes O0/O2, compléments, régressions et
mutations sont détaillés dans le rapport. Une ancienne ancre de mutation
de type de capture est mise à jour pour viser le contrôle étendu, sans
modifier son oracle.

Écart suivant reproduit : `validation/open-async-vector-remove.crust` reste
refusé pour expression non prise en charge dans le corps async. Le programme
est valide selon VE3 ; le refus n’est pas normatif. Les autres lignes N/P et
l’objectif global restent ouverts.

### Complément B5/AS11/AS12 — Retour conditionnel d’un emprunt async

Preuves : [ASYNC_REFERENCE_RETURNS_CYCLE.md](cycles/ASYNC_REFERENCE_RETURNS_CYCLE.md).
Aucune modification normative. Dix méthodes, 23 exécutions natives et
24 refus attendus dans le module final ; périmètre détaillé dans le rapport.

| Règles | Invariant / interactions | Preuves | Statut et limites |
| --- | --- | --- | --- |
| B5, AS8/AS12 | Chaque branche terminale transmet la bonne adresse et conserve toutes les provenances | Deux modes, Int/u8, cases tableaux/vecteurs, await, relais, modèle de trois cibles ; mutations de sélection et provenance détectées | P — return if ; liaison locale conditionnelle encore refusée |
| B1/B2/B3, D1, AS11 | Sources durables et exclusivité jusqu’au dernier usage | Refus des locaux, propriétaires capturés, mauvais mode et accès prématurés aux alternatives ; accès après usage admis | P — cas finis, pas tous agrégats |
| AS10, P8, RT6 | Nettoyage terminé avant join et réemploi du slot | Capture directe puis enfant inactif propriétaire, traces exactes et pool d’un slot ; mutation de chemin de nettoyage détectée après ajout du cas enfant | P — trois mutations ciblées, survie initiale conservée dans le rapport |

Contre-exemple suivant : `validation/open-async-local-reference-if.crust`
avec diagnostic conservé. Le résultat conditionnel reçu dans une liaison puis
retourné après yield devrait être admis ; ce manque n’est pas une règle de refus.
Les autres écarts des sept brouillons demeurent ; objectif global non atteint.

Validation finale du cycle synchrone précédent : 158 méthodes, 188,023 s, OK,
UBSan activé ; quatorze méthodes nouvelles en O2, helper historique à
l’optimisation par défaut. Les 18 erreurs initiales de trois anciennes méthodes
ont été reproduites avec le compilateur antérieur : elles contredisaient U1.
Les fixtures incluent maintenant une lecture explicite, avec assertions de
nettoyage inchangées. Voir REFERENCE_EXPRESSIONS_CYCLE.md pour les traces.

Validation du complément async : 43 méthodes O2 + UBSan, 85,039 s, OK, puis
le test de nettoyage d’enfant ajouté, OK à O0 et O2. Les neuf premières méthodes
passent aussi à O0 (17,467 s). Rapport : ASYNC_REFERENCE_RETURNS_CYCLE.md.

### Complément B2/B4/B5/AS12 — Liaisons empruntées conditionnelles async

[ASYNC_LOCAL_REFERENCES_CYCLE.md](cycles/ASYNC_LOCAL_REFERENCES_CYCLE.md) corrige
`open-async-local-reference-if.crust`, sans changement normatif. Onze méthodes,
23 exécutions natives et 34 refus par passage complet. Les dix premières méthodes
et le complément drop/transfert ont été exécutés à O0 et O2, UBSan fatal.
Régressions de 39 et 10 méthodes réussies ; traces et durées dans le rapport.

| Règles | Invariant / interactions | Preuves | Statut et limites |
| --- | --- | --- | --- |
| B5/AS8/AS12 | Sélection et provenance conservées à travers liaison, yield, relais et retour | Int/u8, deux branches, await et push_new, modèle indépendant graine 2097 ; mutations de pointeur et contrat détectées | P — if et blocs ; match async encore ouvert |
| B1/B2/B3, D1/AS11 | Toutes les cibles et les parents nécessaires restent réservés ; pas de promotion locale | Réemprunt sorti du bloc, prêt enfant, dernier usage, boucle/continue/break, refus de drop/transfert prématurés ; mutations de cible et d’ascendance détectées | P — tableaux/vecteurs scalaires et références injectées |
| B4/V3 | Écriture explicite, type et mode exacts | Alias implicite maintenu refusé, réemprunts explicites admis, mauvaise annotation/mode/type et écriture sans let mut refusés | P — pas d’affectations générales entre références |
| AS10/P8/RT6 | Réemploi après fin d’emprunt et nettoyage | Drop puis pool réemployé ; cycle précédent de nettoyage d’enfant propriétaire réexécuté | P — runtime inchangé, pas preuve exhaustive |

Contre-exemple suivant conservé : `validation/open-async-local-reference-match.crust`
et son diagnostic. Le refus actuel d’un résultat emprunté de match dans un cadre
async n’est pas une règle normative. Les autres lignes N/P restent ouvertes.

### Complément B1/B5/F2/AS12 — Matchs empruntés async

[ASYNC_MATCH_REFERENCES_CYCLE.md](cycles/ASYNC_MATCH_REFERENCES_CYCLE.md) corrige
`open-async-local-reference-match.crust` sans changement normatif.
Treize méthodes : 36 exécutions natives normales et 32 refus par passage complet.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| B5/AS12, RT5/RT6 | Provenance du Ok et du secours conservée après await, yield et retour | Résultat stocké/direct, modes ref/mut, Int/u8, EAGAIN, modèle indépendant de trois cibles ; mutation du contrat détectée | P — familles builtin, pas tous agrégats |
| B1/B2/B3 | Un porteur Result ne fournit pas deux capacités mutables utilisées simultanément | Contre-exemple auparavant accepté, désormais refusé ; seconde projection après dernier usage et deux projections partagées admises ; mutation du porteur détectée | P — référence directe dans Result de handle |
| D1/AS11 | Pas de prolongation implicite d’une cible locale | Cible de bras refusée ; mauvais mode/type/Result entier refusés | P — programmes finis |
| F2/B4a/AS8 | Sujet évalué avant le bon bras ; suspension et retour anticipé préservés | Marqueurs succès/échec, branches inversées, match imbriqué, conversion/pop et erreurs builtin ; mutation de statut détectée | P — familles et formes exécutées |

Le programme invalide de double projection est conservé dans
`validation/async-match-overlapping-result-borrows.crust`, avec logs avant/après.
Son refus ne repose plus sur un conflit accidentel entre deux branches de secours.
Le prochain manque reproduit est le résultat emprunté de boucle async :
`validation/open-async-reference-loop-result.crust`. Les autres obligations
ouvertes restent inchangées ; objectif global non atteint.

Preuves finales du cycle match async : 13 méthodes à O0 (22,933 s) et
62 méthodes à O2 (86,489 s), toutes réussies, UBSan fatal ; quatre mutations
ciblées détectées. Les nombres et limites détaillés figurent dans
ASYNC_MATCH_REFERENCES_CYCLE.md. Le passage initial de 59 méthodes ne couvrait
pas le contre-exemple de double projection, ajouté à la régression finale.

### Complément S5a/B5/AS12 — Résultats empruntés de boucles async

[ASYNC_LOOP_REFERENCES_CYCLE.md](cycles/ASYNC_LOOP_REFERENCES_CYCLE.md) traite
`open-async-reference-loop-result.crust`, sans changement normatif.
Dix méthodes : 18 exécutions natives et 28 refus par passage complet.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5a/B5/AS12 | Chaque break et chaque return anticipé contribue aux cibles du résultat | Modes ref/mut, boucles imbriquées, deux branches, relais async ; contre-exemple de retour imbriqué corrigé ; mutations de contrats détectées | P — formes exécutées, break dans une initialisation conditionnelle encore refusé |
| B1/B2/B3/D1/AS11 | Cibles et parents protégés après sortie, sans prolongation de stockage local | Mutation/lecture/drop prématurés refusés ; locaux non durables refusés ; accès et réemploi après usage admis | P — Int/u8 et tableaux/vecteurs scalaires |
| S4/S5/AS8/AS10/RT6 | Suspension et nettoyage préservent résultat et stockage | Continue répétés, break, enfant inactif propriétaire nettoyé une fois, pool de capacité un réemployé ; mutation de nettoyage détectée | P — pas de preuve générale de nettoyage |
| S5a/RT5/B4a | Choix du pointeur correct et modes/types homogènes | Modèle indépendant des trois indices ; lancement normal/EAGAIN ; type/mode manquant ou divergent refusé | P — modèle fini |

Le contre-exemple invalide initialement accepté est conservé dans
`validation/async-loop-early-return-provenance.crust`, avec traces avant/après.
Le module final passe à O0 + UBSan (10 méthodes, 8,501 s) ; quatre mutations
sont détectées. La régression O2 + UBSan est terminée : 80 méthodes,
92,284 s, OK, sans saut. Rapport et commandes disponibles dans le cycle.
Le prochain manque reproduit est `validation/open-async-loop-break-in-initializer.crust`.
Les autres obligations des sept brouillons restent ouvertes.

### Complément S5/S5a/AS12 — Sorties depuis les expressions async

[ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md](cycles/ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md)
traite `open-async-loop-break-in-initializer.crust`, sans modification normative.
Huit méthodes : 23 exécutions natives et 21 refus par passage complet.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/B5/AS12 | Les sorties imbriquées contribuent au contrat de la bonne boucle | If, blocs, match, opérandes de break/return, boucles internes ; toutes les cibles protégées et cible interne non retenue sans raison ; mutation de provenance détectée | P — initialisation sans aucune branche continuante encore ouverte |
| S4/AS8/B2 | Continue reprend la bonne itération sans fournir de résultat fictif | Initialisation et affectation, yield, compteur et marqueurs ; tâche consommée avant reprise refusée ; mutation continue→break détectée par UBSan | P — types et chemins exécutés |
| D1/AS10/AS11/RT6 | Les scopes quittés sont nettoyés et les cibles restent durables | Enfant inactif propriétaire, destruction une fois et slot réemployé après join ; cible locale refusée ; mutations de nettoyage détectées par invariant et exécution native | P — pas de preuve générale de nettoyage |
| B1/B3/RT5 | Le résultat de match attendu garde ses dépendances à travers break | Succès et EAGAIN injecté, puis utilisation du résultat emprunté ; mutation des deux cibles refusée | P — résultat direct &mut Int |

Le module passe à O0 + UBSan : 8 méthodes, 9,458 s. Quatre fautes sont détectées,
dont une par le contrôle du compilateur ; le classement initial inconclusive
et son explication sont conservés dans le rapport. Régression O2 + UBSan
terminée : 89 méthodes, 88,707 s, OK, sans saut.
Le prochain manque reproduit est `validation/open-async-diverging-initializer.crust`.
Les autres obligations ouvertes des sept brouillons restent inchangées.

### Complément S5/B4a/AS12 — Expressions async sans continuation

[ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md](cycles/ASYNC_DIVERGING_EXPRESSIONS_CYCLE.md)
traite `open-async-diverging-initializer.crust`, sans changement normatif.
Douze méthodes : 42 exécutions natives et 33 refus par passage complet.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/B5/AS12 | Pas de receveur ni de provenance fictifs après une expression sans continuation | Initialisation, affectation, print, loop, return, match attendu ; deux sources protégées ; contre-exemple du retour c inaccessible corrigé | P — annotation tableau sans continuation encore ouverte |
| B4a/AS10/RT6 | Un transfert préparé reste responsable de son nettoyage si l’appel est interrompu | Fuite reproduite avec pool de capacité un, désormais réemployé ; branches interrompues/normales, Result propriétaire et EAGAIN ; mutation de nettoyage détectée | P — captures propriétaires scalaires/Result exercées, pas tous agrégats |
| S4/S5/AS8 | Une boucle interne à un argument ne détruit pas les captures de l’appel extérieur | Suspension et break interne avant création de tâche ; mutation de profondeur détectée par UBSan après raffinement | P — première faute trop large classée inconclusive et conservée |
| B1/B3/D1/AS11 | Les chemins sortants conservent les règles de mode, exclusivité et durée de vie | Mutations prématurées, cibles locales, anciens accès déplacés et break sans valeur refusés ; dernière utilisation puis réemploi admis | P — programme fini |
| S5/B4a | Court-circuit et continue gardent les chemins qui continuent | &&/||, deux chemins ; modèle arithmétique de 1, 2 et 4 itérations | P — pas de preuve générale de contrôle de flux |

Les onze premières méthodes passent à O0 + UBSan (25,569 s). Le complément
court-circuit passe à O0 (2,461 s) et O2 (2,250 s). La régression O2 + UBSan
élargie est terminée : 176 méthodes, 247,789 s, OK, sans saut ; elle précède
l’ajout du complément court-circuit exécuté séparément.
Quatre fautes sont détectées ; l’une a été raffinée après une première
observation inconclusive. Les traces et les deux défauts corrigés figurent
dans le rapport. Le prochain manque est
`validation/open-async-diverging-typed-initializer.crust`.
Les autres obligations des sept brouillons restent ouvertes.

### Complément S5/E3/AS12 — Réceptions typées sans continuation

[ASYNC_TYPED_DIVERGENCE_CYCLE.md](cycles/ASYNC_TYPED_DIVERGENCE_CYCLE.md) traite
`open-async-diverging-typed-initializer.crust`, sans changement normatif.
Six méthodes : 25 exécutions natives et 27 refus par passage complet.

| Règles | Invariant / interactions | Preuves | Statut / limites |
| --- | --- | --- | --- |
| S5/S5a/E3/E7 | Pas de matérialisation d’un receveur qu’aucun chemin n’atteint | Types scalaires, résultats builtin, tableaux vides/imbriqués/de références ; if, bloc, match, loop, return, continue ; désactivation du traitement détectée | P — répertoire async reconnu, pas tous les agrégats |
| V3/E3/E5 | Chaque chemin continuant conserve le type déclaré | Voisin avec tableau réellement fourni ; types/dimensions incorrects et annotations inconnues refusés ; mutation de validation du type détectée | P — scénarios exécutés |
| B1/B3/B5/D1/AS11/AS12 | L’annotation n’efface pas les cibles ou restrictions | Cibles locales, modes divergents et mutations avant dernier usage refusés ; effacement de provenance détecté | P — Int/u8 et références Int |
| B4a/AS10/RT6 | L’appel interrompu nettoie les transferts préparés | Réemploi d’un pool de capacité un, destruction une fois ; faute de nettoyage détectée | P — capture Int dans ce complément |

Le module final passe à O0 + UBSan : 6 méthodes, 13,290 s. Quatre fautes sont
détectées. La régression O2 + UBSan est terminée : 96 méthodes,
114,353 s, OK, sans saut.
À la fin de ce cycle des initialisations typées, RT8 était encore N : le
programme minimal `validation/open-native-thread-basic.crust` était refusé
au parsing malgré sa validité normative.

Suivi : ce constat est historique. Le programme minimal s’exécute désormais
avec la sortie 7, et RT8 est P dans la table actuelle. Le
[cycle des blocs natifs](cycles/NATIVE_BLOCK_LOWERING_CYCLE.md) comprend 13 méthodes,
29 exécutions natives et 40 refus ; les identités et traces de destruction
ont été renforcées et réexécutées à O0/O2. La régression O2 de 81 méthodes
est réussie. Un premier effacement complet de provenance est inconclusif
dans le protocole de mutation ; la perte affinée d’une seule origine est
détectée par l’acceptation indue d’un accès. Les programmes valides encore
refusés avec auxiliaire sync et pool local async restent conservés.

### Appels synchrones empruntés dans les états async et natifs

Voir [le cycle](cycles/SYNC_BORROW_CALLS_CYCLE.md) pour les configurations, journaux et limites.

| Règles | Invariant exercé | Preuves | Statut |
| --- | --- | --- | --- |
| B1/B2/B4a, AS2/AS15 | Prêts préparés protégés pendant les arguments, même suspendus ; fin au dernier usage avec continuations et boucles | Cas admis/refusés et mutations de réservation et de liveness | P — Int et mutable u8 |
| B5/D1/D3, AS9/AS12, MT6 | Union des cibles du contrat, jusqu’au dernier usage après await/join ; pas de fuite de cible locale | Deux cibles/une cible, relais et capture enfant ; mutations du pointeur et des cibles | P — paramètres directs |
| L6, B3, RT8 | Drop scalaire invalide la liaison après contrôle des prêts | Int/Bool/u8, lecture/écriture/double drop refusés ; pool réutilisé après appel interrompu | P — formes exécutées |

### Appels synchrones partagés u8 depuis les états

Rapport : [SYNC_BYTE_BORROW_CALLS_CYCLE.md](cycles/SYNC_BYTE_BORROW_CALLS_CYCLE.md).

| Règles | Invariant et interactions | Preuves exécutées | Limites |
| --- | --- | --- | --- |
| B4/B4a, TX5, AS2/AS15 | &u8 garde sa cible pendant les arguments, même suspendus ; pas de & implicite | Littéral, tableau, local, réemprunt, appel imbriqué, yield/return ; mutation du prêt préparé | P — signatures et expressions du lot |
| B5/D1, AS9/AS12, MT6 | Cibles du résultat exactes depuis les contrats, aucune fuite de local | choose/first, enfant, join, source non retournée libérée ; mutations des cibles, du contrat et du pointeur | P — paramètres directs |
| B2/B3/L6, TX12 | Dernier usage autorise le drop/réemploi ; un usage futur l’interdit | Boucle, parent mutable, pool String capacité un, échec de lancement ; reset seulement historique | P — scénarios finis |
| RT8, TX5 | Type de capture d’octet et résultat emprunté conservés | Bloc natif capturant &String[index], retour via auxiliaire puis join, drop prématuré refusé | P — autres captures/types généraux ouverts |

Exécutions de ce complément : 119 méthodes natives O2 réussies avant les derniers
raccordements, puis 15 méthodes ciblées finales O2 réussies (dont la fixture UTF-8
corrigée). Douze méthodes u8 à O0 et baseline finale O2 vertes ; cinq mutations
u8 détectées. La sélection UTF-8 de 80 méthodes avait un échec de diagnostic
lié à la double transformation de la fixture, corrigé et réexécuté ; ce journal
n’est pas marqué vert. Voir le tableau chronologique du rapport pour les
contrôles après chaque modification et les limites de chaque passage.

### Transferts propriétaires aux helpers synchrones depuis les états

Rapport : [SYNC_OWNED_CALLS_CYCLE.md](cycles/SYNC_OWNED_CALLS_CYCLE.md).

| Règles | Invariant exercé | Preuves | Limites |
| --- | --- | --- | --- |
| B4/B4a/T1, B1/B2 | -> obligatoire, ancien nom invalidé dès préparation, dernier usage du prêt avant transfert | Ordres admis/refusés, vue nommée, prêts mutables, sous-appels ; mutation d’invalidation | P — types Int/String/Vector<Int/u8> |
| AS8/AS12/L6 | Arguments déplacés vivants à travers yield ; nettoyage unique si un argument sort | Un/deux arguments préparés, retour anticipé, boucle interne, réemploi ; mutations d’inscription et d’ordre | P — formes exécutées |
| T6/T9/T11, AS9/RT8 | Adresse et source réelle conservées au retour ; autre candidat détruit | Deux pools, choix 0/1, adresses, join, réemploi ; mutation d’export | P — candidats directs |
| B4c/AS7/MT6 | Captures vivantes avant join ; seuls les pools du résultat retenus ensuite | Factory synchrone, helper first, pool enfant détruit après join, fuite du handle refusée ; mutation de provenance | P — approximation conservative sur les autres candidats |
| U1/L6/V4 | Résultat reçu, transmis ou drop ; remplacement après évaluation | Appel seul/_/liaison inutilisée refusés ; drop(expression), remplacement et annotations A<T> | P — signatures du lot |

Exécutions du cycle propriétaire : 13 méthodes O0, 134 méthodes de régression
native/runtime O2 et 130 méthodes de contrats O2 réussies. Baseline finale
actualisée verte ; six fautes injectées détectées et une omission de remise
à NULL sans effet sur les chemins examinés (champ exclu par consumed et
cleanup_path), explicitement non comptée comme détection. Les dernières
vérifications de fuite de pool/cible sont incluses dans la baseline finale
et le complément O0. Aucune preuve générale de sûreté.

### Booléens des helpers et copies primitives en sortie de bloc

Rapport : [SYNC_BOOL_CALLS_CYCLE.md](cycles/SYNC_BOOL_CALLS_CYCLE.md).

| Règles | Invariant exercé | Preuves | Limites |
| --- | --- | --- | --- |
| I5/B4/B4a, AS2/RT8 | Type booléen distinct d’Int/u8 à travers contrat, état et résultat natif | Table de vérité indépendante, appels imbriqués, capture et annotations ; mutations du type et de la valeur | P — signatures `bool` synchrones et `Bool` des états existantes |
| B4a/B1/B2 | Ordre gauche à droite et réservation des arguments préparés | Courts-circuits, booléen copié avant mutation/transfert, mutable préparé incompatible refusé | P — chemins finis |
| S4/S5/L6/AS10/AS12 | Copie primitive avant nettoyage ; résultat indépendant de sa source | Pool local fermé après join, réemploi, early return pendant préparation ; traces uniques | P — Int/bool/u8/char ; pas de preuve générale |
| U1/B4e | Résultat propriétaire utilisé même dans un chemin qui retourne | Fixture historique corrigée, original sans usage refusé, destruction conservée au return | P — erreur de fixture reproduite sur compilateur antérieur |
| A1/A2/A4/AS12/AS13 | Prêt de pool distinct de provenance du résultat | Cas historiquement refusé `validation/open-async-pool-helper.crust`, désormais exécuté dans ASYNC_POOL_INJECTION_CYCLE.md | P — Int/String/Vector<Int/u8> injectés ; pools locaux et autres types ouverts |

Dix méthodes ciblées O0 : 18 exécutions C, 16 refus, vérification sans
génération de bridge. Régression native/runtime O2 : 144 méthodes vertes.
Contrats/scopes : 249 méthodes, 248 vertes et une fixture U1 corrigée puis
réexécutée séparément ; le premier journal n’est pas présenté comme vert.
Baseline finale O2 verte et quatre fautes injectées détectées ; omission du
snapshot supplémentaire sans effet sur les chemins choisis, non comptée comme
détection. UBSan fatal, Clang C11 pthread ; aucun nouveau résultat ASan/TSan.

### Pools injectés dans les états async et natifs

Rapport : [ASYNC_POOL_INJECTION_CYCLE.md](cycles/ASYNC_POOL_INJECTION_CYCLE.md).

| Règles | Invariant et interactions | Preuves exécutées | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A6, AS2/AS13, MT3 | Source durable et prêt actif dès capture jusqu’à attente ; absence de fermeture du pool injecté | Tâche inactive, enfant, fabrique de handle, bloc natif, fuite refusée et EAGAIN ; mutations de réservation et de consommation détectées | P — quatre types de pools injectés |
| B1/B2/B4/B4a | Mode/type exacts, ordre gauche à droite, dernier usage des alias | Prêts nommés, partagés simultanés, arguments suspendus, refus de promotion mutable ; trois mutations détectées | P — pas de pools locaux aux états |
| B4c/T11/A4, AS12 | Le résultat garde les sources possibles sans prolonger le prêt exclusif | Deux candidats, source non retournée fermée, nouvelle allocation après join ; mutation de provenance détectée | P — contrats du sous-ensemble pris en charge |
| V4/V5/L1/L6/S5, AS8/AS10 | Création typée, adresse stable, destruction unique et réemploi après sortie | Remplacement, return/yield/break/continue, pool capacité un, artefact C d’identité ; mutation du type nominal détectée | P — création directe Int ; String/Vector via helper |

Module final : 19 méthodes à O0 et O2 ; baseline O2 de 28 exécutions C,
36 refus et une vérification seule. Sept fautes injectées détectées.
Régressions O2 : 162 méthodes natives/runtime et 153 de contrats réussies,
avant le dernier garde de type et, pour les 162, avant le test de boucle ajouté.
Les contrôles ciblés finaux couvrent ces ajouts. Aucun résultat ASan/TSan ni
preuve générale ajouté. L’ensemble des sept brouillons reste partiellement
implémenté.

### Création directe de collections dans les états

Rapport : [ASYNC_COLLECTION_CREATION_CYCLE.md](cycles/ASYNC_COLLECTION_CREATION_CYCLE.md).

| Règles | Invariant et interactions | Preuves | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A4, H1, AS12 | Pool injecté typé, source du résultat durable, prêt distinct du stockage | Création directe, retour nommé/calculé, enfant, fermeture de source disjointe, fuite refusée ; mutations type/provenance détectées | P — String/Vector<Int/u8> |
| B1/B2/B4a, VE1, G12 | Case empruntée protégée avant évaluation de l’indice et jusqu’au dernier usage | Yield dans indice, prêts partagés/mutables, enfant et résultat réemprunté ; mutations réservation/mutabilité/indice détectées | P — protection conservative de la collection |
| V4/V5/L1/L6, AS10, RT8 | Nettoyage unique, adresse stable, reprise et réemploi | Remplacement, continue, retour, transfert temporaire interrompu, bloc natif, EAGAIN ; mutation nettoyage détectée | P — types du lot, pas de pool local aux états |
| E1/TX9/TX10/VE1 | Construction vide typée, bornes avant publication | Trois pools pleins avant destruction et quatre indices hors limites ; défaut vide et contenu UTF-8 | P — régions annotées async ouvertes |

Passages ciblés finaux O0/O2 : 14 méthodes, 34 exécutions normales, sept
arrêts diagnostiqués attendus, 64 refus. Six fautes injectées détectées.
Les résultats des régressions élargies sont consignés dans le rapport du cycle.
Régressions finales O2 : 177 méthodes natives/runtime et 97 d’interactions
réussies, avec recouvrement entre sélections. Les sept mutations du lot des
pools sont également rejouées et détectées. Aucun résultat ASan/TSan ajouté.

### Pools locaux dans les états async et natifs

Rapport : [ASYNC_LOCAL_POOLS_CYCLE.md](cycles/ASYNC_LOCAL_POOLS_CYCLE.md).
Validation ciblée et régression native exécutées. Module async_runtime :
275 méthodes, deux divergences de diagnostics historiques corrigées et
réexécutées séparément ; voir le rapport, sans considérer le journal initial vert.

| Règles | Invariant et interactions | Preuves ciblées | Limites |
| --- | --- | --- | --- |
| A1/A2/A3/A6, AS8, RT8 | Source à adresse stable dans l’état, créée à l’exécution et fermée après ses allocations | Pool local Int/String/Vector<Int/u8>, yield, thread natif, retour scalaire, EAGAIN et état inactif | P — emprunts nommés de sources et autres types ouverts |
| T6/T9/T11, B4c, AS12 | Toutes les origines durables à chaque sortie, y compris après remplacement et jonction | Retours, helpers, await/join, blocs et break ; modèle de 12 cas d’ascendance ; mutations d’origines et de frontière détectées | P — modèle fini, pas de preuve générale |
| A4/MT7, B4 | Dépendance de stockage distincte de l’emprunt exclusif du pool | Enfant propriétaire et nouvelle allocation concurrente admis ; enfant empruntant le pool puis allocation prématurée refusé | P — ordonnancements testés seulement |
| S4/S5/L1/L2, AS10/AS14 | Nettoyage puis fermeture, une fois, même sur continue/retour/argument interrompu | Compteur indépendant de quatre ouvertures/fermetures ; traces de destructions ; mutation de fermeture détectée | P — UBSan, pas ASan/TSan |

Baseline finale ciblée O2 : 18 méthodes, 21 exécutions normales, un arrêt
diagnostiqué et 20 refus ; six mutations détectées. Modèle séparé O0/O2 :
neuf exécutions et trois refus. Le rapport conserve les erreurs de fixtures
et l’arrêt de la première campagne sur son ancre ambiguë. Les résultats
du module complet async_runtime sont de 273 réussites et deux assertions de
diagnostics corrigées puis réexécutées à O2 (deux réussites).
La régression native/runtime O2 est terminée : 195 méthodes, 175,346 s, OK.

### Emprunts nommés de pools dans les états

Rapport : [ASYNC_POOL_ALIASES_CYCLE.md](cycles/ASYNC_POOL_ALIASES_CYCLE.md).

| Règles | Invariant et interactions | Preuves | Limites |
| --- | --- | --- | --- |
| B1/B2/B4/B4a | Mode, niveau explicite, dernier usage et arguments préparés | Alias partagés/mutables, réemprunts, appels sync/async/natifs ; mutations niveau/mode/conflit détectées | P — quatre types de pools |
| A1/A4, D1/T11, AS12 | Le résultat garde le pool effectif, même via alias et helper | Retours refusés, source disjointe libérée, modèle de 12 cas ; mutations origine/résumé détectées | P — modèle d’ascendance fini |
| AS2/AS13, RT8 | La capture garde le prêt du pool après sortie du bloc de l’alias | Tâche exportée puis accès prématuré refusé ; faute initialement survivante détectée après ajout de ce cas | P — ordonnancements testés |
| L1/L2/L6, G12 | Nettoyage et réemploi sans déplacement | Quatre types, suspensions, continue/break, drop, reprise du pool ; régression de six mutations locales | P — pas ASan/TSan ni preuve générale |

Ciblé final O2 : 14 méthodes, 15 exécutions C et 27 refus, sept mutations
détectées. Ciblé + modèle O0 : 15 méthodes réussies. Modèle O2 : neuf
exécutions et trois refus. La régression native O2 de 209 méthodes est
terminée avec succès ; voir le rapport pour les durées et journaux.

### Régions annotées dans les blocs async et natifs

Rapport : [ASYNC_REGIONS_CYCLE.md](cycles/ASYNC_REGIONS_CYCLE.md).

| Règles | Invariant et interactions | Preuves ciblées | Limites |
| --- | --- | --- | --- |
| G5/G6/G7 | Configuration lexicale, héritée, remplacée et restaurée | Trois collections, blocs instructions/scalaires/empruntés/propriétaires, oracle des classes physiques ; mutations héritage/restauration détectées | P — constructions async prises en charge |
| G4/G7/G12, AS8/AS12 | Limite conservée après suspension/transfert/retour | Retours conditionnels, réception dans un autre gabarit, épuisement à 1M sans publication partielle ; mutations String/Vector détectées | P — cas finis, sans mesure de performance |
| G10, S4/S5, L1/L2 | Nettoyage des régions sur les chemins de sortie | Continue/break, return, drop et réemploi ; modèle de deux arbres, 28 régions | P — pas de preuve générale |
| A1/A4, D1, B1/B2 | Annotation sans promotion de source ni assouplissement des prêts | Pool trop court et accès pendant un prêt refusés | P — pools et types déjà pris en charge |

Neuf méthodes ciblées O0/O2 réussies, 14 exécutions C et trois refus à O2.
Quatre mutations détectées ; modèle généré avec graines 19 et 73.
Régressions O2 terminées : 102 méthodes pools/collections/régions et
36 méthodes de contrôle de flux, toutes réussies. Les sélections se
recouvrent avec d’autres cycles et ne constituent pas une preuve générale.

### Références de structures dans les états async et natifs

Rapport : [ASYNC_STRUCT_CAPTURES_CYCLE.md](cycles/ASYNC_STRUCT_CAPTURES_CYCLE.md).

| Règles | Invariant et interactions | Preuves ciblées | Limites |
| --- | --- | --- | --- |
| ST5/ST7, AS8/AS9 | Pointeur stable et offsets des champs, mutation en place | Structures imbriquées, pool capacité un, identité après attente et réemploi ; mutations offset/écriture détectées | P — champs Int uniquement |
| B1/B2/B4/B4a, ST9, AS2/AS15, MT1/MT2 | Réservation dès capture et arguments préparés, dernier usage | Alias, enfants, prêt racine après sortie du bloc ; modèle 16 combinaisons et mutations mode/prêt détectées | P — pas de graphe de champs références |
| AS13/AS14, MT3, L1/L6 | Cible durable, destruction unique par son scope, attente obligatoire | Fuite refusée, drop inactif, lancement refusé injecté, traces de destruction | P — ordonnancements exercés |
| ME2/ME3, TF1–TF5, B4c | Résolution nominale des méthodes et contrats des helpers | Type feature historique, retours directs de références de structures, types incompatibles refusés | P — projections de résultats empruntés encore ouvertes |

Ciblé final O2 : 14 méthodes, 15 exécutions C dont une avec échec de lancement
injecté, 29 refus statiques. Modèle O0/O2 : 11 exécutions et cinq refus.
Six mutations détectées ; complément O0 sur les destructions. Les 76 méthodes
de régression des features/références et les 231 méthodes natives réussissent.
La régression native précède le dernier test partagé et les assertions de
destruction supplémentaires ; les passages ciblés finaux couvrent ces ajouts.

### Captures de structures contenant des références

Rapport : [ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md](cycles/ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md).

| Règles | Invariant et interactions | Preuves ciblées | Limites |
| --- | --- | --- | --- |
| ST5/ST7, AS8/AS9 | Pointeurs conservés et offsets mixtes corrects | Lectures Int/&Int/&mut Int, helpers, méthodes, boucles et blocs natifs ; mutations offsets/lecture détectées | P — construction imbriquée à références non exercée |
| B1/B2/B4/B4a, AS2/AS13/AS15, MT1–MT4/MT8 | Capture → porteur → cible reste protecteur | 16 cas du modèle, alias, arguments distincts/aliasés, fuites refusées ; mutations bridge/capture détectées | P — projections directes, effets de remplacement et graphes plus généraux ouverts |
| AS10/AS14, L1/L6, MT7 | L'attente ou le drop inactif libère les prêts sans détruire les cibles | LaunchFailed injecté, traces uniques, réemploi du slot après drop, accès autorisé après dernier usage | P — ordonnancements et types exercés |
| PR1, ancien A5 | Reset historique voit les dépendances transitives | Contre-exemple admis à tort corrigé dans check et compilation ; mutation premier lien détectée | P — API toujours retirée du profil normal |
| U1, B1/B2, ancien A5 | Fixtures historiques atteignent effectivement leurs propriétés mémoire | 20 échecs et 39 erreurs reproduits avant changement ; usages explicites ajoutés, oracles de destruction et modèle inchangés ; 72 méthodes réussies sous UBSan fatal | P — pas de preuve globale |

Ciblé final O2 : 12 méthodes, 16 exécutions C et 25 programmes refusés dans
les deux stages (50 contrôles). Ciblé + modèle O0 : 13 méthodes réussies.
Modèle O0/O2 : 11 exécutions et cinq refus. Cinq mutations comportementales
détectées ; une autre crée une divergence entre check (acceptation) et compilation
(refus par un autre contrôle), sans détection mémoire à l'exécution. Les six mutations antérieures sont rejouées avec
succès. Régressions O2 : 244 méthodes natives et 76 de contrats/références,
toutes réussies. La revalidation des 72 méthodes historiques n'emploie pas
d'option d'optimisation explicite. Journaux initiaux en échec conservés dans le rapport.

## Directives et contrats du noyau

| Règle | Invariant | Vérification exécutée | Limites |
|---|---|---|---|
| G6–G7, AS7 | La directive configure le bon scope ou la bonne définition et vérifie les bornes avant conversion | Deux-points, gabarits K/M/G, débordements, héritage lexical, capacité vide, dupliquée et hors limites | P — la virgule historique reste acceptée |
| TF4–TF5, RT3, RT5 | Chaque spécialisation satisfait toutes les exigences et conserve son résultat et ses emprunts | Contrats à deux méthodes, choix de R, signatures et méthode non déclarée refusées, Future et capture jusqu'au join | P — runtime intégré, corps vérifié avec les types concrets |
| MT10 | L'exclusivité persiste jusqu'à la fin de l'appel ou la destruction du résultat, selon la forme | Les deux annotations, relais, capture async, join et LaunchFailed sous UBSan | P — périmètre des résultats directs |
| G3 | Les éléments gardent leurs adresses et leur ordre logique sur le front descendant | Oracle C des adresses, du front et du sens des tranches, y compris le relais async d'une sous-tranche | P — cas exercés dans le [rapport](cycles/CORE_ANNOTATIONS_CYCLE.md) |

## Closures réutilisables

| Règles | Invariant | Vérification exécutée | Limites |
|---|---|---|---|
| N1–N3, N6 | La création initialise les captures selon leur mode et le retour a un type commun | Copie à la création, move scalaire, refus du non-Copy sans move et des retours hétérogènes | P — scalaires et allocations de pool exercés |
| N4–N5, N7 | Une capture conserve la dépendance de l'emprunt ou la responsabilité de nettoyer l'allocation | Référence de pool conservée, destruction prématurée et sortie de portée refusées, destruction unique et slot réutilisé | P — emprunts vers des scalaires locaux hors du périmètre implémenté |
| N8 | Les appels répétés et le passage en paramètre conservent le type concret et ses captures | Appel immédiat, appels répétés, deux types spécialisés et refus d'une signature incompatible | P — voir [CLOSURES_CYCLE.md](cycles/CLOSURES_CYCLE.md) |

## Intégration du noyau après le tri des échecs

| Règles | Invariant | Vérification exécutée | Limites |
|---|---|---|---|
| N4–N6, N8, E6 | Une projection retournée par une tâche conserve sa cible et son accès | Projections constante et dynamique, attente bloquante et async, échec de lancement injecté, 13 régressions de projection | P — cas recensés dans le tri |
| N1, V1, E4, AS4 | Le type reste cohérent entre valeur et stockage, avant et après suspension | Résultat booléen et branches suspendables, refus de `i32` sur `A<i32>`, écriture contextuelle et refus du débordement | P — témoins ciblés |
| N2, N4, N7, RT3–RT7 | L'abandon exige une preuve de durabilité et le runtime récupère le résultat | Wrapper direct, attente typée, abandon sans dépendance locale, refus avec un emprunt local et nettoyage à la fermeture | P — preuve limitée aux branches concrètes scalaires, propagation publique ouverte |
| N2, N7 | Le nettoyage d'une structure transférée dans une closure est unique | Deux appels partagés, source invalidée et une seule destruction de la structure | P — [rapport de cycle](cycles/CORE_INTEGRATION_FOLLOWUP_CYCLE.md) |

### Backend Rust — attente directe et agrégats empruntés

Voir [le rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md#attente-directe-et-agrégats-empruntés-dans-le-backend-rust).
Témoins exécutés via [check_rust_task_regions.py](../validation/check_rust_task_regions.py)
avec C11, pthread et UBSan à `-O0` et `-O2`.

| Règle | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| AS4, N6 | Une Future inactive est consommée une fois. Le parent reprend le poll de l’enfant et retrouve ses temporaires et marques. | P — plusieurs niveaux, bloc, branche, boucle et `continue` exécutés ; double attente et attente dans `main` refusées. Migration entre workers non imposée. |
| AS12, AS13, N4, N5, N8 | La capture garde ses cibles et le résultat conserve uniquement les dépendances déduites du contrat. | P — agrégat à emprunt relayé, capture à deux champs et projection d’un seul, choix du receveur par branche ; cible locale et conflit mutable refusés. Agrégats possédant une ressource, `AsyncHandle` et résultats dépendants via `join()` non couverts. |
| AS14, N7 | La région de l’enfant est récupérable après transfert de son résultat. | P — quatre attentes successives avec une assertion C excluant le débordement vers une région dédiée ; le témoin de destruction avant démarrage reste vert. ASan et audit indépendant non exécutés. |

### Backend Rust — propriétaires et complétions de tâches

[Rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md#ressources-et-complétions-de-tâches-dans-le-backend-rust).
`validation/check_rust_task_regions.py` : 27 programmes à `-O0` et `-O2`
sous UBSan, 18 refus. Cinq suites voisines : 53 témoins C.

| Règle | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| N2, N4, N7, AS10, AS12, AS14 | La responsabilité des slots `A<T>` suit l’agrégat entre l’appelant, la Future et le résultat. | P — agrégat imbriqué à deux slots, pool injecté, destruction avant démarrage, transfert et réutilisation, motif `Ok(_)`, pool local trop court refusé. Propriétaires dans un autre slot ou un vecteur hors périmètre. |
| N5, N8, RT5, RT6 | `join()` libère les réservations d’exécution et conserve les emprunts du seul résultat `Ok`. | P — agrégat à emprunt mutable via un relais de handle, résultat natif à emprunt via un relais de `Result`, accès avant dernier usage refusé. |
| AS4, RT2, RT5, RT6 | `AsyncHandle.await` suspend sans perdre la complétion et consomme le handle une seule fois. | P — réveil forcé avant et après la mise en sommeil, attente indirecte par une Future, succès avec emprunt ou slot propriétaire et `LaunchFailed` injecté ; second await et lancement bloquant dans `main` refusés. Pas de migration imposée, ni ASan/TSan, ni audit indépendant. |

### Backend Rust — nettoyage composé des slots possédés

[Rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md#nettoyage-composé-des-slots-possédés).

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| N2, N4, N7, L3, L7 | Un slot adopté suit le receveur et est rendu à son pool après ses descendants. | P — struct et enum en pool, struct en vecteur, chaîne dans un même pool avec trace des restitutions, transfert par `.await`. Trois refus pour la durée de vie du pool source. C11 sous UBSan à `-O0` et `-O2`. |
| N4, N5, L4 | Le nettoyage ne suit que les champs propriétaires. | P — référence stockée et slot propriétaire dans le même élément de vecteur, cible encore accessible après nettoyage du conteneur. Crust ne propose pas de destructeurs personnalisés. |

### Post-AST Rust — provenance et résumés

[Rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md#provenance-et-résumés-du-post-ast-rust).

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| N2–N4 | Une réception imbriquée conserve la source du déplacement et les dépendances du champ possédé. | P — assertion directe du lien, du résumé réutilisé et du pool d'origine sur deux sorties de bloc. |
| N4, N6–N8 | Une jonction conserve les deux sources et le placement peut réserver un emplacement commun aux branches exclusives. | P — assertion directe des origines et de la destination, puis 84 témoins C et 54 refus dans six suites. Vérification ciblée du sous-ensemble Rust. |

Mesure de performance post-AST sur 11 programmes synthétiques. Les deux
binaires acceptent chaque cas et émettent le même C. Les médianes, le
protocole et les limites de la référence reconstituée figurent dans le
[rapport de mesure](cycles/CORE_COMPOSITION_CYCLE.md#mesure-du-coût-des-résumés).

### Post-AST Rust — plan de possession

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| G1, N2, N4, N7, L3, L7 | Le placement couvre le receveur et le parcours généré rend les slots descendants avant leur parent. | P — deux tests Rust, 70 témoins C sous UBSan et 47 refus. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#plan-de-possession-des-agrégats-dans-le-post-ast) |

### Post-AST Rust — adoption et transfert

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| N2, N4, N7, L3, L7 | La racine transférée emporte les slots adoptés, rendus des feuilles à la racine. | P — trace exacte après sortie de bloc et appel, réutilisation des slots, transfert async exercé, 60 témoins C sous UBSan et 41 refus. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#adoption-et-transfert-selon-le-plan-de-possession) |

### G1 — scalaires synchrones et destination finale

| Règle | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| G1 | La construction utilise la réservation du receveur ou de l'appelant lorsqu'elle est disponible et compatible avec le chemin. | P — cinq témoins instrumentés du curseur, 75 témoins C au total sous UBSan et 47 refus. Les promotions à plusieurs déplacements et le choix global entre scopes restent ouverts. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#placement-des-scalaires-dans-leur-destination-finale) |

### G1 — chaînes, destinations multiples et frames

| Règle | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| G1, N2, N7 | Les transferts compatibles réutilisent une adresse durable et le chemin exécuté détermine le scope de nettoyage. | P — 2 tests Rust, 95 témoins C sous UBSan et 54 refus. Cas ciblés avec chaînes, receveurs concurrents, appelant et suspension. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#g1--chaînes-de-déplacements-destinations-multiples-et-frames) |

### G9 — choix de la datastack à régions

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| G4, G6–G10 | Le post-AST borne les acquisitions simultanées, dirige les acquisitions indéterminées vers une région dédiée et respecte les limites du gabarit. | P — 5 nouveaux témoins et 100 témoins C au total sous UBSan, 54 refus. Bornes conservatrices aux jonctions et aux appels. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#g9--placement-des-régions-à-partir-du-post-ast) |

### G10 — recul groupé du curseur régional

| Règles | Propriété exercée | Preuve et limite |
| --- | --- | --- |
| G8, G10, G12 | Le nettoyage précède le recul et un slot transféré arrête le recul à sa frontière. | P — deux traces natives du curseur, contrôle de l'adresse après transfert, 102 témoins C sous UBSan et 54 refus. [Rapport](cycles/CORE_COMPOSITION_CYCLE.md#g10--recul-groupé-du-curseur-régional) |

## Chaînes bornées, binaire et temps

TX23 : bornes UTF-8, stockage inline, déplacement, vues et emprunts en pool
exercés. N4/N5/N6 : dix refus ciblés couvrent types incompatibles, accès privés,
déplacement et durée de vie des vues. Neuf programmes fonctionnels et deux
régressions passent sous UBSan sur macOS ARM64. Les témoins binaires/temporels
et de disposition inline passent sur macOS x86-64, Linux ARM64/x86-64 et Windows
x86-64 ; Windows ARM64 est compilé uniquement. L’auto-reconstruction produit un
C identique aux générations 2 et 3. Pas d’audit indépendant ni de preuve générale.
[Rapport détaillé](cycles/BINARY_TIME_BOUNDED_CYCLE.md).

## API async par défaut

Aucune nouvelle règle. Régressions ciblées des emprunts File/buffered, durée de
vie de split TCP et confidentialité/refus TLS conservées avec les nouveaux
imports. Témoins sur macOS, Linux et Windows x86-64 ; Windows ARM64 compilé
uniquement. Voir le [rapport](cycles/ASYNC_DEFAULT_API_CYCLE.md).

## Lisibilité des exemples

Aucune nouvelle règle. Quatorze programmes modifiés passent sous UBSan O1 sur
macOS ARM64 ; les 38 blocs EN/FR correspondent aux sources. Le refus de insert
sans receveur est consigné ; `_previous` résout l’exemple sans modifier le core.
[Rapport](cycles/EXAMPLE_CLEANUP_CYCLE.md).

## Contrats de verrou objet (MT11)

Corboc déduit les contrats des annotations de struct et des méthodes d’instance
publiques, les conserve lors des spécialisations/imports et refuse la réentrée
checked sur le même objet via helpers et alias. Six exécutions UBSan fatales,
dix refus et trois régressions de gardes sont consignés dans le dépôt compilateur
(`docs/OBJECT_LOCK_CYCLE.md`). Le témoin à trois threads avec un vrai verrou
s’exécute sur macOS ARM64/x86-64, Linux x86-64 et Windows x86-64 sous Wine.
Windows ARM64 est compilé seulement. Aucun verrouillage automatique ni preuve
générale de sûreté n’est revendiqué.

## Déplacement entre threads (TR1)

Cinq exécutions O1/UBSan fatal couvrent les moves ordinaires, closures locales,
transferts par défaut, ressources créées dans le worker et nettoyage avant
suspension. Quatorze refus couvrent moves directs/structurels, closures, wrappers
génériques, tableaux, champs sélectionnés, états/résultats async imbriqués et
annotations mal placées. Le runner des verrous objet reste vert (six exécutions,
dix refus). Résultats dans le dépôt compilateur :
`validation/thread-transfer-results.json` et `docs/THREAD_TRANSFER_CYCLE.md`.
L’analyse est indépendante de la cible ; les backends runtime n’ont pas changé
et n’ont pas été rejoués. Exécution Windows ARM64 toujours différée.

## API de métriques runtime

[Evidence and limits](RUNTIME_METRICS-fr.md). Eight Corbo observations plus
C/Corbo ABI concurrent-counter witnesses pass with fatal UBSan. API executes on
macOS ARM64/x86-64, Linux x86-64 and Windows x86-64; Windows ARM64 compile-only.
