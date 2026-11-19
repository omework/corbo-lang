[English](ASYNC_OWNED_FIELD_WRITES_CYCLE.md)

# Remplacement de champs possédés en async

## Fonctionnalité raccordée

Ce lot applique les règles existantes de remplacement, de provenance et de
destruction aux champs A<T> en async, ainsi que AS16, RT6 et SL1. Aucune règle
normative n'est changée. Les cas sont issus des remplacements déjà exercés en
synchrone et des attentes/suspensions déjà retenues.

Le contrat de suspension utilise maintenant la représentation commune
`owned_field_writes`, collectée aux points de suspension. Le contrat de
terminaison reste distinct. Un remplacement précédant yield appartient au
premier ; un remplacement ultérieur peut appartenir seulement au second.
Les snapshots passent par les mêmes contrôles de provenance durable que les
écritures à la terminaison.

Les effets sont raccordés au backend après un appel synchrone, un await ou
un Select. Le suivi des sources par champ conserve les pools requis. Chez
l'appelant synchrone, l'attente du handle applique aussi les modifications du
graphe possédé, avec les alternatives initiales requises par LaunchFailed.

L'affectation directe d'un champ A<T> est générée dans l'état async : la nouvelle
valeur est évaluée, son type et sa provenance sont vérifiés, le champ reçoit
le nouveau pointeur et l'ancienne allocation est détruite. L'adresse de la
nouvelle allocation reste stable. Le nettoyage après suspension suit le
contenu effectivement possédé par l'agrégat.

## Validation ciblée

Sept méthodes passent à O0 en 3,603 s et à O2 en 4,373 s : huit exécutions
natives et un programme refusé aux deux entrées par passage. Journaux :
`validation/async-owned-field-writes-scope-final-o0.log` et
`validation/async-owned-field-writes-scope-final-o2.log`. Les deux passages
se terminent par OK ; le processus O2 a été observé terminé avec code 0.

Les contrôles comprennent les sources distinctes aux suspensions et à la
terminaison, join, await direct, affectation directe, fonction auxiliaire,
réemploi des pools, échec du lancement, remplacement conservé par une perdante
de Select et descendant d'enum. L'échec de lancement conserve la valeur initiale
7 ; une terminaison normale expose 11 ; une perdante arrêtée après yield
conserve 9.

Le premier passage contenait une attente de refus incorrecte : le pool court
fournissait seulement une allocation intermédiaire déjà détruite avant sa fin.
Ce programme est maintenant explicitement attendu valide et exécuté. Le cas
refusé place la dernière allocation dans le pool court : elle survivrait à
ce pool. Le journal initial est conservé ; aucune règle n'a été modifiée pour
accepter le premier cas.

La régression directement liée à O2 passe 109 méthodes en 64,053 s, code 0 :
`validation/async-owned-field-writes-regression-o2.log`. Elle précède un dernier
ajustement : le contrôle de provenance cherche le scope le plus proche d'un
receveur transféré vers un enfant. Les deux passages ciblés de sept méthodes
ci-dessus vérifient cet ajustement, avec un cas dédié ; la régression complète
n'a pas été répétée après cette modification.

Les exécutions natives utilisent
Clang C11, pthread et UBSan sans récupération. Aucune campagne de mutations ni
recherche adversariale supplémentaire n'est lancée, selon la consigne utilisateur.

## Limites

Les descendants remplacés contenant eux-mêmes des emprunts restent explicitement
non raccordés dans ce lot historique. Les champs &Int et &mut Int sont désormais
couverts par le [lot suivant](ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
Les sources de stockage agrégées peuvent conserver
des sources anciennes par prudence ; le lot ne revendique pas une précision
maximale pour toutes les branches, fabriques et projections. Les gardes de mutex
et les autres familles ouvertes ne sont pas couvertes par ces résultats.
L'audit indépendant reste distinct et n'est pas réputé effectué.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_field_writes -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_field_writes test_async_consuming_enum_match test_async_enum_suspension_fields test_suspension_effects test_async_structure_effects test_select_source test_async_owned_struct_returns test_task_result_storage test_foundation_rules.FoundationTests.test_owned_struct_field_replacement_preserves_disjoint_borrow test_foundation_rules.FoundationTests.test_borrowed_owned_field_replacement_keeps_alternative_sources -v
```

Snapshot : `/tmp/crust-before-async-owned-field-writes/`.
Les différences d'implémentation sont archivées dans
`validation/async-owned-field-writes-{async_lowering,async_structure_effects,crust}.py.patch`.
