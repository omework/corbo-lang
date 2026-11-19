[English](ASYNC_OWNED_ENUMS_CYCLE.md)

# Enums alloués : captures, retours async et pools par bras

## Périmètre et règles

Ce lot applique AS2, AS8–AS15, SL1, les contrats de provenance, les transferts
explicites et la distinction entre T local et A<T>. Il ne change aucune règle
normative. Le contre-exemple `validation/open-async-owned-enum.crust`, refusé
avant ce lot mais admis dans son pendant synchrone, est maintenant exécuté.

Les formes couvertes sont des enums alloués dont les bras contiennent Int,
&Int, &mut Int et des descendants possédés pris en charge par l'analyse des
agrégats finis. Un pool conserve une source et un layout par bras. Transférer
l'enum conserve son allocation ; le retour restitue son bras possible, ses
sources et ses prêts. Un auxiliaire synchrone peut emprunter ou recevoir cet
enum depuis un corps async. Les handles publics gardent le type A<Enum>.

## Défauts rencontrés et corrections

- Les classifications des captures, résultats et signatures publiques ne
  reconnaissaient que les structures. Elles incluent maintenant les enums
  représentables. Les pools locaux async construisent chaque source de bras
  avec sa taille, ses offsets et ses catégories de champs.
- Le pont vers un auxiliaire synchrone traitait certaines références d'enums
  comme des références de tableaux. Il reconstruit maintenant les métadonnées
  des champs uniquement lorsque le bras correspondant est actif à l'exécution.
- Les chemins empruntés conservent leur préfixe de bras. Les constructions de
  champs acceptent aussi le réemprunt explicite `&*n`, avec vérification de
  capacité. Les emprunts de temporaires restent refusés : une suppression trop
  large du filtre syntaxique les avait involontairement admis. Le test historique
  `test_reference_field_requires_explicit_named_int_borrow` a détecté cette
  régression, corrigée en autorisant uniquement le réemprunt nommé supplémentaire.
- Les résultats de tâches perdaient les variants possibles. Cette information
  traverse désormais captures, transferts, branches, relais et join. Une
  alternative inconnue ne peut pas être éliminée par une alternative connue.
  Un champ contractuel absent est ignoré seulement si son bras est prouvé
  impossible ; l'absence d'information n'est pas une preuve d'impossibilité.
- La régression des contrats opaques a révélé un registre de types périmé
  lorsque le client installait ses déclarations sans aucun corps de fonction.
  L'indexation resynchronise le registre des descripteurs publics. Le test
  vérifie toujours que les corps et définitions async sont absents.

## Preuves ciblées exécutées

`tests/test_async_owned_enums.py` passe 12 méthodes à O0 en 17,243 s :
24 exécutions natives, 14 programmes invalides et 28 contrôles de refus.
Journal : `validation/async-owned-enum-final-instrumented-count-o0.log`.
Les contrôles verify_program et compile_source partagent des composants et
ne constituent pas deux vérificateurs indépendants.

Les cas admis couvrent await direct, spawn/join, fabriques et relais, plusieurs
bras dont un vide, champs partagés et mutables, descendants possédés, créations
depuis un pool injecté, destruction inactive, échec de lancement et réemploi.
Les refus couvrent notamment les transferts implicites, l'usage après transfert,
les drop prématurés, les pools trop courts, les champs manquants et la confusion
entre résultat local et allocation en pool.

Un modèle indépendant croise zéro ou une suspension pour chacune des deux
branches de Select : quatre combinaisons. Il calcule le premier Ready selon
l'ordre des polls, sans consulter le compilateur. Les exécutions comparent le
bras rendu, la destruction unique des deux captures et la réutilisation des
deux sources de bras après nettoyage. Ces quatre cas sont inclus dans les comptes.

## Mutations et limite révélée par l'oracle

La campagne finale passe son baseline de 12 méthodes à O2 en 21,092 s et
détecte cinq mutations par assertions : mauvais numéro de bras à la création,
lecture de bras inactifs, perte des variants au join, perte des variants publics
et omission des chemins empruntés de l'enum. Journal :
`validation/async-owned-enum-gate-mutations-o2.log` ; processus terminé avec
code 0, échecs internes des compilateurs mutés attendus.

