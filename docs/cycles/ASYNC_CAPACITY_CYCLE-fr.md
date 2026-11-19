[English](ASYNC_CAPACITY_CYCLE.md)

# Cycle AS7 — Dimensionnement des pools d’états async

## Périmètre et décisions

Application de AS7 et du brouillon 04 ; aucune nouvelle règle normative.
La capacité C par défaut de 16 ne dimensionne plus les programmes Crust.
`#(directive, async_pool_sizes={nom:capacité, ...})` configure les pools au
niveau du programme. Les capacités doivent être des Int32 strictement positifs ;
les doublons, noms inconnus et directives imbriquées sont refusés. Le parseur
accepte les noms qualifiés dans la directive, mais les déclarations de namespaces
restent à implémenter. Un nom inconnu qualifié reçoit le diagnostic correspondant.

Les spécialisations d’une même fonction async générique possèdent des pools
séparés ; la capacité indiquée pour son nom source s’applique à chacun.
Les capacités explicites restent des limites physiques : une limite insuffisante
provoque l’arrêt contrôlé existant, sans réemploi d’un slot vivant ni agrandissement
silencieux. Le diagnostic de création cyclique liste tous les pools encore non
bornés, y compris les descendants dépendant du cycle.

## Calcul et hypothèses

`async_capacity.py` extrait les créations entre fonctions async. Le vérificateur
synchrone relève les identités des emplacements de tâches/handles rencontrés dans
chaque corps et au niveau du script. Ce relevé est monotone : restaurer un état
pour analyser une autre branche ne supprime pas les emplacements de la première.
Il inclut les résultats opaques des appels, les paramètres symboliques et les
alias ; il surestime donc le stockage nécessaire.

Le backend relève les temporaires qui peuvent détenir une tâche ou un handle dans
chaque état async. Pour un graphe acyclique, la borne d’un type additionne les
emplacements synchrones et, pour chaque type parent qui peut le créer, la borne
du parent multipliée par son nombre de temporaires de tâches. Une capacité
explicite coupe la dépendance correspondante et permet de borner les descendants.
Un pool inutilisé reçoit au moins un slot pour produire un tableau C valide.
Une borne calculée dépassant Int32 est refusée avec demande de capacité explicite.

Argument de conservation, **pas une preuve formelle** : chaque instance vivante
du sous-ensemble actuel possède un emplacement propriétaire dans le code
synchrone ou dans un état parent vivant. Compter tous ces emplacements, même
incompatibles entre chemins ou alias du même état, majore le nombre d’instances.
Le parent récursif reste compté tant qu’il attend son enfant. La borne suit les
instances vivantes, pas seulement le nombre de threads actifs.

Prémisses à réexaminer lors des prochaines extensions : les fonctions synchrones
sont non récursives ; elles ne sont pas invoquées arbitrairement par le backend
async ; les états async n’acceptent pas actuellement des captures/résultats de
tâches ni des collections dynamiques de handles. Les boucles réutilisent un
nombre fini d’emplacements. Select, runtime::thread et de nouvelles formes de
stockage de tâches doivent enrichir cette analyse avant d’être admis.

Le crochet C `CRUST_TASK_POOL_CAPACITY` reste disponible pour les oracles qui
invoquent directement les fabriques C hors du programme vérifié. Ce n’est ni une
capacité implicite du langage, ni une preuve portant sur du C arbitraire.

## Contre-exemples et interactions

- Dix-neuf tâches retournées par une fabrique synchrone et conservées ensemble :
  dépassement de l’ancien défaut de 16, désormais admis et exécuté.
- Dix-neuf tâches dans une branche terminée par `return` : collecter uniquement
  l’état final du vérificateur oublierait cette branche. Le relevé monotone la
  conserve. Une mutation rétablissant l’oubli est détectée.
- Récursion directe de profondeur quatre : capacité quatre admise, capacité trois
  épuisée avec `task pool capacity exceeded`. Le parent n’est pas libéré avant
  le retour de l’enfant.
- Récursion mutuelle et cycle indépendant : tous les noms manquants figurent dans
  le diagnostic ; une capacité explicite sur un membre du cycle borne l’autre.
- Modèle indépendant : 1 ou 3 parents conservent chacun 1 ou 3 enfants inactifs.
  Le pic attendu est le produit, calculé sans consulter le vérificateur. Le pilote
  C fait avancer tous les parents jusqu’au yield avant d’en terminer un, puis
  vérifie que tous les pools sont vides. Quatre configurations exécutées.
- Retours de handles par contrat, transfert d’une allocation vers parent puis
  enfant, attente, nettoyage unique de la capture et réemploi de son adresse.
  Utiliser la valeur transférée reste refusé.
- Deux spécialisations de type feature, deux pools de données, captures partagées,
  attente des handles et reprise de mutation après l’attente. Une mutation avant
  l’attente reste refusée.
- Boucle avec continue et break : les tâches sont nettoyées à chaque itération.

## Exécutions

