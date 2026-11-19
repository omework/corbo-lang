[English](ASYNC_BORROWED_STRUCT_POOLS_CYCLE.md)

# Pools async de structures contenant des emprunts

## Périmètre

Ce lot applique ST1–ST4, ST6–ST14, T1/T6, B1/B2/B4a, D1, L1/L2 et
AS2/AS8–AS14 aux structures Int/&Int/&mut Int prises en charge par le layout
existant. Aucune règle normative n'est modifiée. Les pools locaux/injectés et
les constructeurs nommés sont raccordés ; les captures propriétaires générales
de ces structures et leurs retours entiers restent ouverts.

## Implémentation et invariants

Les champs empruntés utilisent des descripteurs Cell sans posséder la cible.
Leur provenance suit le porteur lors des transferts, des branches, des sorties
de boucle et des remplacements. Les arguments déjà évalués restent réservés
pendant une suspension d'un argument suivant. Les contrats des auxiliaires
synchrones et enfants async mettent à jour les cibles stockées.

Une référence partagée extraite du porteur conserve sa cible indépendamment du
porteur. Un réemprunt mutable conserve aussi la réservation de la capacité du
champ. Le retour partagé via un auxiliaire utilise le contrat de terminaison
complet, notamment lorsque le porteur était local et a déjà été détruit.
Aucune cible locale n'est promue.

La fin des prêts stockés au dernier usage prend en compte les emprunts encore
actifs du porteur, y compris ceux détenus par une tâche ou un handle lancé.
Les chemins disjoints restent distincts. Le retrait des dépendances expirées
est calculé jusqu'à stabilisation.

## Contre-exemple corrigé

`validation/rejected-async-local-view-task-target.crust` crée une View contenant
&n, puis une tâche qui emprunte la View. Une version intermédiaire acceptait
`drop(->n)` avant l'attente de cette tâche : le porteur n'avait plus d'usage
lexical direct, mais restait emprunté. Les deux étapes acceptaient le programme
invalide ; il n'a pas été exécuté. Le journal
`validation/async-borrowed-struct-pools-task-counterexample.log` conserve ce constat.

La correction conserve les cibles stockées tant qu'un prêt actif recouvre le
champ du porteur. Le test déterministe vérifie le refus avec tâche, handle lancé
et alias, ainsi que les voisins admis après attente ou dernier usage d'alias.
La mutation qui ignore les prêts du porteur est détectée.

## Preuves exécutées

- Suite ciblée finale O0 : 15 méthodes réussies, 22,937 s ; 28 exécutions
  natives, 31 programmes invalides refusés aux deux étapes, soit 62 contrôles.
  Journal : `validation/async-borrowed-struct-pools-counted-o0.log`.
- Baseline finale O2 : 15 méthodes réussies, 23,547 s. Dix mutations détectées,
  aucune survivante ou inconclusive. Les échecs affichés après chaque mutant
  sont les détections attendues, pas des échecs de baseline.
  Journal : `validation/async-borrowed-struct-pools-final-mutations-o2.log`.
- Régression finale O2 : 153 méthodes réussies, 163,356 s.
  Journal : `validation/async-borrowed-struct-pools-final-regression-o2.log`.

Les trois processus sont terminés avec code 0. Les exécutions C utilisent
Clang C11/pthread, Wall/Wextra/Werror, Wno-unused-function, UBSan fatal et
O0/O2 selon la campagne. Aucune nouvelle preuve ASan/TSan.

Le modèle fini de boucle compare les résultats pour 0, 1 et 3 itérations.
Les sondes natives contrôlent le nettoyage pendant suspension et le remplacement
d'un receveur parent. Ce n'est pas un modèle indépendant complet du vérificateur.
Les mutations visent la destruction de la cible empruntée, le transport/perte
ou maintien excessif des dépendances, la réservation mutable, les arguments
préparés, les prêts du porteur et l'origine des résultats. Les oracles restent
inchangés dans les copies temporaires ; ces dix détections n'établissent pas
un taux général de couverture.

## Chronologie et limites

Les journaux intermédiaires sont conservés. Le premier passage avait six échecs
pour huit méthodes : diagnostics de fixtures, notation de réemprunt et prêt
conservé au-delà du dernier usage. Le passage `returns-o0` a exposé le refus
indu du retour partagé via une structure locale, corrigé par le contrat complet.
La première campagne de mutation a été interrompue par une ancre non unique,
rendue unique avant la campagne finale. Une régression intermédiaire comportait
79 succès et une erreur d'import de module ; la commande finale corrige ce nom.
La fixture d'alias nécessitait le raccordement des emprunts nommés de porteurs.

Les deux sondes synchrones/async du journal `field-last-use-probe` refusent
conservativement de détruire la cible d'un champ si un champ frère est utilisé
ensuite. Aucune nouvelle sémantique de précision par champ n'est inventée ici.
Les graphes mixtes, les autres types empruntés, les retours locaux de graphes et
les captures propriétaires générales de structures empruntantes restent ouverts.
Les décisions relatives aux handles lancés ne sont pas modifiées.
`reset()` reste retiré du prototype, sans nouvel essai de cette API historique.

Snapshot : `/tmp/crust-before-async-borrowed-struct-pools`.
Diffs : `validation/async-borrowed-struct-pools-*.py.patch`.
L'objectif complet reste actif ; aucune preuve générale de sûreté n'est revendiquée.
