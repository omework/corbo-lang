[English](ASYNC_OWNED_STRUCT_RETURNS_CYCLE.md)

# Retours async de structures propriétaires

## Règles et périmètre

Ce lot applique les règles existantes T1/T6, D1/T11, B1/B2/B4, ST1/ST7/ST15,
L1/L2/L6 et AS5/AS8/AS9/AS10/AS12/AS13. Les brouillons 01, 03, 04 et 05 sont
concernés. Aucune règle normative n'est modifiée.

Une tâche peut rendre une structure propriétaire reçue par transfert, y compris
un graphe fini de champs A<Int>, A<String>, A<Vector<Int/u8>> et de structures
de cette famille. Le retour conserve l'allocation et ses adresses. Le receveur
nettoie ensuite le graphe complet. Le même résultat peut traverser des attentes
successives, une fabrique, un relais de tâche, un Result retourné par une
fonction synchrone, un Result transmis à une tâche et une enveloppe imbriquée.

Les corps async ne construisent pas encore librement ces structures ni leurs
pools. Les graphes contenant des emprunts, les enums généraux, les signatures
publiques runtime::Handle<A<Structure>> et le passage des structures propriétaires
aux auxiliaires synchrones depuis async restent à raccorder. Ce lot ne ferme
pas le chantier général des agrégats.

## Défaut initial et implémentation

Le [programme minimal](../../validation/open-owned-async-struct-return.crb) était
refusé à la signature par les deux stages. Les diagnostics sont conservés dans
`validation/owned-async-struct-return-baseline.log`. Le runtime possédait déjà
la représentation et les destructeurs nécessaires ; le suivi statique du
résultat était incomplet.

Chaque tâche et handle conserve maintenant, séparément de ses captures, les
sources du résultat par chemin de champ. Les contrats exposent ces chemins et
les instancient lors des appels. Le vérificateur reconstruit le graphe possédé
après join et le conserve lors de l'extraction du Result, des retours de
fonctions et des jonctions if, match ou break. Le contrat de tâche et celui
des contraintes de sources conservent la même distinction entre racine et
descendants. Les origines concrètes sont conservées à la création et à la
remise ; les reconstructions symboliques utilisent les sources du contrat.

La syntaxe Result<A<T>,runtime::Error> est reconnue pour les types nominaux ;
les types inconnus sont refusés. L'élargissement ne permet pas de fabriquer
un résultat dont la provenance des champs est absente. Le backend conserve
ses restrictions explicites sur les graphes non pris en charge.

## Scénarios et oracles

Les douze méthodes de `tests/test_async_owned_struct_returns.py` exercent :

- retour normal, lancement refusé, absence du marqueur et type inconnu ;
- attente directe ou nommée avec lecture puis nouveau transfert ;
- fabriques, relais d'instances, choix conditionnel de tâches ;
- Result transmis à un helper, à un autre helper propriétaire, puis à une tâche,
  et deux niveaux de Result à l'attente ;
- sortie de Result par if et break, puis projection du champ possédé ;
- dernier usage d'un emprunt du champ avant drop, avec voisin refusé ;
- durée de vie du pool d'un champ indépendamment du pool de la racine.

Un modèle fini place chacun des trois pools du graphe Root → Child → Int dans
le scope extérieur ou dans le bloc produisant le Result. Les huit dispositions
doivent accepter uniquement celle où les trois pools survivent au résultat.
Il exerce donc un programme admis et sept refusés. Les refus ne sont pas exécutés.

Deux sondes C possèdent une tâche non lancée : destruction à sa suspension,
ou poursuite jusqu'à remise. Elles vérifient l'adresse de la racine et du champ,
une seule destruction de chacun, l'ordre enfant avant parent et le réemploi
des deux slots. Elles n'introduisent aucune annulation d'une exécution lancée.

