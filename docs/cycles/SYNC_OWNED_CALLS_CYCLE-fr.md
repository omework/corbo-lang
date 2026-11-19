[English](SYNC_OWNED_CALLS_CYCLE.md)

# Cycle — transferts propriétaires aux auxiliaires synchrones

## Portée et règles

Suite de [SYNC_BYTE_BORROW_CALLS_CYCLE.md](SYNC_BYTE_BORROW_CALLS_CYCLE.md).
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept brouillons ont été
reconsultés, ainsi que T1–T11, ARGUMENTS.md, AS7–AS9 et le brouillon 01.
Aucune règle normative n’est modifiée. Ce lot raccorde B4/B4a/B4c, T1/T6/T9/T11,
U1/L6, AS2/AS8/AS9/AS12 et RT8 : appels synchrones depuis les états async ou
les blocs natifs, avec paramètres et résultats propriétaires Int, String,
Vector<Int> et Vector<u8>.

`->` reste obligatoire pour l’argument propriétaire. La préparation invalide
immédiatement l’ancien accès et sauvegarde le pointeur Cell dans l’état.
Les arguments suivants peuvent suspendre, mais ne peuvent réutiliser cet accès
ni invalider un prêt préparé. Le callee reçoit le pointeur, sans déplacement
ni copie de l’allocation. Ses paramètres gardent leur mutabilité déclarée.

Le résultat est reçu, transmis avec une flèche ou détruit par `drop(-> call())`.
L’appel isolé, `_` et une liaison sans usage sont refusés. La réception admet
l’annotation A<T> correspondante ; Int et A<Int> ne sont pas confondus.
Un résultat peut remplacer un receveur après évaluation complète, être passé
à un autre auxiliaire ou capturé directement par une tâche enfant.

## Implémentation et nettoyage

La génération synchrone utilise des allocations et des sources symboliques
extérieures au scope d’adaptation. Le C reçoit des Cell * réels. Le scope
extérieur n’est pas nettoyé par cette adaptation : ses pools appartiennent
au contexte appelant. L’allocation retournée est explicitement exportée avant
le nettoyage du scope d’adaptation ; les autres allocations suivent les
nettoyages du corps synchrone vérifié.

Les transferts préparés sont inscrits dans le mécanisme existant de nettoyage
d’arguments. Un return pendant un argument ultérieur détruit ces allocations
une fois, puis nettoie les scopes quittés, sans appeler le callee. Deux transferts
préparés sont nettoyés dans leur ordre inverse de réception. Un break interne
à une boucle de calcul d’argument ne nettoie pas les arguments de l’appel
extérieur qui continue. Les cas de boucle généraux restent soumis au suivi
existant ; ce cycle ne prétend pas les épuiser.

Le contrat des résultats async compose les candidats propriétaires des
résumés synchrones. Une restitution de paramètre conserve son origine ;
plusieurs candidats conservent l’union. Un helper qui rend seulement a après
avoir consommé b permet au pool de b de finir après join, avant l’usage du
résultat a. Le handle en cours conserve néanmoins les deux captures et ne
peut sortir du scope du pool de b. Les fabriques synchrones de tâches conservent
cette distinction. L’analyse utilise des résumés ; une inférence cyclique ou
un candidat non direct garde l’approximation conservative existante.

## Défauts et précisions trouvés

Le premier raccordement de source symbolique ne l’inscrivait pas parmi les
sources extérieures connues du vérificateur : il était refusé par l’invariant
interne de durée de vie. L’inscription est corrigée sans émettre de fermeture
de ce pool extérieur.

Le programme valide qui crée `let vue = &allocation` dans un état, lit via
un helper, puis transfère après le dernier usage, restait refusé comme une
expression ref non supportée. Les places Int et mutables u8 peuvent maintenant
produire cette liaison. Les contrôles existants de type, mutabilité, capacité
et dernière utilisation sont réutilisés ; les cas avec usage futur restent
refusés. Les références imbriquées ne sont pas aplaties.

Les fixtures initiales employaient `*a = n` pour un accès propriétaire alloué,
alors que l’écriture retenue est `a = n`. Le helper inutilisé était donc refusé
avant les cas exercés. Elles ont été corrigées. Une sonde utilisait aussi
`match <-h.join()` ; les scénarios exécutés utilisent le match de join déjà
implémenté. La sonde exploratoire `copy(a)` sur une allocation Int est refusée
par le chemin tableau ; elle n’est pas comptée comme obligation de copie de
structure ST18 ni comme preuve de duplication d’allocation dans ce cycle.

## Vérification

`tests/test_sync_owned_calls.py` comprend treize méthodes, vingt-deux exécutions
Crust/C et vingt refus attendus par passage complet, plus une vérification
sans génération C. Les oracles sont les sorties écrites indépendamment du
compilateur, les traces de destruction, l’égalité des adresses avant/après
restitution et le réemploi effectif de pools de capacité un ou deux.