La mutation de lecture d'un bras inactif survivait dans la deuxième campagne
(`async-owned-enum-second-mutations-o2.log`). Une sortie correcte et UBSan ne
suffisaient pas : une lecture inutile pouvait rester dans une page mappée ou
être supprimée par l'optimiseur. Le test du pont instrumente donc le C pour
exiger que chaque lecture de référence désigne un champ du layout actif et
une allocation vivante. Ce contrôle provoque un échec observable avant memcpy.
Il ne modifie pas le runtime livré et ne déduit pas la gagnante depuis celui-ci.
Il dépend toutefois des métadonnées de layout produites par l'implémentation ;
ce n'est pas une preuve indépendante de la correction de ces métadonnées.

## Régressions

La première régression de 200 méthodes a terminé avec un échec et une erreur
en 211,375 s : champ d'un bras impossible dans un handle public et registre
périmé du client opaque. Journal : `async-owned-enum-regression-o2.log`.
Ces deux défauts ont été corrigés ; les tests ciblés passent, dont le cas opaque
en 0,014 s (`async-owned-enum-opaque-contract-fix.log`).
La première régression synchrone passe 234 des 235 méthodes ; la méthode
restante détecte l'emprunt de temporaire décrit ci-dessus, en 96,842 s.
Journal : `async-owned-enum-sync-regression-o2.log`. La régression synchrone
finale passe les 235 méthodes en 113,717 s, avec code 0, dans
`async-owned-enum-final-sync-regression-o2.log`.
La régression async intermédiaire passe 200 méthodes en 230,667 s
(`async-owned-enum-final-regression-o2.log`, code 0), avant la dernière
restriction syntaxique des champs. Sa nouvelle exécution sur les sources
finales passe également les 200 méthodes en 199,338 s, avec code 0 :
`async-owned-enum-gate-regression-o2.log`.
Tous les processus finaux sont terminés. Ce lot est clos pour son périmètre
documenté ; il ne clôt pas le chantier global.

Après rétablissement du refus des emprunts temporaires, les 12 méthodes ciblées
passent également à O0 en 19,996 s (`async-owned-enum-final-gate-o0.log`).
La campagne précédente à O2, avant cette dernière restriction syntaxique,
avait déjà détecté les cinq fautes (`async-owned-enum-final-mutations-o2.log`,
baseline en 15,757 s) ; la campagne finale les détecte à nouveau.

Les exécutions ciblées utilisent clang C11, pthread, O0/O2, avertissements
comme erreurs et UBSan fatal. Aucun résultat nouveau ASan ou TSan n'est revendiqué.

## Traces intermédiaires et limites

Les journaux `async-owned-enum-first-o0.log`, `second-o0.log`, `third-o0.log`
conservent les échecs intermédiaires de classification, diagnostic, chemins et
variants. Les suites enrichies de dix puis douze méthodes passent dans
`fourth-o0.log` et `fifth-o0.log`, avant l'ajout du second bras empruntant au
test de handle public. Cet ajout a révélé le défaut conservé dans
`async-owned-enum-count-o0.log`. La première campagne de mutations s'arrête
sur ce baseline défaillant : elle n'est pas comptée comme une campagne exécutée.

Ce lot ne couvre pas encore le match direct d'un enum utilisateur dans le
corps async, sa construction locale sans pool, les graphes récursifs ni toutes
les compositions imbriquées de variants. Les tests d'affichage dans les corps
async passent par un auxiliaire synchrone. La précision des variants descendants
reste à éprouver séparément. Aucun de ces refus ne devient une règle normative.
Le cas minimal `validation/open-async-enum-match.crust` confirme cet écart :
les deux entrées refusent `match_expr` dans le corps async, alors qu'elles
acceptent son pendant synchrone (`validation/open-async-enum-match.log`).
Reset reste retiré de l'API publique ; les éventuels cas historiques de la
régression synchrone utilisent explicitement le profil de compatibilité.

Le chantier global reste incomplet : autres compositions async, gardes de
mutex et audit des sept brouillons restent à poursuivre. Le type et les
signatures publiques du scheduler restent explicitement à arbitrer.

## Reproduction et archive

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_owned_enums -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_owned_enum_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_owned_enums test_select_result_storage test_select_source test_select_results test_public_structure_handles test_task_result_storage test_async_owned_struct_captures test_async_owned_struct_returns test_async_struct_pools test_async_borrowed_struct_pools test_async_borrowed_local_results test_async_local_owned_result_graphs test_async_execution_arguments test_sync_task_arguments -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_crust test_reference_fields test_mutable_reference_fields test_owned_results test_mutable_match_function_return test_direct_borrow_returns -v
```

Les six diffs Python sont archivés dans `validation/async-owned-enum-*.py.patch`
depuis le snapshot `/tmp/crust-before-async-owned-enum/`. La consigne utilisateur
d'affichage de la checklist à chaque étape est conservée dans AGENTS.md.
