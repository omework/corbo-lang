[English](ASYNC_FIELD_REBORROWS_CYCLE.md)

# Réemprunts de champs dans les états async

Suite : le retour de ces projections depuis une fonction async est désormais
raccordé dans [ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md).
Le refus décrit ci-dessous est conservé comme constat historique.

Cycle du 7 novembre 2026. Application de ST6–ST9, ST11–ST12, B1/B2/B4a,
V4, AS2/AS8/AS12/AS13 ; aucune règle normative modifiée.

Les projections Int et les réemprunts explicites de champs &Int/&mut Int
conservent leurs chemins dans l'état, les arguments et les enfants async.
Les résultats projetés d'auxiliaires synchrones et de méthodes conservent
ces réservations. Les champs disjoints restent accessibles. L'export d'un
alias garde les cibles durables, sans exiger la survie de sa liaison locale.
Une vraie cible locale reste refusée.

V4 a également révélé une restriction injustifiée : une liaison `let` contenant
un &mut peut modifier sa cible. Seule la réaffectation de la liaison demande
`let mut`. Les tests historiques concernés ont été corrigés selon cette règle.

## Résultats exécutés

- `async-field-reborrows-complete-o0.log` : 13 méthodes, 29,970 s, OK.
- `async-field-reborrows-complete-o2.log` : 13 méthodes, 18,158 s, OK,
  avant l'ajout des deux arguments directs helper/méthode.
- `async-field-reborrows-method-argument-o2.log` : complément, une méthode,
  3,072 s, OK.
- `async-field-reborrows-final-mutations-o2.log` : baseline finale de 12 méthodes,
  17,504 s, OK ; 21 exécutions C et 29 programmes invalides contrôlés par
  les deux entrées (58 contrôles). Sept fautes injectées détectées : réservation
  du porteur entier, perte d'ascendance, suppression du conflit, perte du chemin
  du helper, perte du résultat enfant, offset incorrect, restriction V4 restaurée.
  Certaines détections sont des refus injustifiés, pas des violations mémoire.
- Modèle indépendant : 32 combinaisons de champs, alias, opérations et derniers
  usages, dont 24 exécutions C et huit refus attendus. Attentes calculées sans
  reprendre les décisions du compilateur.
- `async-field-reborrows-native-o2.log` : 256 méthodes, 209,022 s, OK.
- `async-field-reborrows-contracts-o2.log` : 76 méthodes, 82,161 s, OK.
- `async-field-reborrows-struct-mutations-o2.log` : six mutations antérieures
  rejouées et détectées.

Les deux régressions élargies ont été lancées avant le dernier élargissement
des arguments de méthodes ; le complément ciblé et les mutations finales
couvrent ce changement. Clang C11 pthread, UBSan fatal, O0/O2 selon le journal.
Aucun nouveau résultat ASan/TSan ou second compilateur ; aucune preuve formelle.

## Échecs conservés et limites

`async-field-reborrows-initial-o0.log` conserve deux erreurs corrigées :
export d'alias et restriction V4. `async-field-reborrows-targeted-o0.log`
conserve deux échecs de fixture (helper absent), corrigés puis revérifiés
dans `async-field-reborrows-fixture-recheck-o0.log` : deux méthodes, OK.

Le programme `validation/open-async-field-reference-return.crust` reste
valide mais refusé : le retour d'une projection depuis la fonction async
elle-même n'est pas encore raccordé au contrat de l'appelant. Les remplacements
de champs références et les graphes généraux restent ouverts. Ce cycle
ne clôt pas les sept brouillons ni l'objectif global.

Les journaux sont sous `validation/`. Le diff d'implémentation est conservé
dans `validation/async-field-reborrows-async_lowering.patch`.
