[English](PUBLIC_HANDLE_CONTRACTS_CYCLE.md)

# Contrats publics des handles

## Règles et périmètre

Le brouillon 04, AS2/AS13, RT5/RT7 et MT5 imposent un type public
`runtime::Handle<T>` indépendant de la frame, avec conservation des captures,
des sources de stockage et de l'obligation d'attente. Aucune règle normative
n'est modifiée par ce lot.

Les paramètres transférés et retours transférés des fonctions synchrones
acceptent maintenant ce type pour les résultats scalaires pris en charge
et les tableaux fixes Int/u8, y compris imbriqués. Deux fonctions async de
frames différentes peuvent utiliser le même auxiliaire. Les signatures
historiques `Execution<fonction>` restent compatibles. Le programme conservé
dans `validation/open-public-handle.crust` s'exécute et affiche 7 puis 9.

Les contrats regroupent les captures partagées, exclusives et les réemprunts
partagés issus d'une capacité exclusive. Leurs cibles et leurs pools ne sont
pas déduits de T. Les descripteurs de contrats ne génèrent pas de pool ou
de frame supplémentaire. Le C conserve sa représentation CrustExecution.

## Défauts trouvés et corrigés

- Un appelant ne possédant que les contrats, sans catalogue de corps async,
  perdait la protection de captures mutables. Des gardes conditionnées par
  la présence de définitions désactivaient ces prêts. Elles ont été retirées.
  Reproduction : `validation/public-handle-contracts-opaque-o2.log` ;
  correction : `validation/public-handle-contracts-opaque-fixed-o2.log`.
- Un réemprunt partagé de Vector créé depuis un paramètre mutable devenait
  entièrement exclusif après passage au type public. Une lecture partagée
  valide était refusée. Le contrat conserve désormais séparément la capacité
  ancêtre réservée et le mode partagé exposé. Reproduction :
  `validation/public-handle-contracts-opacity-o2.log` ; contrôle corrigé :
  `validation/public-handle-contracts-shared-capability-o2.log`.
- Les ensembles vides de captures/sources d'un handle public ne sont pas
  remplacés par une provenance locale fictive.

## Validation exécutée avant le complément sur les jonctions

Clang C11 avec pthread, avertissements fatals et UBSan fatal, O0/O2.
Les 17 méthodes de `tests/test_public_handle_contracts.py` passent :

- O2, 15,508 s : `validation/public-handle-contracts-arrays-fixed-o2.log`.
- O0, 26,018 s : `validation/public-handle-contracts-arrays-final-o0.log`.
- Régression de 54 méthodes, 42,951 s :
  `validation/public-handle-contracts-arrays-regression-o2.log` ; contrats,
  annotations locales, appels opaques et tableaux async préexistants.

Ces essais incluent les fabriques et relais, les captures partagées et
mutables, les pools injectés et captures propriétaires, le réemploi après
attente, le refus de lancement avec nettoyage unique, les résultats Bool/u8/
Void, les tableaux Int/u8 et imbriqués, les mauvais types de résultat même
quand le destinataire ignore la charge, ainsi que l'abandon interdit du handle.
Les programmes invalides sont contrôlés à verify_program et compile_source.

Un modèle indépendant combine deux cibles avec trois permissions chacune
(absente, partagée, mutable), puis lecture ou écriture sur l'une des cibles :
36 scénarios, dont 18 exécutés en C et 18 refusés aux deux entrées. L'oracle
utilise la table des permissions, pas les contrats produits par le compilateur.
Les appelants opaques sont construits sans corps ni cartes d'inférence.

Sept fautes injectées dans des copies temporaires sont détectées : perte
d'exclusivité, exclusivité excessive, perte de la distinction du réemprunt
partagé, effacement de source, désactivation des prêts sans corps, absence
de contrôle de charge scalaire et absence de contrôle de forme des tableaux.
Journal : `validation/public-handle-contracts-arrays-mutations-o2.log`.

La mutation d'effacement de source survivait initialement : le test utilisait
un relais direct, sans exercer la substitution fautive à travers un second
appel. Le test conserve désormais une chaîne supplémentaire et un appelant
opaque ; le pool extérieur doit être accepté et le pool de bloc refusé.
Les résultats initiaux restent dans `…-final-mutations-o2.log`, et les six
mutations précédant le complément tableaux dans `…-chain-mutations-o2.log`.
La campagne initiale `…-mutations-o2.log` contient également une faute
inconclusive de contrôle de charge : le corps du consommateur échouait avant
le contrôle recherché. Un consommateur qui ignore la charge isole ce contrôle.

Les régressions élargies ont terminé avec 312 méthodes natives en 251,441 s
(`…-native-o2.log`) et 275 méthodes async en 454,787 s (`…-async-o2.log`).
Elles ont chargé le code avant les derniers correctifs de groupes de captures
et l'extension tableaux ; elles ne remplacent donc pas les contrôles ciblés
finaux. Une sélection voisine antérieure de 75 méthodes passe en 57,287 s
(`…-regression-o2.log`). Les séries se recouvrent et ne doivent pas être additionnées.

Les journaux d'échec incluent des erreurs de fixtures corrigées sans modifier
les règles : syntaxe bool, méthode byte_len, usages explicites manquants et
littéraux u8 remplacés par l'annotation de tableau supportée. Les assertions
de résultats et de sûreté sont conservées.

## Complément : jonctions de frames différentes

