[English](NESTED_PLAIN_RESULTS_CYCLE.md)

# Cycle RT5/RT6 — Retours async et résultats imbriqués sans emprunt

## Portée normative

Application des règles déjà retenues, sans modification normative : AS4
(tâche inactive attendue donnant T), RT5/RT6 (handle attendu donnant
Result<T,runtime::Error>, erreur de lancement distincte du résultat interne),
U1 (usage explicite), règles de capture, de drop et de réemploi des pools.
AGENTS.md, les guidelines et l’index design-buffer ont été relus ; ce cycle
prolonge les cycles précédents dont la lecture normative complète est déjà
consignée. L’objectif des sept brouillons reste ouvert.

Les six charges Int, Bool, u8, char, (), runtime::Error étaient déjà utilisables
comme résultats de join dans les contrats synchrones et les captures async.
Leur retour depuis une fonction async était refusé, même lorsque la fonction
renvoyait simplement le résultat d’une attente. Le contre-exemple
validation/open-async-plain-result-return.crust s’exécute maintenant ; son
ancien log de refus est conservé comme preuve historique.

## Implémentation et invariants examinés

Les types imbriqués sont enregistrés structurellement lors de l’analyse des
signatures, ainsi que l’enveloppe ajoutée par le join de chaque définition
async. Il n’y a pas de limite artificielle fixée à deux niveaux. Les tables
partagées conservent les faits de type canoniques, pas des informations de
programme. Le C ne déclare que les niveaux nécessaires au programme courant.
Un test compile le même programme avant et après un programme plus profond
et exige un C identique. Une signature profonde sans tâche exécutée est testée.

Le premier niveau utilise le type C existant ; chaque niveau supplémentaire
contient son propre statut et une valeur du niveau précédent. L’attente
synchrone copie la charge directement dans ce champ et reçoit séparément le
statut extérieur. L’attente async utilise un temporaire de statut distinct,
conservé dans l’état ; aucune conversion de pointeur entre structures de tailles
différentes n’est introduite. Le résultat temporaire est initialisé avant le
point de reprise, pas à chaque poll. Le match extrait seulement le niveau
courant. L’erreur interne ne devient donc ni succès ni erreur extérieure.

Les contrats et analyses d’effets/provenances gardent le type complet. La
représentation s’applique aussi aux captures, copies, retours directs d’attente,
if, loop, match, annotations, réaffectations et drop de ces valeurs. Un résultat
simple ne contient aucune dépendance vers les allocations utilisées pour le
calculer : après l’attente, sa lecture peut suivre le drop de ces allocations.
Les résultats propriétaires ou empruntés restent dans leurs chemins existants.

## Modèle et contre-exemples

Le générateur de tests construit des chaînes de joins. Son oracle n’utilise
ni les tables du compilateur ni le C : chaque lancement réussi ajoute une
couche de succès ; refuser un lancement empêche l’exécution de son enfant et
place l’erreur exactement à ce niveau. Six valeurs terminales sont suivies à
profondeur 2 et 4, en observation synchrone et après capture/suspension async
(24 configurations). Huit configurations refusent un des quatre niveaux de
lancement, avec les deux mêmes modes d’observation. Un programme de profondeur
7 vérifie que le support n’est pas limité aux exemples à deux couches.

Le test de nettoyage transfère une allocation à travers parent/enfant : succès
et refus de lancement doivent détruire la capture une fois puis permettre de
réutiliser la même adresse. Un autre programme conserve une capture mutable
jusqu’au join, détruit ensuite sa cible, puis lit le résultat simple. Les
variantes avec lecture, drop ou reset historique avant attente sont refusées.
`reset()` reste retiré du prototype ; ce dernier contrôle utilise explicitement
allow_legacy_reset=True.

Les voisins invalides changent profondeur ou charge, substituent un entier ou
une erreur à un Result, réutilisent une liaison après drop, ou ignorent un
résultat faillible. Les trois diagnostics d’usage sont contrôlés explicitement.
Ce sont 23 refus attendus et 52 exécutions natives dans le module final de
11 méthodes, par niveau d’optimisation. Ce décompte ne comprend pas les suites
de régression ni les campagnes de mutation.

