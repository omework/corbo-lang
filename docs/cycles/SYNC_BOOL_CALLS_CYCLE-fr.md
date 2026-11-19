[English](SYNC_BOOL_CALLS_CYCLE.md)

# Cycle — booléens à la frontière des appels synchrones

Suivi : le manque concernant les pools injectés décrit dans ce rapport
est traité pour Int/String/Vector<Int/u8> dans le
[cycle suivant](ASYNC_POOL_INJECTION_CYCLE.md). Les autres limites demeurent.

## Règles et portée

Suite de [SYNC_OWNED_CALLS_CYCLE.md](SYNC_OWNED_CALLS_CYCLE.md).
AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept brouillons, B4/B4a,
les règles de scopes, A1–A6 et AS2/AS8–AS16/MT1–MT8 ont été reconsultés.
Aucune décision normative n’est modifiée. Les obligations des sept brouillons
restent ouvertes au-delà de ce lot.

Le raccordement des pools révèle la nécessité de distinguer leur réservation
exclusive pendant une tâche et la dépendance de stockage d’un résultat après
son attente. Le premier mécanisme n’est pas encore raccordé aux états. Avant
cette extension, ce cycle corrige une famille de signatures manquante à la
même frontière : les paramètres et résultats booléens des fonctions synchrones.

Le frontend synchrone existant écrit ces signatures `bool` et les états async
utilisent `Bool`. Ce cycle adapte leurs représentations internes ; il ne change
pas la syntaxe et n’introduit pas d’alias public. Un booléen n’est pas un Int ou
un u8, malgré sa représentation C entière. La sélection des contrats doit
conserver cette distinction jusqu’au résultat et aux captures d’un bloc natif.

## Contre-exemples et corrections

`fn flag(b:bool)->bool{return b;}` appelé depuis un `async fn work()->Bool`
était refusé, notamment par « une valeur Bool est requise » sur un retour
direct. Les appels fournissent maintenant un résultat typé Bool dans les
états et acceptent les arguments booléens sans conversion implicite.
Les liaisons, annotations existantes, réaffectations, conditions, retours,
captures enfant et retours de blocs natifs utilisent cette même adaptation.

Un deuxième contre-exemple vient du test de durée de vie : un bloc synchrone
avec pool local, join, copie booléenne puis sortie rendait cette copie par sa
dernière expression. Il était refusé comme transfert sans flèche, bien qu’il ne
transfère aucune allocation. Les résultats primitifs Int/bool/u8/char de ces
blocs sont maintenant copiés avant le nettoyage. Les propriétaires continuent
d’exiger une flèche et les références gardent leurs vérifications de durée.

Les copies booléennes ne retiennent aucun pool ni emprunt après join. Un prêt
lu par un premier sous-appel peut finir avant le transfert suivant, tandis
qu’un argument mutable préparé reste exclusif pendant les autres arguments.
Un return dans un argument booléen ultérieur nettoie le propriétaire déjà
préparé ; la fonction non appelée ne produit aucun effet.

## Vérification

`tests/test_sync_bool_calls.py` contient dix méthodes : 18 programmes C
exécutés, 16 programmes invalides refusés, plus une vérification sans émission
de bridge. Huit des exécutions comparent la table de vérité de deux booléens
au modèle Python indépendant `left and right`, en async et bloc natif.
Les autres oracles fixent valeurs, ordre d’effets et traces de destruction.

La régression runtime/native ajoute ce module à sa sélection existante.
`tests/run_sync_bool_regression.py` réexécute les cinq modules de contrats
et 119 méthodes de fondations ciblant blocs, conditions, retours, booléens,
scalaires et courts-circuits. Les modèles de provenance existants de ces
modules restent inclus. Ce n’est ni la suite entière du projet ni une preuve
générale sur les combinaisons du langage.

Clang C11, pthread, O0/O2, `-Wall -Wextra -Werror -Wno-unused-function`, UBSan
avec `-fno-sanitize-recover=all`. Aucun nouveau résultat ASan, TSan, second
compilateur C, fuzzing ou preuve formelle n’est revendiqué.

## Mutations et limites de leurs oracles

