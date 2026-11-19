[English](RECURSIVE_LINK_REPLACEMENT_CYCLE.md)

# Remplacement d'un lien propriétaire récursif complet

## Règles et modification

Application des règles retenues pour les champs A<T>, les emprunts, le
remplacement et le nettoyage. La nouvelle allocation est évaluée avant la
destruction de l'ancien sous-arbre ; son pool doit survivre au porteur. Aucun
changement normatif, aucune copie du contenu du sous-arbre déplacé.

Le cas alterne Node.Link { next: A<Link> } et Link { node: A<Node> }.
Un helper remplace link.node par un Node.End neuf, détruisant l'ancien Node.Link
et ses descendants. L'écriture était déjà implémentée. Le filtre de lecture du
match refusait ensuite `let child = &*link.node` et empêchait de parcourir le
nouveau sous-arbre. Il transmet maintenant le type de cette projection au
contrôle général, qui vérifie le mode et les prêts. Les champs inconnus ont
un diagnostic précis. Un emprunt mutable à travers un porteur partagé demeure
refusé.

## Cas ciblés

Deux méthodes dans tests/test_recursive_link_replacement.py : deux exécutions
natives et quatre programmes invalides aux deux entrées.

- Remplacement du sous-arbre, lecture de la nouvelle valeur 9, destruction
  unique des cinq anciennes allocations nommées.
- Réemploi d'un slot de Node et de Link avant la destruction de la racine,
  puis réemploi du pool destinataire de capacité un avec la valeur 12.
- Même opération appelée depuis une tâche, avec yield après remplacement.
- Pool destinataire créé dans un bloc enfant refusé pour les deux chemins.
- Emprunt mutable à partir du champ accessible en lecture, et champ inexistant,
  refusés par les deux entrées.

## Résultats exécutés

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-link-replacement-first-o0.log | Deux sous-cas refusés par le filtre de match |
| recursive-link-replacement-second-o0.log | Une méthode, 1,036 s, code 0 |
| recursive-link-replacement-third-o0.log | Remplacement passe ; diagnostic générique pour champ inexistant |
| recursive-link-replacement-final-o0.log | Deux méthodes, 0,916 s, code 0 |

Régression terminée : 49 méthodes en 30,432 s, code 0, dans
validation/recursive-link-replacement-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_link_replacement -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_recursive_link_replacement test_recursive_owned_replacement test_recursive_mutable_results test_recursive_borrow_results test_recursive_borrow_projections test_shared_match_field_reads test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_enum_nominal test_mutable_match test_mutable_match_function_return -v
```

Les harnais ciblés/async utilisent C11/pthread, warnings en erreurs, UBSan fatal,
O0 puis O2. Les anciens harnais synchrones activent UBSan sans ajouter O2 et
emploient legacy-reset pour leurs scénarios historiques. Aucun nouveau modèle
indépendant ni campagne de mutations ; les cas précédents restent dans la
sélection de régression.

## Limites

Couverture de cette substitution finie et des chemins indiqués. Les graphes
neufs produits dans les contrats de fabriques de tâches récursives restent à
vérifier ; ni ce cycle ni les précédents ne prouvent une sûreté générale.
L'intégration de toutes les fonctionnalités et les arbitrages publics ouverts
ne sont pas déclarés terminés.

Snapshot : /tmp/crust-before-recursive-link-replacement/.
Diff : validation/recursive-link-replacement-crust.py.patch.
