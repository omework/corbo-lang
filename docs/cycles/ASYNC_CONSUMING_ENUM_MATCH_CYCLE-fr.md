[English](ASYNC_CONSUMING_ENUM_MATCH_CYCLE.md)

# Match consommant d'enum dans un corps async

## Règles existantes appliquées

Ce lot raccorde les transferts explicites, F2/U1 (usage des champs possédés),
D1 (destruction), les durées de vie des pools et AS8–AS15 au match consommant.
Il ne change pas la sémantique normative. La priorité de validation confirmée
par l'utilisateur est l'implémentation et les tests des cas déjà énumérés ;
la recherche adversariale approfondie et les mutations sont reportées à un
audit distinct. AGENTS.md conserve cette consigne.

## Implémentation

Le backend async extrait les champs du bras actif vers les membres stables de
l'état, détache les champs possédés de leur porteur et détruit ce dernier avant
le corps du bras. Les champs extraits suivent le nettoyage ordinaire, y compris
après yield, break, continue, return et destruction d'une perdante de Select.
L'adresse de l'allocation transférée reste inchangée.

Les champs partagés et mutables conservent les cibles extérieures nécessaires.
Un match consommant ne crée pas de réservation d'emprunt sur le porteur détruit.
Les motifs écartant un champ possédé et les liaisons sans usage explicite sont
refusés dans chaque variante, même si la construction connue en choisit une autre.

Deux suivis de provenance ont été corrigés :

- Un candidat `owned_projection` décrit la source du champ, avec son chemin,
  au lieu de reprendre celle de la racine. Le contrat de résultat async peut
  restituer un descendant et ses propres descendants possédés.
- Le backend conserve les sources par champ lors d'une construction et des
  transferts locaux. Extraire un champ ne lui impose plus la durée de vie du
  pool de son ancien porteur. Les métadonnées suivent les mêmes instantanés et
  jonctions de contrôle que les dépendances stockées.

Les contrats de retour d'emprunt reconnaissent également `moved_field_parameter`,
déjà produit par l'analyse commune du match consommant.

## Tests exécutés

La suite `tests/test_async_consuming_enum_match.py` passe 10 méthodes à O0,
en 4,377 s, code 0. Elle contient 10 exécutions natives et 10 programmes refusés,
contrôlés par les deux entrées verify_program et compile_source (20 contrôles).
Ces entrées partagent des analyses ; ce ne sont pas deux preuves indépendantes.
Journal : `validation/async-consuming-enum-match-final-o0.log`.

Les cas portent sur l'ordre porteur/champ, la destruction unique, l'identité
d'adresse, le réemploi des pools, les retours de références partagées et mutables,
les champs possédés imbriqués, les références stockées, Select et les sorties
de boucle. Le transfert depuis un pool de porteur plus court est admis ; celui
depuis un pool du champ trop court est refusé.

Les binaires sont compilés avec Clang, C11, pthread, Wall/Wextra/Werror et UBSan
sans récupération. Aucun résultat ASan ou TSan n'est revendiqué.

La régression à O2 passe 117 méthodes en 95,528 s, processus terminé avec code 0.
Elle couvre les deux modes de match, les enums possédés, les retours de structures
et leurs graphes, le stockage des résultats de tâches, les résultats propriétaires,
Select et les nettoyages suspendus. Journal :
`validation/async-consuming-enum-match-regression-o2.log`.

## Échecs intermédiaires et limites

Le cas enregistré `validation/open-async-consuming-enum-match.crust` était
refusé explicitement par le backend ; il s'exécute maintenant et affiche 7.
Le premier passage a relevé la mauvaise source du descendant retourné et la
provenance d'emprunt déplacé non raccordée. Il a aussi exécuté les tests Select
importés par inadvertance : l'import du harnais a été corrigé. Le test de durée
de vie du pool a ensuite reproduit le refus conservateur causé par la fusion
des sources du porteur et du champ, corrigé par le suivi par champ.

Deux préparations de tests ont été corrigées sans changer leur intention :
le transfert vers le bras doit être à son entrée ; le cas de retour terminal
ne doit pas conserver un suffixe inatteignable. Les journaux intermédiaires sont
conservés dans `validation/async-consuming-enum-match-*.log`.

Ce lot n'établit pas une sûreté générale. Les effets de suspension sur les
descendants d'enums restent un chantier distinct. Le suivi par champ des sources
locales est précis pour les constructions et transferts testés ; les producteurs
qui ne fournissent pas ces métadonnées conservent la provenance agrégée. Les
compositions générales de contrats, graphes récursifs et types non représentés
ne sont pas déclarées couvertes par cette suite. Aucun audit indépendant ni
nouvelle campagne de mutations n'a été exécuté pour ce lot.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_consuming_enum_match -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_consuming_enum_match test_async_enum_match test_async_owned_enums test_async_owned_struct_returns test_async_local_owned_result_graphs test_async_result_storage test_task_result_storage test_owned_results test_select_result_storage test_suspended_cleanup -v
```

Snapshot des modules précédents : `/tmp/crust-before-async-consuming-enum-match/`.
La commande initiale de copie utilisant `python` était indisponible ; le snapshot
a été reconstruit immédiatement avec `python3` et le patch archivé du lot précédent
pour async_lowering.py, seul module déjà modifié à ce moment.
Les trois patches des modules sont archivés sous
`validation/async-consuming-enum-match-*.py.patch`. Le point d'injection de
la campagne de mutations du lot précédent a été ajusté au nouveau texte, sans
relancer cette campagne.
