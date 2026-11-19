[English](ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md)

# Cycle — captures de structures contenant des références

Les écarts concernant les réemprunts directs et leur retour async sont depuis
traités dans [ASYNC_FIELD_REBORROWS_CYCLE.md](ASYNC_FIELD_REBORROWS_CYCLE.md)
et [ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
Les limites indiquées dans ce rapport restent les observations de son cycle.

Suite du [cycle des structures à champs Int](ASYNC_STRUCT_CAPTURES_CYCLE.md).
Aucune modification normative. Règles concernées : ST5/ST7/ST9/ST11,
B1/B2/B4/B4a, AS2/AS8–AS15, MT1–MT4/MT8 et RT8 ; PR1 pour la séparation
du reset historique. Les obligations restantes des sept brouillons restent ouvertes.

## Implémentation

Une tâche peut capturer `&View` ou `&mut View` lorsque le layout de View contient
des champs Int, &Int et &mut Int. Les pointeurs existants sont conservés.
Le suivi retient le porteur et, transitivement, ses cibles et leurs sources.
Une lecture `*view.data` charge le pointeur du champ puis son contenu Int.
Les offsets mixtes prennent en compte la taille des pointeurs ; une écriture
Int ne peut pas écraser un champ référence.

Les auxiliaires et méthodes synchrones reçoivent des entrées symboliques dont
les dépendances correspondent aux champs réels. Leurs prêts et mutations des
Int ciblés restent vérifiés par le backend synchrone. Les instantanés des
pointeurs de champs sont établis à l'entrée du bridge. Les appels dont le
contrat modifie les dépendances d'une structure restent explicitement non
raccordés : les accepter sans propagation des effets ne serait pas correct.

Les captures sont relayées entre tâches et dans les blocs de threads natifs.
Le résultat Int ne conserve pas artificiellement l'emprunt après attente.
Une tâche inactive détruite ou un lancement refusé libère ses réservations,
sans détruire les allocations seulement empruntées. Le runtime C est inchangé.

Le [cas historique](../../validation/open-async-struct-reference-field.crb) affiche
désormais 7 ; son [C généré](../../validation/async-struct-reference-field-basic.c)
est conservé. Les patchs de ce cycle sont dans `validation/async-struct-reference-fields-*.patch`.

## Contre-exemples et corrections

Le premier passage a révélé que le reset historique ne regardait que les
cibles directement capturées : tâche → View masquait le second lien View → Int.
Il pouvait donc détruire cet Int avant l'attente. Le contrôle parcourt désormais
les dépendances transitives. Le test impose le refus dans `verify_program` et
`compile_source`. Après attente et dernier usage, le reset reste admis dans le
profil historique seulement. PR1 n'est pas modifiée.

Les premiers essais ont aussi exposé une limitation antérieure : `target.set(n)`
ne prend pas encore une expression générale dans le chemin synchrone. Le test
du bridge utilise `*target = n`, dont la sémantique de mutation est déjà établie.
Le [cas set non raccordé](../../validation/open-sync-set-expression.crb) et son
[diagnostic](../../validation/open-sync-set-expression.log) restent consignés.
Un essai de constructeur imbriqué utilisait des noms pointés non reconnus par
la grammaire. Il ne constituait pas une preuve de support de la construction
imbriquée ; le test de layout utilise plusieurs champs références explicitement
déclarés, séparés par des Int, et conserve son oracle d'offsets mixtes.

Les tests historiques reset/champs références avaient également dérivé de U1 :
ils créaient des allocations sans usage explicite. Avant modification des
fixtures, les mêmes 20 échecs d'assertion et 39 erreurs sont reproduits avec les
trois modules du compilateur d'avant ce cycle. Les journaux sont conservés.
Les fixtures lisent maintenant les allocations avant les opérations étudiées ;
les sorties ajoutées sont attendues explicitement. Les traces de destruction,
les identités de slots, les décisions du modèle (19 admissions, 13 refus), et
les diagnostics mémoire attendus ne sont pas affaiblis. Les appels historiques
sur une référence existante utilisent son nom conformément à la règle retenue.

## Preuves exécutées

Les passages async/natifs utilisent Clang C11, pthread, warnings bloquants,
UBSan fatal et O0/O2. Le recontrôle des 72 méthodes synchrones utilise Clang
C11, warnings bloquants et UBSan fatal **sans option d'optimisation explicite** :
leur ancien harnais ne lit pas CRUST_TEST_OPT. Aucun nouveau résultat ASan,
TSan, second compilateur ou preuve formelle.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Initial O0 | 23 méthodes, 14,520 s ; 2 échecs et 1 erreur. Inclut accidentellement les tests natifs importés ; l'import a ensuite été corrigé | [Initial](../../validation/async-struct-reference-fields-initial-o0.log) |
| Recontrôle O0 | 10 méthodes, 4,846 s, OK | [Recontrôle](../../validation/async-struct-reference-fields-recheck-o0.log) |
| Ciblé + modèle O0 | 13 méthodes, 9,159 s, OK | [O0](../../validation/async-struct-reference-fields-complete-o0.log) |
| Frontière des effets, réemprunt explicite corrigé | 1 méthode O2, 0,011 s, OK | [Frontière](../../validation/async-struct-reference-fields-update-boundary-o2.log) |
| Ciblé final O2 | 12 méthodes, 6,550 s, OK ; 16 exécutions C, dont un LaunchFailed injecté et un reset historique ; 25 programmes refusés dans chacun des deux stages, soit 50 contrôles | [Baseline du runner final](../../validation/async-struct-reference-fields-classified-mutations-o2.log) |
| Modèle O2 + régressions historiques initiales | Le modèle passe ses 16 cas (11 exécutions, 5 refus). Ensemble de 73 méthodes : 48,253 s, 20 échecs et 39 erreurs historiques | [Passage initial élargi](../../validation/async-struct-reference-fields-model-and-sync-o2.log) |
| Mêmes régressions sur compilateur antérieur | 72 méthodes, 23,936 s ; mêmes 20 échecs et 39 erreurs | [Baseline historique](../../validation/async-struct-reference-fields-sync-baseline.log) |
| Fixtures historiques corrigées, UBSan fatal | 72 méthodes, 43,956 s, OK | [Recontrôle synchrone](../../validation/async-struct-reference-fields-sync-recheck.log) |
| Régression contrats/features/références O2 | 76 méthodes, 72,495 s, OK | [Contrats](../../validation/async-struct-reference-fields-contracts-o2.log) |
| Régression native O2 | 244 méthodes, 207,068 s, OK | [Native](../../validation/async-struct-reference-fields-native-o2.log) |

Les sélections se recouvrent. La régression native a chargé la fixture initiale
de remplacement de champ ; le passage ciblé final utilise le réemprunt explicite
corrigé. Il n'y a pas de changement du compilateur entre ces deux passages.

Le modèle indépendant raisonne sur deux liens de durée de vie, tâche → porteur
→ Int, l'exclusivité et l'attente. Il ne consulte pas les décisions du compilateur.
Les tests couvrent aussi les alias hors de leur bloc, les arguments réellement
distincts ou aliasés, les reprises de boucle, la destruction unique et le réemploi.

## Mutations

Le [runner ciblé](../../tests/run_async_struct_reference_field_mutations.py) modifie
des copies temporaires. Cinq fautes comportementales sont détectées : offsets
calculés comme des Int, valeur lue remplacée, dépendances du bridge supprimées,
reset limité au premier lien et dépendance de capture perdue.

La suppression du refus des changements de dépendances est classée
`STAGE_DIVERGENCE` : verify_program accepte le programme, mais compile_source
le refuse encore par une autre limitation de représentation. C'est un écart
entre stages détecté, pas une sixième preuve de détection d'une violation mémoire
à l'exécution. Les journaux intermédiaires qui l'étiquetaient DETECTED sont
historiques ; le runner final distingue ce cas.
Le [journal classé par stage](../../validation/async-struct-reference-fields-stage-mutations-o2.log)
conserve les noms des deux points d'entrée pour rendre cet écart explicite.

Les six mutations du cycle précédent sont également détectées après adaptation
de leurs ancres au nouveau calcul d'offset. Leur baseline réussit 14 méthodes,
15 exécutions C et 29 refus : [journal](../../validation/async-struct-reference-fields-prior-mutations-o2.log).
Aucun taux global de détection n'est déduit de cet échantillon choisi.

## Limites et suite

Le [réemprunt direct de champ dans une tâche](../../validation/open-async-struct-field-reborrow.crb)
reste refusé : [diagnostic](../../validation/open-async-struct-field-reborrow.log).
Il faut raccorder les projections, leurs prêts par champ, les appels et les
provenances des résultats. Les modifications des dépendances de champs doivent
ensuite se propager dans les contrats des tâches et chez leurs appelants.
Les champs propriétaires, les graphes de types plus généraux, les captures
par transfert et la construction générale de structures dans les états restent
ouverts. Le layout aplati est utilisé, mais ce cycle n'a pas validé la construction
de structures imbriquées contenant des références.

Les autres obligations de stockage, signatures, scheduler public, Select et
gardes restent ouvertes. Ce cycle ne clôt pas l'objectif global et ne prouve
pas la sûreté de tous les graphes de références ni de tous les ordonnancements.

## Reproduction

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_struct_reference_fields test_async_struct_reference_field_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_reference_field_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_capture_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_SANITIZE=undefined python3 -m unittest test_reset_transitions test_reference_fields test_mutable_reference_fields -v
```
