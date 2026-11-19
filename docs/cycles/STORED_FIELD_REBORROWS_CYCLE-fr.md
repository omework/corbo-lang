[English](STORED_FIELD_REBORROWS_CYCLE.md)

# Cycle — stockage des réemprunts de champs mutables

## Règles et corrections

Application de ST4, ST8, ST11–ST14, B1–B5, D1, AS12/AS13 et MT3.
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des brouillons sont relus ;
les règles retenues ne changent pas. Les sept brouillons restent partiellement
implémentés et l’objectif global reste ouvert.

Le programme conservé dans
`validation/open-struct-field-reborrow-stored-shared.crust` s’exécute maintenant.
Le porteur View contient un emprunt partagé obtenu à travers la capacité
mutable d’un Writer. Détruire View après join n’invalide pas le résultat ;
détruire Writer ou sa cible avant le dernier usage reste refusé.

Un réemprunt d’un champ `&mut Int` conserve désormais la représentation de
sa véritable allocation (`Cell *`), comme les autres références d’allocations.
Les champs Int contenus directement utilisent toujours un pointeur de contenu
(`int *`). Les contrats et les résultats de join maintiennent cette distinction,
y compris après un helper, une méthode, une fabrique ou un handle reçu en paramètre.
Les résultats mélangeant champs directs et indirects conservent leur
représentation commune de pointeurs de contenu et l’union de leurs réservations.

La réservation de champ est conservée dans la chaîne des captures. Les
projections typées à travers un enum comptent une capacité dérivée une seule
fois ; leur porteur, le champ et la cible restent protégés. Les contrats des
structures retournées résolvent aussi les origines de champs indirects.
Le passage de typage des blocs natifs déduit le type d’un `pool.new` nommé
depuis son pool, au lieu de produire un type None et une exception Python.

Le runtime C n’est pas modifié. Le C du contre-exemple corrigé est conservé
dans `validation/stored-field-reborrow-fixed.c`. Les diffs du compilateur,
de l’analyse des résultats et du passage natif sont dans
`validation/stored-field-reborrows-*.py.patch`.

## Scénarios et modèle

`test_stored_field_reborrows` couvre les références partagées et mutables
stockées depuis un champ, les alias nommés, les helpers/méthodes, les relais,
la fabrique d’un porteur, sa copie, son retour async ou natif, la destruction
et le réemploi du slot original après le dernier usage. Les voisins invalides
modifient/détruisent le porteur d’origine ou sa cible trop tôt, ou exportent
une référence liée à un porteur local. Deux refus de reset emploient uniquement
le profil historique. Le lancement refusé injecté vérifie le même nettoyage
unique que le chemin normal : View, Writer, puis Int.

Le modèle `test_stored_field_reborrow_model` maintient un graphe logique
résultat → capacité du champ Writer → cible, sans consulter les objets du
compilateur. Il examine seize combinaisons : accès indépendant ou invalidant,
avant/après dernier usage, avec/sans helper. Dix programmes s’exécutent et six
sont refusés aux deux entrées. Les trois modèles précédents des champs et du
détachement sont également rejoués.

## Preuves exécutées

Les journaux ci-dessous sont dans `validation/`.

- `stored-field-reborrows-complete-final-o0.log` : neuf méthodes,
  12,669 s, OK, avec le modèle indépendant.
- `stored-field-reborrows-complete-mutations-o2.log` : baseline finale de
  huit méthodes, 8,525 s, OK ; quatorze exécutions C, dont un lancement refusé
  injecté, et 28 programmes invalides vérifiés aux deux entrées (56 contrôles).
  Six fautes injectées détectées.
- `stored-field-reborrows-models-o2.log` : neuf méthodes, 22,323 s, OK,
  avant les derniers compléments de fabrique/copie/réemploi ; trois modèles
  antérieurs (24, 24 et 12 combinaisons) et les six méthodes initiales du lot.
- `stored-field-reborrows-final-model-o2.log` : deux méthodes, 4,511 s, OK ;
  nouveau modèle et projection typée à travers un enum.
- `stored-field-reborrows-relays-o2.log` : 35 méthodes, 24,486 s, OK ;
  retours de champs, contrats mixtes et références détachées.
