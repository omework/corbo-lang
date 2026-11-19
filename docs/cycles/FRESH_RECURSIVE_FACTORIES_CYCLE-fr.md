[English](FRESH_RECURSIVE_FACTORIES_CYCLE.md)

# Graphes récursifs neufs dans les fabriques de tâches

## Règles et implémentation

Règles existantes de contrats, provenance, transferts, durabilité des pools et
AS8–AS12. Aucune règle normative modifiée. Ce lot complète le cas où une fabrique
construit un graphe neuf dans des pools injectés puis retourne une tâche qui le
possède. Les lots précédents couvraient les graphes reçus par transfert.

L'analyse utilisait uniquement le préfixe fini du type jusqu'à sa première
répétition. Elle fabriquait ainsi une cible locale pour une variante absente et
perdait le pool et l'emprunt du descendant profond réellement construit.
results.py suit maintenant les chemins concrets de Value. Les contrats portent
aussi les variantes par chemin via task_result_shapes ; ces métadonnées sont
instanciées lors des relais et exploitées pour restaurer le graphe après attente.
Le lowering async conserve les champs profonds du résultat propriétaire et
les captures explicitement vides pour les variantes prouvées absentes.

## Cas exécutés

Trois méthodes dans tests/test_fresh_recursive_factories.py : cinq
programmes natifs et sept invalides aux deux entrées. Construction de deux
liens A<Node> et d'un Node.End contenant &Int ; appel direct et relayé depuis
main, puis appel depuis une tâche et lecture après yield. Lecture 7, nettoyage,
réemploi du pool terminal et écriture 8 ; mutation de cible avant lecture et
destruction du pool avant attente refusées.

| Journal dans validation/ | Résultat |
| --- | --- |
| fresh-recursive-factories-first-o0.log | 2 méthodes refusées : cible non durable |
| fresh-recursive-factories-second-o0.log | Chemins trouvés ; variantes de descendants et captures manquantes |
| fresh-recursive-factories-third-o0.log | Exécutions passent ; marqueur CHECK oublié dans les cas de drop |
| fresh-recursive-factories-fourth-o0.log | 2 méthodes, succès |
| fresh-recursive-factories-fifth-o0.log | 2 méthodes, 1,733 s, code 0 |
| fresh-recursive-factories-conditional-first.log | Jonction End/Link refusée : provenance de champ absente |

La troisième méthode vérifie la jonction des deux formes retournées :
un Node.End direct ou le graphe à deux liens. Les deux branches passent, ainsi
que leurs refus de mutation prématurée. La jonction ignore une forme seulement
si une variante d'un ancêtre prouve que le chemin y est absent ; une variante
inconnue reste inconnue. Les formes proviennent du contrat final de la tâche,
pas d'une supposition que le graphe capturé demeure inchangé.

Première régression : 82 méthodes en 118,799 s, code 0, dans
validation/fresh-recursive-factories-regression-o2.log. Ciblé final O0 : trois
méthodes en 2,554 s, code 0, dans fresh-recursive-factories-final-o0.log.
Régression finale : 83 méthodes en 119,547 s, code 0, dans
fresh-recursive-factories-final-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_fresh_recursive_factories -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_fresh_recursive_factories test_recursive_task_factories test_recursive_join_helpers test_async_recursive_owned test_factory_owned_effects test_task_result_storage test_async_local_owned_result_graphs test_async_result_storage test_async_awaited_owned_results test_select_result_storage test_recursive_link_replacement test_recursive_mutable_results test_recursive_borrow_results -v
```

Les harnais ciblés compilent C11/pthread, warnings en erreurs et UBSan fatal.
Pas de campagne adversariale ni de mutations ajoutée. Les assertions de valeurs,
de destruction et de durée de vie sont les oracles explicites des cas.

## Limites

Les formes dont une alternative demeure opaque
ne sont pas réduites à une variante connue d'une autre branche ; elles peuvent
rester conservatrices. Pas de preuve générale ni de déclaration d'achèvement
de l'intégration globale.

Écart suivant reproduit aux deux entrées : un emprunt &Vector<A<Int>> ne peut
pas encore être capturé par une tâche. Le programme et les diagnostics sont
conservés dans validation/open-async-owned-vector-capture.crust et .log. Le
programme construit un vecteur, y transfère une allocation, attend une tâche
qui ne lit que sa longueur, puis détruit le vecteur et réemploie le pool Int.
Cette limite est une lacune d'implémentation, pas une nouvelle règle de langage.

Snapshot : /tmp/crust-before-fresh-recursive-factories/.

Diffs : validation/fresh-recursive-factories-{results.py,crust.py,async_lowering.py}.patch.
