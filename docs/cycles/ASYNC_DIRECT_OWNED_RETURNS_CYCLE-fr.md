[English](ASYNC_DIRECT_OWNED_RETURNS_CYCLE.md)

# Retours directs d'allocations attendues

## Règles et défaut reproduit

Ce lot applique T1/T6, D1/T11, V5, L1/L2, AS4/AS8/AS10/AS12 et SL1.
Aucune règle normative n'est modifiée. Le programme
[open-direct-awaited-allocation-return.crust](../../validation/open-direct-awaited-allocation-return.crb)
était refusé par verify_program et compile_source à `return <-leaf(p).await;`,
malgré le marqueur explicite. Les diagnostics sont conservés dans
[le journal initial](../../validation/direct-awaited-allocation-return-baseline.log).

Une tâche inactive rend directement son type de résultat. Un handle lancé
rend un Result : cette différence doit rester visible dans le type, y compris
sans variable intermédiaire. Retourner une allocation ne prolonge pas son pool.

## Implémentation

Le retour propriétaire explicite utilise désormais le traitement commun des
expressions propriétaires. Celui-ci reconnaît aussi l'attente d'une tâche
calculée, puis vérifie le type exact du résultat. Les sources durables sont
contrôlées avant l'export ; le nettoyage du scope n'inclut pas l'allocation
transférée. Les champs de l'état et de l'allocation ne sont pas déplacés.
Les retours nommés conservent leur comportement antérieur.

Le même chemin accepte maintenant une allocation produite par l'attente d'une
tâche calculée comme argument transféré, avec conservation du nettoyage pendant
l'évaluation des arguments suivants. Les attentes de handles dans ce contexte
restent refusées : elles produisent un Result, pas un A<T> direct.

## Scénarios et preuves

`tests/test_async_direct_owned_returns.py` exerce les quatre familles A<Int>,
A<String>, A<Vector<Int>> et A<Vector<u8>>. Pour chacune : attente directe,
tâche nommée, tâche rendue par un bloc et branche conditionnelle propriétaire.
Les sorties sont observées et le pool à un slot est réutilisé après destruction.
Un échec de lancement injecté n'exécute pas le corps de la tâche.

Les voisins refusés omettent la flèche, rendent une allocation d'un pool local
trop court, confondent le résultat du handle et celui de la tâche, ou changent
le type de l'allocation. Le transfert d'une allocation calculée vers un appel
synchrone ou async est aussi interrompu par un return dans l'argument suivant,
après suspension : l'appel n'a pas lieu et le résultat préparé est détruit.

Le retour d'un résultat de Select conserve sa charge gagnante et nettoie
la sélection. Le cas ordonné testé rend 7 et ne construit pas la charge 9
de la perdante. Les deux pools restent réutilisables ensuite.

Deux sondes C possèdent exclusivement une racine non lancée. La première
la détruit au premier point de suspension et observe une destruction unique
de l'allocation détenue par l'enfant. La seconde poursuit jusqu'à la remise
du résultat et vérifie que l'adresse obtenue est celle d'entrée. Après drop,
le même slot peut être réutilisé. Ces sondes n'introduisent pas d'annulation
publique d'une tâche lancée.

## Exécutions

Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function, UBSan fatal.

- `validation/direct-awaited-allocation-initial-o0.log` : six méthodes,
  16,060 s, OK sur le code du lot.

- `validation/direct-awaited-allocation-mutations-o2.log` : baseline finale
  de six méthodes, 21,993 s, OK ; trois fautes injectées détectées (refus du
  retour valide, destruction prématurée de l'allocation retournée, oubli du
  nettoyage de l'enfant suspendu). Campagne terminée avec code 0, aucune
  survivante ni non concluante dans cet échantillon.

- `validation/direct-awaited-allocation-regression-o2.log` : 44 méthodes,
  102,279 s, OK sur le code final. Les résultats Select, les appels synchrones
  propriétaires, les nettoyages suspendus et l'ensemble du lot des Result
  produits par await sont rejoués ensemble.

Tous ces processus sont terminés avec code 0. Les modules modifiés et les
nouveaux tests/runners passent py_compile. Les liens des rapports ont été
contrôlés. Le patch est conservé dans
[async_lowering-direct-awaited-allocation.patch](../../validation/async_lowering-direct-awaited-allocation.patch).

## Limites

Les quatre familles et les formes syntaxiques testées ne couvrent pas tous
les agrégats propriétaires. Les sondes d'identité et de destruction portent
sur des chemins finis, sans preuve générale de sûreté ni résultat ASan/TSan.
Le runtime de scheduling n'a pas été modifié. Les arbitrages de handles
possédés par des tâches inactives et des perdantes Select restent ouverts.
L'objectif global n'est pas terminé.
