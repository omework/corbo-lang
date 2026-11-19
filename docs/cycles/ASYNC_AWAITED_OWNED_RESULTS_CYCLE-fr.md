[English](ASYNC_AWAITED_OWNED_RESULTS_CYCLE.md)

# Résultats propriétaires produits directement par await

## Périmètre et règles

Ce lot applique U1, T1/T2/T6, B4a, D1/T11, L1/L2/L6 et
AS2/AS4/AS8/AS10/AS12 aux expressions qui produisent un Result propriétaire
par attente. Les décisions normatives ne changent pas : une tâche inactive
rend T, un handle lancé rend Result<T,runtime::Error>, et les transferts
restent explicites. Les brouillons 01, 04 et 07 sont concernés.

Les types exercés sont A<Int>, A<String>, A<Vector<Int>> et A<Vector<u8>>,
ainsi que deux niveaux de Result propriétaires. Les formes comprennent un
handle nommé, un lancement direct, une tâche nommée, un appel async direct
et une expression bloc retournant une tâche ou un handle.

## Contre-exemples et correction

Le programme minimal est
[open-awaited-owned-result-argument.crust](../../validation/open-awaited-owned-result-argument.crb).
Avant correction, `relay(->h.await)` était refusé par verify_program et
compile_source avec « transfert -> explicite requis ». Un retour
`return <-h.await;` était également refusé avec « <- explicite requis ».
Les marqueurs étaient pourtant présents. Les résultats initiaux sont dans
[le journal de reproduction](../../validation/awaited-owned-results-baseline.log).

Le backend emploie maintenant un traitement commun des expressions Result
propriétaires pour les arguments synchrones, les captures async et les retours.
Il réutilise les chemins d'attente existants, conserve le type de la charge et
les sources du stockage, puis laisse au receveur le nettoyage. Le match direct
d'une attente de tâche retournant un Result est aussi raccordé, y compris
lorsque la tâche provient d'une expression bloc. Les valeurs préparées avant
un argument suspendu restent enregistrées pour les sorties anticipées et les
destructions aux points de suspension.

Le changement n'ajoute aucune attente cachée ni annulation publique. Pour
un retour nommé, les règles existantes de fermeture des scopes sont conservées ;
le transfert descendant vers un appel exige toujours le rattachement local.

## Vérification et oracles

Le module `tests/test_async_awaited_owned_results.py` vérifie :

- les quatre familles, les six formes d'attente, les valeurs observées et le
  réemploi d'un pool à un slot ;
- l'absence de flèche, la seconde attente du handle, le motif propriétaire `_`,
  les types incompatibles et le retour depuis un pool trop court ;
- le retour direct, le match direct et le transfert à un appel async ;
- le nettoyage d'un premier argument quand le suivant suspend puis quitte la
  fonction, avant même la création ou l'appel du receveur ;
- les erreurs injectées aux différents niveaux de Result, sans résultat réussi
  fictif et sans double destruction ;
- le nettoyage d'une branche Select perdante avec un Result préparé.

Un modèle fini séparé distingue trois détenteurs successifs : l'enfant direct,
les arguments préparés, puis le receveur async. Pour chaque suspension possible
et pour Ok/Err, il prédit une destruction de la charge présente ou aucune charge.
Dix sondes C exercent ces étapes, la restitution du slot, l'identité au réemploi
et le refus d'une seconde destruction. Elles possèdent exclusivement une racine
non lancée ; elles ne détruisent pas une tâche concurrente en cours.

Les programmes source traversent le parseur, le vérificateur et le générateur C.
Les sondes C servent uniquement à inspecter les points de suspension et leur
nettoyage. Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan
fatal sont employés, à O0 et O2 selon les passages.

## Résultats exécutés

- `validation/awaited-owned-results-initial-o0.log` : six méthodes, 39,670 s, OK.
  Ce passage précède l'élargissement des tests et le maintien explicite du
  comportement de retour nommé à travers les scopes.
- `validation/awaited-owned-results-cleanup-o2.log` : deux méthodes, 10,168 s,
  OK ; erreurs imbriquées et dix sondes de destruction suspendue.
- `validation/awaited-owned-results-select-o2.log` : une méthode, 1,255 s, OK ;
  deux exécutions Select avec charge présente ou refus de lancement de l'enfant.

- `validation/awaited-owned-results-final-o0.log` : neuf méthodes, 64,613 s,
  OK sur le code final ; instrumentation du harnais : 110 exécutions natives
  et 17 programmes invalides vérifiés par les deux stages (34 contrôles).

- `validation/awaited-owned-results-regression-o2.log` : 96 méthodes,
  111,724 s, OK sur le code final. Sélection : résultats sans charge,
  nettoyages aux suspensions, résultats Select, Select source, appels
  synchrones propriétaires et effets de structures async.

- `validation/awaited-owned-results-mutations-o2.log` : baseline finale de
  neuf méthodes, 64,482 s, OK ; cinq fautes injectées détectées : refus de
  l'attente valide, oubli d'un argument préparé synchrone, oubli d'une capture
  préparée async, omission des arguments lors de la destruction suspendue,
  destruction prématurée de la charge retournée. Cette dernière provoque
  notamment un diagnostic UBSan fatal dans le mutant.
- `validation/awaited-owned-results-previous-mutations-o2.log` : baseline
  précédente de douze méthodes, 35,063 s, OK ; les huit mutations du lot
  des résultats sans charge restent détectées.

Les deux campagnes se terminent avec le code 0, sans mutation survivante ni
non concluante parmi ces treize fautes choisies. Aucun processus de ce lot ne
reste en cours. Les modules modifiés et les nouveaux tests/runners passent
py_compile. La suite runtime complète du cycle précédent n'a pas été
relancée : le présent changement de traduction est exercé par les programmes
natifs et la sélection de régression ci-dessus.

## Limites

Le sous-ensemble de charges et les deux niveaux de Result ci-dessus ne couvrent
pas les signatures et conteneurs généraux. Les diagnostics et contrats restent
conservateurs. Le modèle fini de nettoyage n'est pas un modèle général de
l'ordonnancement. Aucun nouveau résultat ASan/TSan ni preuve de sûreté générale
n'est revendiqué. Les arbitrages de handles capturés par une tâche inactive ou
conservés par une perdante Select restent distincts et ouverts.

Le patch est conservé dans
[async_lowering-awaited-owned-results.patch](../../validation/async_lowering-awaited-owned-results.patch).
L'objectif global reste en cours.

La recherche du lot suivant a aussi reproduit le refus de
`return <-leaf(p).await` lorsque leaf rend directement A<Int>, sans enveloppe
Result. Le programme et les deux diagnostics sont conservés dans
`validation/open-direct-awaited-allocation-return.crust` et
`validation/direct-awaited-allocation-return-baseline.log`. Le raccordement
est traité séparément dans le
[cycle des retours directs d'allocations](ASYNC_DIRECT_OWNED_RETURNS_CYCLE.md),
avec ses propres preuves et limites.