Un oracle de contrat vérifie deux obligations de sources distinctes : le pool
fourni à un ancien reset doit être distinct de celui du résultat et de celui
de son champ `.value`. Ce test utilise expressément `allow_legacy_reset=True` ;
reset reste retiré du profil normal. L'attendu porte sur le contrat inféré,
indépendamment des chemins de contrôle du générateur C.

## Exécutions et corrections intermédiaires

Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function, UBSan fatal.

- `owned-async-struct-return-initial-o0.log` : quatre méthodes, une erreur
  d'attendu provenant d'un snippet sans receveur ni marqueur à la sortie du
  bloc externe. Le snippet est corrigé conformément à T1/T6, sans assouplissement.
- `owned-async-struct-return-second-o0.log` : quatre méthodes réussies.
- Les journaux `third-o0`, `fourth-o0`, `helper`, `fifth-o0` et `helper-second`
  conservent les refus rencontrés lors du raccordement : import descendant
  manquant dans le test de branche, marqueur de retour de Result manquant,
  signature nominale non reconnue, graphe et variante absents du contrat.
  Les deux premiers défauts sont dans les snippets, les suivants dans le
  compilateur. Les invocations `helper` et `fifth-o0` n'imposaient pas O0 ;
  leur suffixe ne constitue pas une preuve du niveau d'optimisation.
- `owned-async-struct-return-expanded-o0.log` : neuf méthodes, 5,181 s, OK.
- `owned-async-struct-return-contract-o0.log` : 18 méthodes, 11,913 s, OK,
  après raccordement de l'analyse des contraintes, captures antérieures incluses.
- `owned-async-struct-return-final-o0.log` : onze méthodes, 9,024 s, OK,
  avant le relais supplémentaire de Result et les jonctions if/break.
- `owned-async-struct-return-final-counted-o0.log` : douze méthodes,
  7,845 s, OK sur le code final ; 19 exécutions natives et onze programmes
  invalides refusés par les deux stages, soit 22 contrôles de refus.

`validation/owned-async-struct-return-mutations-final-o2.log` : baseline finale
de douze méthodes, 8,226 s, OK ; cinq fautes injectées détectées : confondre le
pool du champ avec celui de la racine, omettre le graphe à la remise, perdre
les champs dans les contrats de fabriques, détruire avant remise, omettre la
contrainte du champ. La mutation de pool admet à tort plusieurs cas du modèle,
que les assertions de refus détectent. Les fautes restent dans des copies
temporaires ; ni les oracles ni les règles ne sont modifiés.

Les cinq mutations des captures restent détectées :
`validation/owned-async-struct-return-previous-mutations-o2.log`, baseline de
neuf méthodes, 11,265 s. Ce passage précède le dernier complément de relais.

Régression élargie : `validation/owned-async-struct-return-regression-o2.log`,
86 méthodes, 115,948 s, OK. Sélection : captures/retours de structures,
contraintes, fabriques, retours directs, Result attendus et résultats Select.
Le code chargé précède le dernier raccordement du relais de Result propriétaire.

Régression sur le code final :
`validation/owned-async-struct-return-final-regression-o2.log`, 54 méthodes,
29,324 s, OK : captures, contraintes, règles d'usage des résultats propriétaires
et handles propriétaires publics déjà pris en charge. Les douze tests ciblés
finaux et les mutations finales couvrent le complément de relais et de jonctions.
Toutes les campagnes finales sont terminées avec code 0 ; les sélections se recouvrent.

## Limites

Les fichiers Python modifiés et les nouveaux tests passent `py_compile`.
Les diffs par rapport au début du lot sont conservés dans
`validation/owned-async-struct-return-*.py.patch`.
Les modèles et sondes sont finis et ne prouvent pas la sûreté générale du
langage. Aucun nouveau résultat ASan/TSan n'est revendiqué. Les types,
constructions et signatures encore ouverts ci-dessus restent à implémenter ;
les arbitrages de handles capturés et de perdantes Select ne sont pas modifiés.