- `stored-field-reborrows-fields-resolved.log` : 76 méthodes, 48,200 s,
  75 réussites et un diagnostic de fixture historique corrigé ensuite.
  `stored-field-reborrows-historical-last.log` : cette méthode réussit,
  1,596 s. Le journal des 76 méthodes reste présenté avec son échec.
- `stored-field-reborrows-helper-mutations-final-o2.log` : baseline de huit
  méthodes, 4,140 s, OK ; dix exécutions C, seize refus aux deux entrées,
  six mutations détectées, y compris la classification du résultat inline
  à travers le handle reçu en paramètre.

La régression native élargie `stored-field-reborrows-native-o2.log` termine
avec 297 méthodes réussies en 226,611 s. Elle a démarré avant le raccordement
du contrat de porteur retourné et les
derniers tests de copie, réemploi, lancement refusé et résultat inline de
handle. Ces compléments sont couverts par les passages ciblés finaux.

Les nouveaux harnais emploient Clang C11/pthread, avertissements fatals,
UBSan fatal et O0/O2. Les tests historiques de `test_foundation_rules`
n’ajoutent pas d’option d’optimisation explicite, même dans un journal nommé O2.
Aucun nouveau passage ASan/TSan, second compilateur ou résultat de performance.

## Mutations et contre-exemples intermédiaires

Les six mutations ciblées retirent la représentation de référence d’allocation,
altèrent la classification du résultat de helper, omettent la réservation du
champ ou son ascendance au join, rétablissent le refus des captures projetées,
ou omettent l’origine du champ dans le porteur retourné. Toutes sont détectées,
notamment par le refus de programmes valides. Ce n’est pas un taux universel
de détection. L’omission d’ascendance, survivante au lot précédent, est détectée
par le nouveau programme qui possède un porteur mutable extérieur distinct.

La campagne antérieure des retours de champs conserve sept mutations détectées
et une survivante (`join_target_capability_omitted`) : son contrôle modifié
concerne désormais la représentation des résultats mixtes et le test sélectionné
n’établit pas son équivalence générale. Journal
`stored-field-reborrows-return-mutations-o2.log`.
La première reprise des mutations de helpers détecte cinq fautes et laisse
survivre l’ancienne mutation de classification : le cas choisi ne comportait
plus de résultat inline. Un voisin retournant un champ direct via un handle
reçu a été ajouté et l’ancre adaptée au nouveau contrôle des projections.

Les journaux initiaux restent conservés :

- `initial` puis `capture` : refus de capture projetée, corrigé après raccordement
  de la référence stockée ; le programme initial affiche ensuite 7 puis 7.
- `helper-probe` : classification de résultat encore incompatible avec le champ,
  corrigée dans l’analyse et les contrats.
- `canonical-contracts-o2` : trois erreurs et deux échecs ont exposé les unions
  inline/indirectes, l’exclusivité du parent mutable et le relais d’un handle.
  Les corrections conservent les tests existants.
- `canonical-o0` : le premier snippet de thread avait une capture non conforme,
  puis le passage natif a révélé le type None d’un constructeur en pool. La
  capture nommée explicite et l’inférence du type sont corrigées.
- `container-relay-o2` : cible absente du contrat du porteur retourné ; le
  raccordement des origines indirectes corrige ce refus.
- `nested-probe` : double comptage d’une capacité à travers un enum ; corrigé
  sans supprimer la réservation de cet enum ou de sa cible.

Les cinq échecs historiques de diagnostics ont été reproduits sur les snapshots
précédant ce lot (`stored-field-reborrows-historical-baseline.log`). Des variantes
invalides avaient supprimé le seul usage d’une allocation et déclenchaient U1
avant le contrôle mémoire voulu. Des lectures explicites ont été ajoutées à
ces seules variantes ; leurs attentes de refus mémoire restent inchangées.

## Limites

Ce lot ne généralise pas le stockage de références vers des cases inline de
tableaux/structures ni tous les graphes d’agrégats. Les modifications de
dépendances de champs depuis les états async restent ouvertes. Les modèles
sont finis et les ordonnancements ne sont pas exhaustifs. Le runtime public
complet, Select, les gardes de mutex et le placement général restent à réaliser.
