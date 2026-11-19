[English](CORE_LOCK_HASHMAP_CYCLE.md)

# Contrats de verrou et stockage natif de HashMap

[MT10](../ASYNC_MULTITHREAD_RULES.md#5-sûreté-mémoire-entre-threads) ajoute un
contrat de verrou sur le receveur. [HM1–HM6](../HASH_MAP.md) fixent les clés,
les opérations, les emprunts, le stockage et les dépendances de la première
version de `HashMap`.

Le parseur accepte les deux formes de MT10 sur les méthodes synchrones.
Le vérificateur associe l'identité du receveur au résultat et suit cette
dépendance jusqu'à la destruction effective. Les contrats synchrones
relayant une acquisition ou un résultat conservent l'information. Si deux
paramètres doivent désigner des objets distincts, le contrat fait vérifier
cette exigence chez l'appelant. L'annotation sert à l'analyse statique.
L'acquisition et la libération réelles restent la responsabilité du corps.

Le stockage natif de `HashMap` utilise les deux extrémités d'une data stack
dédiée. Les entrées grandissent à une extrémité. L'index grandit à l'autre
et peut être reconstruit en place. Les cases libres sont réutilisées. Le
remplacement d'une clé existante ne consomme aucun emplacement supplémentaire.
Les opérations C distinguent l'insertion, le remplacement et l'échec de
capacité avant de publier un changement.

Les essais synchrones exercent la libération par `drop`, par fin de bloc,
le déplacement vers un nouveau receveur et le relais par une fonction.
Ils vérifient le refus d'une nouvelle acquisition après le dernier usage du
résultat, via un alias, via un auxiliaire et après une destruction sur un seul
chemin. Les refus sont vérifiés dans `verify_program` et `compile_source`.
Les sondes C vérifient une collision, le maintien de l'adresse lors du
réindexage, la réutilisation d'une case, la restitution des anciennes valeurs,
le nettoyage des valeurs restantes et les deux chemins de capacité.

Le retour d'un résultat de méthode à travers un relais a exposé deux défauts.
Le placement ne reconnaissait pas certaines méthodes comme producteurs d'une
valeur locale. L'inférence de provenance utilisait aussi l'identité d'un appel
temporaire recréé à chaque passe, ce qui pouvait empêcher la convergence.
Le placement reconnaît désormais ces méthodes et l'inférence garde l'identité
de l'expression source. Les régressions incluent les retours de structures
et les appels synchrones depuis async.

- [Essais ciblés UBSan à `-O0`](../../validation/core-lock-hashmap-o0.log).
- [Essais ciblés et régressions UBSan à `-O2`](../../validation/core-lock-hashmap-o2.log).

Le passage d'un résultat qui porte un verrou en argument et sa capture async
sont restreints dans le prototype. Les essais portent sur les obligations
d'appel et de durée de vie, et s'appuient sur le contrat fourni par
l'implémentation pour le verrouillage effectif.

Le code C de `HashMap` est exercé directement. Son raccordement aux
expressions, types et résultats Crust reste ouvert, ainsi que le suivi des
emprunts et des dépendances par entrée et l'ordre de nettoyage de charges
dépendantes. Les résultats constituent des essais fonctionnels ciblés.
