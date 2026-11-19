[English](ASYNC_POOL_ALIASES_CYCLE.md)

# Cycle — emprunts nommés de pools dans les états

Suite du [cycle des pools locaux](ASYNC_LOCAL_POOLS_CYCLE.md).
Aucune modification normative : B1/B2/B4/B4a/B4c, A1–A4, D1,
T6/T9/T11, AS2/AS12/AS13, RT8 et MT7, brouillons 03/04/05.
L’objectif global et les sept brouillons restent partiellement implémentés.

## Implémentation

Les corps async et natifs peuvent lier un pool local par `&p` ou `&mut p`,
et réemprunter une référence de pool par `&*memory` ou `&mut *memory`.
Le type nominal, le mode et les annotations doivent correspondre. Un `&`
supplémentaire sur une référence n’est pas aplati. Une source en lecture
ne devient pas mutable. La réservation suit la dernière utilisation, les
réemprunts, les arguments préparés et les tâches qui capturent la référence.

L’alias conserve les sources locales effectives des allocations créées par
son intermédiaire. Les résumés de résultats suivent aussi les alias de pools
injectés : un résultat issu de p ne retient pas inutilement q. Les frontières
continuent à refuser une allocation dont le pool ne survit pas au receveur.

Une tâche peut sortir du bloc de la liaison alias lorsque le pool reste
durable. Le prêt envers cette liaison est retiré à la frontière ; le prêt
envers le pool demeure. Les valeurs locales aux états ont toujours une adresse
stable. Aucun changement du runtime C n’est nécessaire pour cette extension.

[Diff du lowering](../../validation/async-pool-alias-implementation.patch),
[programme historique](../../validation/open-async-local-pool-alias.crb),
[C généré](../../validation/async-pool-alias-basic.c).

## Scénarios et contre-exemples

Les programmes admis couvrent les quatre types de pools pris en charge,
la réutilisation après drop, yield, les réemprunts imbriqués, les appels
synchrones, les tâches enfants et natives, les boucles avec continue/break,
le transfert au-delà du bloc d’un alias et les sources disjointes.

Les programmes refusés couvrent les modes et niveaux incorrects, les conflits
d’alias, l’utilisation du pool avant l’attente d’une tâche, les arguments
préparés, la réutilisation d’une capture consommée et les fuites d’allocations.
Le pool peut être réutilisé après la fin du prêt sans détruire les allocations
qui restent vivantes : prêt exclusif et dépendance de stockage restent distincts.

La première campagne de mutations laisse survivre l’omission du prêt racine
dans l’argument d’un enfant : l’alias encore présent dans le bloc protège
indirectement ce pool. Le test a été complété par une tâche transférée hors du
bloc de l’alias, suivie d’un accès prématuré au pool. Ce programme doit être
refusé ; la mutation l’accepte. La campagne finale détecte cette omission.
Le journal initial est conservé et n’est pas présenté comme entièrement vert.

## Preuves exécutées

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
résultat ASan/TSan, second compilateur ou preuve formelle.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Ciblé initial O0 | 12 méthodes, 4,552 s, OK | [Initial](../../validation/async-pool-alias-initial-o0.log) |
| Ciblé final + modèle O0 | 15 méthodes, 20,429 s, OK | [O0](../../validation/async-pool-alias-final-and-model-o0.log) |
| Baseline finale O2 | 14 méthodes, 8,804 s, OK ; 15 exécutions C et 27 refus | [Baseline et mutations](../../validation/async-pool-alias-final-mutations-o2.log) |
| Modèle d’ascendance O2 | Une méthode, 5,179 s, OK ; neuf exécutions, trois refus | [Modèle](../../validation/async-pool-alias-model-o2.log) |
| Mutations initiales | Six détectées, une survivante examinée | [Initial](../../validation/async-pool-alias-mutations-o2.log) |
| Mutations finales | Sept fautes détectées | [Final](../../validation/async-pool-alias-final-mutations-o2.log) |
| Mutations des pools locaux rejouées | Baseline 18 méthodes/19,546 s, OK ; six fautes détectées | [Régression mutations](../../validation/async-pool-alias-local-mutations-o2.log) |
| Régression native O2 | 209 méthodes, 213,343 s, OK | [Régression](../../validation/async-pool-alias-native-o2.log) |

Le modèle est l’oracle d’ascendance indépendant du cycle précédent, appliqué
à une chaîne alias → réemprunt → enfant async → allocation retournée. Il compare
les profondeurs lexicales du pool et du receveur, et distingue la copie scalaire
indépendante. Il n’utilise ni le résumé du compilateur ni son état interne.

Les sept mutations ciblent le prêt racine, les origines de stockage, le niveau
de référence, la promotion mutable, les conflits à la création, la durée de vie
de la liaison intermédiaire et la précision du résumé de source. Les oracles
restent inchangés dans les copies mutées. Aucun taux général n’est extrapolé.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_pool_aliases test_async_pool_alias_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_pool_alias_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_pool_alias_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_local_pool_mutations.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
```

## Limites

Ce lot couvre Pool<Int>, Pool<String>, Pool<Vector<Int>> et Pool<Vector<u8>>.
Il ne généralise pas les signatures async aux agrégats utilisateur, ne fournit
pas une preuve de tous les ordonnancements et ne termine pas les règles du
scheduler, de Select ou des gardes. Les régions annotées dans les corps async
sont traitées dans le [cycle suivant](ASYNC_REGIONS_CYCLE.md). Les comptages de méthodes entre
campagnes se recouvrent et ne s’additionnent pas comme des scénarios indépendants.