Clang Homebrew 20.1.3, arm64 macOS ; C11, UBSan avec
`-fsanitize=undefined -fno-sanitize-recover=all`. Les oracles C utilisent aussi
`-Wall -Wextra -Werror -Wno-unused-function -pthread`.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| 9 méthodes ciblées à O0 | Réussies, 10,623 s | validation/async-capacity-final-O0.log |
| 9 méthodes ciblées à O2 | Réussies, 10,898 s | validation/async-capacity-final-O2.log |
| 7 premières méthodes + obligations de handles + features async | 19 réussies, 17,289 s | validation/async-capacity-O2-regression.log |
| Deux interactions ajoutées ensuite | Réussies, 1,368 s, puis incluses aux deux exécutions finales | validation/async-capacity-interactions.log |
| Deux oracles C de registre et de réemploi concurrent | Réussis, 1,578 s | validation/async-capacity-C-boundary.log |
| Quatre mutations | Toutes détectées | validation/async-capacity-mutations.log |
| Borne inférée au-delà de Int32 et coupure par capacité explicite | Une méthode réussie, 0,011 s | validation/async-capacity-overflow.log |
| Retour d’emprunt récursif après capacité explicite | Diagnostic de provenance conservé, méthode réussie, 0,565 s | validation/async-capacity-relay-final.log |

Les neuf méthodes ciblées exécutent 13 binaires par niveau : 12 réussites et un
épuisement contrôlé attendu. Elles vérifient 11 programmes refusés. Le test supplémentaire de dépassement
de borne ajoute un refus et une compilation admise, sans exécution du C géant. Les quatre
mutations remplacent la borne par un plafond de 16, oublient les enfants,
oublient l’historique des branches, ou agrandissent une capacité explicite.
La dernière est détectée par le comportement natif d’épuisement ; les trois
premières par les assertions de borne issues des scénarios indépendants.

Le test historique de retour d’emprunt récursif attendait le diagnostic de
provenance avant toute vérification de capacité. AS7 donne désormais priorité à
la capacité manquante. Ce test fournit maintenant `relay:4` pour continuer à
éprouver la restriction de provenance ; aucune acceptation n’a été assouplie.

La première exécution a révélé des erreurs dans le nouveau pilote de test :
noms d’états ABI incorrects, méthode de libération inexistante et mauvais nom
pour l’argument de diagnostic attendu. Elles ont été corrigées en lisant l’ABI,
sans changer la sémantique testée. Le journal initial est conservé. L’importation
de classes de tests dans ce module lançait aussi les suites runtime/features ;
elles ont été remplacées par des imports de modules.

Régression large du journal initial : 304 méthodes en 521,670 s, avec cinq
échecs d’assertion et une erreur (dont quatre échecs de sous-cas du pilote ABI
initial). Parmi les suites préexistantes : **274/275 méthodes async et 22/22
méthodes type features réussies**. La seule méthode async restante est celle du
diagnostic de provenance, adaptée et réexécutée avec succès ci-dessus. Les
nouveaux cas défaillants ont tous passé dans les exécutions ciblées finales.
Il n’y a pas eu de seconde exécution monolithique des 304 méthodes.

Une régression synchrone supplémentaire a exécuté 243 méthodes en 128,684 s :
239 réussies, quatre méthodes avec 14 erreurs de sous-cas, toutes dues à des
allocations propriétaires sans usage explicite (U1), dans `test_conditionals`.
Le journal est `validation/async-capacity-sync-regression.log`. Ces quatre
programmes ont reçu une lecture explicite de `data`, `inner` ou `fresh`, avec
assertions sur les sorties mises à jour. Les assertions de destruction et leur
ordre sont conservés : on n’a pas remplacé un nettoyage de scope/reset par un
drop anticipé. Les 28 méthodes de `test_conditionals` ont ensuite réussi en
55,242 s avec UBSan fatal (`CRUST_SANITIZE=undefined`), au niveau d’optimisation
par défaut de Clang ; trace `validation/async-capacity-conditionals-migrated.log`.
Le premier lot synchrone utilisait les flags historiques stricts de ses helpers,
sans imposer globalement un sanitizer ; il ne constitue pas une exécution UBSan
globale. Les tests reset restent dans le profil de compatibilité explicite.

La validation finale agrège ces exécutions et les reprises ciblées : elle ne
prétend pas qu’une suite globale unique a été relancée après les migrations.

## Limites restantes

La borne n’est pas minimale : branches exclusives, appels séquentiels, fonctions
inutilisées et alias peuvent la gonfler. La limite explicite est alors utilisable.
La récursion est éprouvée ici pour les résultats scalaires ; les résultats
empruntés récursifs ne sont pas couverts. L’épuisement arrête le processus :
il ne constitue pas une preuve de nettoyage de toutes les autres tâches.
Les namespaces, Select, les captures de structures utilisateur, le scheduler
public, les types publics runtime::Handle/runtime::Error et les mutex restent
ouverts. Cette validation ne démontre ni la sûreté générale du langage ni
l’achèvement des sept brouillons.