## Exécutions terminées

Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, UBSan fatal
(-fsanitize=undefined -fno-sanitize-recover=all). Les oracles de runtime ajoutent
-Wall -Wextra -Werror. Les anciens helpers contraintes/effets utilisent leur
optimisation par défaut et activent UBSan via CRUST_SANITIZE ; il ne faut pas
leur attribuer O2 sur la seule base de CRUST_TEST_OPT.

| Vérification | Résultat terminal | Trace |
| --- | --- | --- |
| Nouveau module final O0 | 11 méthodes réussies, 30,583 s | validation/nested-plain-O0-final.log |
| Nouveau module final O2 | 11 méthodes réussies, 32,593 s | validation/nested-plain-O2-final.log |
| Premières 10 méthodes nouvelles, runtime::Error, contraintes et effets | 67 méthodes réussies, 50,626 s | validation/nested-plain-O2-regression.log |
| Retours directs d’attentes, nommées/calculées/conditionnelles | 1 méthode, 8 exécutions réussies | validation/nested-plain-direct-returns.log |
| Résultats simples, spawn_blocking, obligations, capacités, features async | 39 méthodes réussies, 48,193 s | validation/nested-plain-runtime-regression.log |
| Résultats Bool/tableaux, attentes calculées, emprunts, ABI et pools existants | 15 méthodes réussies, 29,331 s | validation/nested-plain-typed-regression.log |
| Diagnostics précis des trois résultats ignorés | 1 méthode réussie | validation/nested-plain-use-diagnostics.log |
| Mutations finales | 5 détectées | validation/nested-plain-mutations-final.log |

La régression de 67 méthodes précède l’ajout des retours directs de handles ;
les deux exécutions complètes finales et les 39 méthodes runtime les suivent.
Le premier log nested-plain-O0.log chargeait aussi involontairement les 11 tests
du module importé ; l’import a été corrigé et les décomptes finaux ci-dessus
concernent uniquement le nouveau module. Aucun résultat n’a été affaibli.
La compilation Python des modules modifiés et des nouveaux tests a réussi.

Les mutations, appliquées à des copies temporaires, effacent respectivement
le statut extérieur synchrone, le statut extérieur async, le statut intérieur,
le contrôle de type du retour et l’obligation d’utiliser le résultat extrait.
Les cinq produisent des échecs d’assertions des tests attendus. Aucune n’est
comptée comme détectée sur la seule base d’une erreur de syntaxe ou de build.
La campagne cible ces cinq fautes ; elle ne mesure pas une couverture globale.

## Limites et travail restant

La construction C actuelle concerne les enveloppes runtime::Error répétées
sur les six charges indiquées. Elle ne rend pas génériques tous les Result<T,E>,
les signatures de charges propriétaires/empruntées ou les conteneurs de résultats.
Un écart voisin était reproduit dans
validation/open-async-business-result-envelope.crust et son log : le résultat
existant Result<u8,IntegerConversionError> peut sortir d’une tâche, mais une
fonction async déclarant l’enveloppe de son join n’est pas encore acceptée.
Ce programme était un cas valide restant à implémenter, pas un test négatif de
sémantique. Cet écart est corrigé dans
[BUSINESS_RESULT_ENVELOPES_CYCLE.md](BUSINESS_RESULT_ENVELOPES_CYCLE.md), sans
arbitrage normatif supplémentaire.

L’API runtime::Handle<T>, l’installation publique du scheduler, réveils et équité,
runtime::thread, Select, mutex et les autres écarts déjà consignés restent
ouverts. Ce cycle ne les prétend pas couverts. Il n’y a ni preuve formelle,
ni TSan, ni campagne ASan, ni exécution de toute la suite monolithique.

Commandes reproductibles :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_nested_plain_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_nested_plain_results -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts test_spawn_blocking test_handle_obligations test_async_capacity test_async_type_features -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_nested_plain_mutations.py
```