Les résultats de if, loop et match de fonctions async distinctes peuvent
maintenant partager un type public identique. L'unification compare le type
du résultat, puis transforme les positions de captures de chaque frame en
groupes de permissions communs avant de réunir leurs cibles. Elle conserve
les sources de stockage de toutes les branches possibles. Elle ne convertit
pas les tâches inactives et ne rend pas compatibles deux charges différentes.

Le programme `validation/public-handle-control-if.crust` était refusé avec
« même type requis dans toutes les branches » ; ce résultat est reproduit
depuis la copie du compilateur antérieure aux jonctions et conservé dans
`validation/public-handle-control-before.log`.

Les cinq méthodes de `tests/test_public_handle_control.py` passent à O2 en
10,547 s (`validation/public-handle-control-injected-pools-o2.log`). Elles
exercent 22 exécutions C : deux branches pour if, loop avec continue, match
consommant, partagé et mutable, avec captures empruntées puis String
transférées depuis deux pools, plus deux résultats de tableaux fixes.
Les 20 variantes invalides de permission/type passent par les deux entrées.
Des appelants opaques supplémentaires exercent quinze refus (cibles actives
et pool trop court) et dix acceptations, sans aucun corps async disponible.

Quatre fautes spécifiques sont détectées : omission de l'unification dans le
contrat, omission dans le backend, perte des captures de la seconde branche
et perte des pools capturés par un if. Les deux dernières font accepter à
tort un accès ou une fuite chez l'appelant opaque. Journal :
`validation/public-handle-control-mutations-o2.log`.

L'import direct d'une classe de tests avait déclenché sa découverte complète
par unittest ; ce lancement a été interrompu et le module importé à la place.
Le journal initial garde l'interruption. Les premières fixtures de match
consommant ont été corrigées en `match (-> choice)`. Un test de capture
propriétaire omettait les transferts descendants intermédiaires T4/T5 :
le scénario final construit les String dans la branche via des pools injectés,
puis les transfère à la tâche. La propriété testée reste la survie des pools.

La passe finale commune O0 réussit : 22 méthodes, 36,457 s,
`validation/public-handle-contracts-control-final-o0.log`. Les sept mutations
des contrats restent détectées après ce complément dans
`validation/public-handle-contracts-control-mutations-o2.log`.
La régression finale commune O2 réussit : 60 méthodes, 67,191 s,
`validation/public-handle-contracts-control-final-o2.log`. Elle inclut aussi
les contrats historiques de tâches/handles, leurs retours par contrôle de flux
et les résultats tableaux. La régression de résultats de boucles passe :
18 méthodes, 15,984 s, `validation/public-handle-control-loop-results-o2.log`.

Une sélection historique supplémentaire de 71 méthodes (conditions, boucles,
remplacements) termine avec 27 erreurs de sous-cas et deux échecs de diagnostic,
tous liés à U1 : des allocations des fixtures n'avaient aucun usage explicite.
Journal initial : `validation/public-handle-control-flow-regression-o2.log`.
Deux méthodes représentatives reproduisent ces refus sur le compilateur avant
les jonctions (`validation/public-handle-control-loop-fixtures-before.log`).
Des lectures scalaires explicites ont été ajoutées aux fixtures. Les assertions
de sortie, de trace et d'ordre de destruction, de réemploi et le diagnostic
de pool trop court ne changent pas. La relance réussit : 71 méthodes en
60,942 s, `validation/public-handle-control-flow-fixtures-fixed-o2.log`.
Les diffs des fixtures sont conservés dans les fichiers
`validation/public-handle-control-u1-*.patch` ; les changements du compilateur
dans `validation/public-handle-contracts-*.py.patch` et
`validation/public-handle-control-*.py.patch`. Le nouveau module
`handle_types.py` contient les descripteurs publics et l'unification.

## Limites et suite

Mise à jour : les contrats synchrones à résultat alloué Int, String et
Vector<Int/u8>, ainsi que leur enveloppe faillible, sont maintenant traités
dans [le cycle des résultats alloués](PUBLIC_OWNED_HANDLES_CYCLE.md).
Les limites ci-dessous décrivent la fin du présent cycle scalaire/tableaux.

- Les signatures publiques de résultats empruntés et propriétaires restent
  à raccorder ; les annotations locales de ces handles fonctionnent déjà.
- Les paramètres/retours publics dans les signatures async restent ouverts.
  Deux programmes minimaux sont conservés avec leurs diagnostics dans
  `validation/open-public-handle-owned-contract.crust` et
  `validation/open-public-handle-async-parameter.crust`. Ces refus sont des
  limites d'implémentation, pas de nouvelles règles normatives.
- Les captures générales, le remplacement de dépendances de champs,
  Select, l'installation publique du scheduler et les gardes restent ouverts.
- Le profil historique reset refuse encore un reset dans un auxiliaire après
  son join lorsque la source était capturée. Le reset dans l'appelant après
  retour de l'auxiliaire est exercé avec succès. Le refus conservateur est
  conservé dans `validation/public-handle-contracts-reset-o2.log` ; il ne
  constitue pas une nouvelle règle. Reset demeure retiré du profil normal.
- Pas de nouveau contrôle ASan/TSan, second compilateur C ou preuve formelle.
  Les tests ne couvrent ni tous les types ni tous les ordonnancements.

Le cycle de contrats synchrones scalaires/tableaux et de leurs jonctions est
terminé pour ce périmètre testé. L'objectif global n'est pas terminé ; les
limites de signatures ci-dessus restent des obligations d'implémentation
pour les lots suivants.
