[English](ASYNC_POOL_INJECTION_CYCLE.md)

# Cycle — pools injectés dans les états async et natifs

Suivi : la création directe de String/Vector<Int/u8> est raccordée dans le
[cycle suivant](ASYNC_COLLECTION_CREATION_CYCLE.md). Les autres limites de
ce rapport restent ouvertes.

Suite de [SYNC_BOOL_CALLS_CYCLE.md](SYNC_BOOL_CALLS_CYCLE.md). Aucune règle
normative modifiée. Ce lot raccorde les prêts de pools aux contrats et aux
états ; il ne termine pas l’ensemble des sept brouillons.

## Périmètre implémenté

- Captures `&Pool<T>` et `&mut Pool<T>` pour Int, String, Vector<Int> et
  Vector<u8>. L’ABI transporte un `Source*`, distinct d’une allocation.
- Réservation dès la création de la tâche, conservée pendant son exécution
  et jusqu’à son attente ; libération après join ou destruction inactive.
  Une allocation retournée conserve sa dépendance au pool sans conserver
  automatiquement le prêt exclusif de la tâche.
- Appels synchrones par contrats, fabriques retournant une tâche ou un
  handle, appels enfants, captures explicites dans les blocs natifs et
  union des provenances possibles du résultat.
- Création directe d’Int depuis le pool injecté ; remplacement après
  évaluation, retour, yield, break et continue avec nettoyage et réemploi.
  String et Vector passent actuellement par une fabrique synchrone.
- Emprunts de pools nommés, annotations correspondantes, dernier usage,
  coexistence des prêts partagés et refus d’une promotion en mutable.

Les marqueurs statiques de capture de pool ne sont pas inscrits comme des
allocations à détruire. Le code des bridges ne ferme pas le pool injecté.
L’ordre des arguments protège un pool préparé pendant l’évaluation des
arguments suivants, y compris à travers une suspension.

## Contre-exemples et limites rencontrées

Le cas valide `validation/open-async-pool-helper.crust`, auparavant refusé,
est maintenant couvert. Les premiers passages ont révélé le suivi manquant
des alias nommés de sources dans les effets et leur annotation non reconnue.
Ces raccordements sont corrigés. Une création explicitement typée String
depuis un Pool<Int> pouvait être traitée comme Int par le nouveau chemin
direct : elle est désormais refusée, avec deux tests et une mutation dédiés.

Deux limitations préexistantes ont été conservées explicitement dans les
fixtures : un retour propriétaire calculé d’un helper synchrone passe par
un receveur nommé ; l’observation d’adresse depuis un état passe par un
helper synchrone. Les journaux intermédiaires en échec ne sont pas présentés
comme des réussites finales.

## Preuves exécutées

Clang C11, pthread, O0/O2, warnings bloquants et UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`).

| Passage | Résultat | Journal |
| --- | --- | --- |
| Module final O0 | 19 méthodes, 11,501 s, OK | [O0](../../validation/async-pool-current-o0.log) |
| Baseline finale O2 | 19 méthodes, 16,631 s, OK ; 28 exécutions C, 36 refus, une vérification seule | [Baseline et mutations](../../validation/async-pool-final-mutations-o2.log) |
| Régression native/runtime O2 | 162 méthodes, 177,235 s, OK | [Régression](../../validation/async-pool-regression-o2.log) |
| Contrats O2 | 153 méthodes, 66,997 s, OK | [Contrats](../../validation/async-pool-contracts-o2.log) |

Les deux régressions élargies précèdent le dernier garde de type nominal ;
la régression native précède aussi l’ajout du test de boucle supplémentaire.
Les passages ciblés finaux incluent ces compléments. Ces sélections ne sont
pas la suite complète du projet.

Les oracles fixent les valeurs, les destructions uniques, l’identité avant
et après yield/join et le réemploi du même slot. Deux pools candidats testent
la précision des dépendances ; une source non retournée peut se fermer.
L’échec de lancement EAGAIN n’exécute pas le corps et rend les captures.
Les modèles existants des exigences de pools et provenances sont rejoués
dans les contrats. Aucun nouveau modèle général du scheduler n’est ajouté.
L’artefact [Crust](../../validation/async-pool-identity.crb), son
[C généré](../../validation/async-pool-identity.c) et sa
[trace](../../validation/async-pool-artifact-run.log) conservent l’observation
d’identité et de destruction.

Sept fautes injectées dans des copies temporaires sont détectées par les
tests inchangés : effacement du type nominal, oubli de réservation côté
appelant, oubli du prêt nommé, conversion d’un prêt partagé en mutable,
oubli du prêt de l’enfant, oubli de la provenance fraîche du résultat et
réutilisation du nom transféré à un bloc natif. Les échecs affichés après
la baseline dans le journal sont les détections attendues des mutants.
Aucun taux général de détection n’en est déduit.

## Travail restant

Création de pools locaux dans les états, création directe de String/Vector
dans ces états, pools de structures/enums, captures et signatures générales
d’agrégats restent à raccorder. Le placement implicite général, l’API
publique du scheduler, Select et les autres obligations des brouillons
restent ouverts. Aucun résultat ASan, TSan, second compilateur ou preuve
formelle n’est ajouté par ce cycle. Les tests ne prouvent pas la sûreté
générale du langage ni toutes les exécutions concurrentes.
