[English](FACTORY_OWNED_EFFECTS_CYCLE.md)

# Remplacements propriétaires dans les contrats des fabriques

## Périmètre et règles

Suite de `FACTORY_SUSPENSION_CONTRACTS_CYCLE.md`. Les règles AS3–AS5, AS14,
AS16, SL1 et les règles existantes de remplacement et de durée des pools
s'appliquent aussi lorsqu'une tâche créée par une fonction synchrone remplace
un champ A<T>. Aucune sémantique nouvelle ni modification normative.

Le cas conservé dans `validation/open-factory-owned-suspension.crust` reprend
le remplacement déjà testé pour les appels async directs : valeur 7 au départ,
allocation de 9 avant yield, allocation de 11 après reprise. Une perdante de
Select doit conserver 9 et son pool ; une terminaison normale conserve 11.

## Implémentation

Les contrats distinguent les remplacements à la terminaison et aux points de
suspension. Les valeurs de tâches conservent le porteur, le chemin du champ,
les sources possibles du nouvel objet et ses emprunts contenus. Les fabriques
relayées remappent ces éléments sur leurs propres paramètres. Les effets ne
sont pas exécutés à la création d'une instance inactive.

L'analyse applique les remplacements avant les mises à jour de références des
champs. Les effets d'un join conservent l'alternative sans exécution en cas de
LaunchFailed ; l'attente directe d'une tâche inactive applique sa terminaison.
Les résumés de Select utilisent les remplacements suspendus des perdantes.
Le vérificateur et la préparation des effets pour le C généré reçoivent les
mêmes informations de provenance depuis le contrat.

Le premier passage a révélé un défaut connexe : un pool injecté retransmis par
une autre fabrique était décrit comme une cible locale. Le remappage conserve
maintenant son identité de paramètre source. La permutation des arguments
remappe également les emprunts contenus dans une nouvelle allocation.

## Cas exécutés

Six méthodes dans `tests/test_factory_owned_effects.py` :

- Contrats de fabrique et de relais examinés sans corps synchrones ; pool
  intermédiaire distinct du pool final.
- Join normal et échec de lancement injecté ; destruction unique de l'ancien
  élément et réemploi des slots après nettoyage.
- Await via fabrique relayée, paramètres permutés et transfert de tâche.
  Drop d'une instance inactive après yield sans remplacement de son champ.
- Select perdant, par relais et directement depuis une fabrique.
- Pool intermédiaire court admis après terminaison normale ; pool final trop
  court refusé, en await et en join.
- Descendant contenant &Int, fabrique à paramètres permutés : lecture après
  Select, drop de la cible refusé avant lecture, réemploi après nettoyage.

Le passage ciblé comprend huit exécutions natives et trois programmes invalides
aux deux entrées, soit six contrôles de refus. Les valeurs et traces attendues
sont écrites dans les tests, indépendamment des contrats calculés.

## Résultats exécutés

- O0 ciblé : six méthodes, 3,579 s, processus terminé avec code 0 ; journal
  `validation/factory-owned-effects-o0-third.log`.
- O2 lié : 117 méthodes, 80,867 s, processus terminé avec code 0 ; journal
  `validation/factory-owned-effects-regression-o2.log`. Il inclut les six
  méthodes ciblées sur l'implémentation finale.

Les exécutions natives utilisent Clang C11, pthread, les avertissements traités
comme erreurs et UBSan sans récupération. Aucun test sauté dans ces passages.
Ce n'est pas la suite entière du projet.

## Limites

Ce lot exerce A<Int> et A<Leaf> contenant &Int. Il ne démontre pas les graphes
récursifs, toutes les variantes d'enums ni toutes les combinaisons de mutations.
Les unions de provenance et les effets de lancement restent conservateurs.
Les préfixes de tâches déjà lancées restent distincts de ceux des tâches
inactives attendues directement. Les arbitrages scheduler/constructeurs de mutex
et capture d'un handle lancé ne sont pas modifiés.

Pas de nouvelle campagne de mutations ou de recherche adversariale approfondie.
Les modèles présents dans les suites liées sont rejoués, sans revendiquer un
nouveau modèle indépendant ou une preuve générale de sûreté.

## Reproduction et artefacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_factory_owned_effects
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_factory_owned_effects test_factory_suspension_contracts test_async_result_factories test_async_owned_field_writes test_async_owned_borrow_writes test_async_replaced_borrow_results test_async_mutable_descendant_results test_suspension_effects test_select_source test_async_structure_effects
```

Snapshot : `/tmp/crust-before-factory-owned-effects/`. Les différences de
`results.py`, `async_structure_effects.py`, `async_lowering.py` et `crust.py`
sont archivées dans `validation/factory-owned-effects-*.py.patch`.
Les journaux initiaux conservent le refus des pools relayés. Le deuxième
passage a aussi détecté une liaison de test redéclarée dans le même scope ;
elle est renommée sans changement des effets attendus.