Les campagnes utilisent des copies temporaires du compilateur et les mêmes
tests, après baseline verte. Quatre fautes sont détectées : acceptation d’un
Int comme argument booléen, inversion du résultat booléen, perte du type dans
l’inférence du bloc natif, refus d’un résultat primitif de bloc valide.

La première tentative de suppression du snapshot laissait sa déclaration C
inutilisée : Clang rejetait le C avec `-Werror`. Ce n’était pas une observation
de lecture après libération. La mutation corrigée retire aussi la déclaration
et survit. Le C inspecté montre que les expressions des chemins choisis avaient
déjà produit `read`/`selected` ou une variable scalaire encore en portée C.
La classification finale est « sans effet comportemental sur les chemins
choisis », pas « détectée », ni preuve d’équivalence générale. Les journaux
initiaux restent conservés ; la campagne finale ajoute une mutation distincte
qui réintroduit le véritable refus injustifié de la sortie de bloc.

## Artefact et suite

[Programme conservé](../../validation/sync-bool-boundaries.crb) et
[C généré](../../validation/sync-bool-boundaries.c) : lecture via auxiliaire booléen,
suspension, join, drop de 7, réemploi du slot avec 9, fermeture du pool puis
lecture du résultat indépendant. Sortie `9`, `1` ; destructions de 7 et de 9
exactement une fois. La copie `block_value` précède `source_close` dans le C.

[Pool injecté encore ouvert](../../validation/open-async-pool-helper.crb) conserve
le cas valide au regard d’A1/A2/A4/AS12/AS13 qui reste refusé par la limitation
des captures. Ce n’est pas un test exigeant de maintenir ce refus. Il faut
suivre le prêt exclusif jusqu’à la fin de la tâche, puis seulement la source
du résultat, à travers les contrats et la traduction `Source *`. Les pools
locaux d’états, les signatures générales, runtime/scheduler/Select/mutex et
le placement général restent à compléter. Le but global reste actif.

## Résultats exécutés

| Campagne | Résultat | Journal dans validation/ |
| --- | --- | --- |
| Premier lot O0 | Huit méthodes, sept vertes ; sortie de bloc booléenne refusée à tort | `sync-bool-initial-o0.log` |
| Sortie de bloc corrigée O0 | Huit méthodes vertes, 5,573 s | `sync-bool-block-o0.log` |
| Lot ciblé final O0 | Dix méthodes vertes, 5,902 s | `sync-bool-final-o0.log` |
| Native/runtime O2 | 144 méthodes vertes, 132,205 s | `sync-bool-regression-o2.log` |
| Contrats et scopes O2 | 249 méthodes : 248 vertes, une fixture non conforme à U1 | `sync-bool-contracts-scopes-o2.log` |
| Reproduction sur le compilateur antérieur | Même refus de la fixture pour résultat inutilisé | `sync-bool-baseline-fixture.log` |
| Fixture corrigée O2 | Une méthode verte, cas accepté et deux refus | `sync-bool-fixture-fixed-o2.log` |
| Mutations finales O2 | Baseline dix méthodes verte, 11,079 s ; quatre fautes détectées, une omission sans effet observé | `sync-bool-reviewed-mutations-o2.log` |
| Artefact C O2 | Valeurs 9 et 1 ; deux destructions uniques ; exit 0 | `sync-bool-artifact-run.log` |
| Pool injecté | Refus de capture encore ouvert | `sync-bool-open-pool-probe.log` |

La fixture `test_match_expression_early_return_has_function_result_type`
créait `scratch` sans usage explicite. Le compilateur antérieur au cycle,
reconstitué en copie temporaire, la refusait déjà. La correction ajoute
`print(scratch)` et adapte la sortie attendue ; le nettoyage reste automatique
au return, et son oracle de destruction unique est conservé. La version sans
usage est désormais vérifiée comme refus U1. La sélection de 249 n’a pas été
réexécutée intégralement après cette seule correction de fixture : son échec
initial demeure visible, et la méthode corrigée est réexécutée séparément.

Le compilateur du cycle n’a pas été modifié depuis le lancement des sélections
O2. Tous les processus mentionnés ci-dessus sont terminés. Ces résultats
clôturent ce lot, pas le travail d’intégration des règles restantes.