Les scénarios croisent : transferts explicites, dernier usage d’emprunt nommé,
arguments imbriqués, yield/await pendant préparation, return anticipé, boucle
interne, plusieurs arguments propriétaires, résultat conditionnel et pools
réels distincts, fabrique synchrone, enfant async, join, échec de lancement,
remplacement de receveur, annotations de type et nettoyage de collections.
Les contrats synchrones existants et les scénarios natifs/runtime pertinents
sont réexécutés. Aucun nouveau générateur aléatoire ni modèle général de
concurrence n’est revendiqué ; les modèles de provenance des tests de contrats
existants restent inclus dans cette sélection.

Clang C11, pthread, O0/O2, `-Wall -Wextra -Werror -Wno-unused-function`,
`-fsanitize=undefined -fno-sanitize-recover=all`. Les diagnostics UBSan échouent
les tests. Pas de nouvelle validation ASan/TSan ni de second compilateur ; les
blocages ASan antérieurs ne sont pas des succès. Pas de preuve formelle.

## Mutations

La campagne commence par une baseline verte et travaille dans des copies
temporaires, avec les mêmes tests. Les fautes portent sur l’invalidation de
l’ancien nom, l’inscription des arguments préparés au nettoyage, l’ordre de
leur nettoyage, l’export du résultat hors de l’adaptation, la provenance du
résultat async et le rejet d’un résultat propriétaire ignoré.

La première campagne contenait aussi l’omission de la remise à NULL du champ
déplacé. Elle a survécu. Sur les chemins exécutés, `consumed` exclut déjà ce
champ du nettoyage terminal, et `cleanup_path` sélectionne ce nettoyage plutôt
que celui d’une instance inactive. Le champ obsolète n’est donc plus lu. La
classification finale est « sans effet comportemental sur les chemins choisis »,
pas « faute détectée » ni preuve générale d’équivalence. Le test supplémentaire
supprimant l’invalidation du nom contrôle la véritable possibilité de réutiliser
l’ancien accès. Le journal de la survie initiale est conservé.

Les ancres des mutations des cycles précédents ont été ajustées à l’insertion
du cas propriétaire dans la génération, sans changer les fautes ni les oracles.
Leur adaptation syntaxique n’est pas revendiquée comme une réexécution de ces
campagnes anciennes.

## Artefacts et limites

`validation/sync-owned-identity.crust` et son C conservent un aller-retour réel
par helper synchrone, état async et join. L’adresse initiale est celle du résultat
et du slot réemployé ; a=7 puis b=9 sont détruits une fois. Le C conserve une ABI
Cell * → Cell *, sans objet intermédiaire. Les arguments sont préparés avant
l’appel C : l’ordre d’évaluation C n’est pas utilisé pour ordonner les effets.

Restent à raccorder les signatures générales d’agrégats, les pools injectés aux
helpers depuis les états, la création locale de pools dans ces états et d’autres
familles d’expressions et de résultats. Les provenances non directes restent
conservatrices ; ce lot n’affirme pas que toute fabrique ou toute signature
propriétaire est couverte. Les obligations encore ouvertes des sept brouillons,
notamment runtime/scheduler/Select/mutex et placement général, restent actives.

## Résultats exécutés

| Campagne | Résultat | Journal dans validation/ |
| --- | --- | --- |
| Lot propriétaire O0 | 13 méthodes, 9,336 s, OK | `sync-owned-final-o0.log` |
| Régression native et runtime O2 | 134 méthodes, 153,121 s, OK | `sync-owned-regression-o2.log` |
| Contrats synchrones O2 | 130 méthodes, 66,683 s, OK | `sync-owned-contracts-o2.log` |
| Complément de durée de vie O0, après ajout de deux refus | Une méthode, 0,620 s, OK | `sync-owned-final-lifetimes-o0.log` |
| Campagne finale de mutations O2 | Baseline actuelle 13 méthodes verte, six fautes détectées ; une sans effet observé sur les chemins choisis | `sync-owned-final-mutations-o2.log` |
| Artefact C O2 | Adresse conservée, slot réemployé, deux destructions uniques | `sync-owned-artifact-run.log` |

Les treize méthodes de la baseline finale incluent les deux refus ajoutés
après le lancement de la grande régression : handle sortant du pool d’une
capture encore active, et emprunt retourné depuis une entrée transférée.
Les journaux initiaux avec erreurs de fixture et mutation survivante sont
conservés. Le succès des campagnes porte sur ces scénarios et configurations ;
il ne clôt ni la preuve de sûreté ni l’intégration des sept brouillons.

Suite : [appels booléens et sorties primitives de blocs](SYNC_BOOL_CALLS_CYCLE.md).
