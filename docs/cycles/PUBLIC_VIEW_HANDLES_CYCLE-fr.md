[English](PUBLIC_VIEW_HANDLES_CYCLE.md)

# Contrats publics des handles à résultat vue

## Périmètre et règles

Ce lot applique AS12/AS13, RT5/RT6, MT1/MT5/MT6, D1/D3, B1/B2/B4/B5,
TX4/TX5/TX12 et les règles de tranches. Il n'introduit aucune nouvelle règle.
Les signatures synchrones publiques acceptent maintenant les résultats &str,
&u8, &[Int], &[u8], &mut [Int], &mut [u8] et Result<&str,SliceError>.
Les mêmes types étaient déjà disponibles dans des tâches concrètes ; leur
contrat public ne doit pas perdre les dépendances de stockage.

Un descripteur opaque conserve séparément les captures actives et les groupes
de vues retournées. Join libère les premières ; les seconds protègent encore
les cibles jusqu'au dernier usage. Les alternatives de fonctions distinctes
sont réunies, sans attacher le résultat à une capture temporaire sans lien.
Une capacité exclusive peut rester nécessaire derrière un résultat partagé.
Les données statiques peuvent fournir une vue sans groupe de cible dynamique.
Les descripteurs publics ne produisent aucun pool ou état d'exécution fictif.

Le vérificateur concret, les contrats de résultats et les contraintes de sources
conservent ces groupes. L'analyse des effets reconnaît aussi le type de vue
extrait du Result de join : un défaut empêchait d'appeler byte_len sur cette
valeur après un match. Le passage d'une case de tableau fixe u8 à un paramètre
&u8 reconnaît désormais son descripteur d'emprunt ; auparavant la représentation
interne array_ref faisait rejeter ce passage valide.

## Contre-exemples et exécutions

Le refus initial du contrat public est conservé dans
`validation/public-view-handles-before.log`. Le programme
`validation/open-public-handle-view-contract.crust` est désormais pris en charge.
La première version du scénario contenait aussi une expression bloc à valeur
textuelle non raccordée ; le scénario utilise maintenant des liaisons ordinaires
et un drop explicite de la capture temporaire. Cette autre restriction n'est
pas présentée comme corrigée.

Les dix méthodes de `tests/test_public_view_handles.py` passent :

- O0, 31,040 s : `validation/public-view-handles-final-o0.log`.
- O2, 31,337 s : `validation/public-view-handles-final-o2.log`.

Compilation C11 par Clang, pthread, avertissements fatals et UBSan fatal.
Une assertion supplémentaire sur la contrainte sémantique de sources est ensuite
ajoutée au test des deux relais : elle passe à O0 (0,463 s) et O2 (0,757 s),
journaux `validation/public-view-handles-contract-check-o{0,2}.log`.
Aucun changement du compilateur n'intervient entre ces passages.

Les scénarios comprennent :

- Relais publics, helper join, appelants opaques sans corps ni catalogue async.
- Destruction de la capture temporaire après join ; destruction ou mutation
  d'une cible du résultat refusée avant son dernier usage, admise après.
- Tranches partagées et mutables Int/u8, réemprunts, lecture depuis un accès
  d'origine réservé, écriture via la vue et résultat partagé issu d'une capture
  mutable. Les signatures conservent leurs modes.
- Octets empruntés depuis String ou tableau fixe, et vues statiques.
- Résultat de découpe UTF-8 enveloppé dans le Result de join ; succès, mauvaise
  frontière et dépassement ; échec de lancement injecté à l'exécution.
- Réinitialisation historique après join : pool indépendant admis, pool cible
  refusé, à travers des relais et conversion de handle concret vers public.
  Reset reste accessible uniquement par option de compatibilité explicite.

Le modèle indépendant énumère les ensembles d'objets nécessaires avant et
après join, pour deux branches de tâches aux paramètres permutés. Sur 32
scénarios, six sont exécutés et 26 doivent être refusés par les deux entrées
verify_program et compile_source. Le modèle ne consulte ni les résumés ni le C.
Le test de contrats vérifie en plus l'obligation de distinction entre le pool
réinitialisé et la source de la capture retournée, indépendamment du refus
redondant que peut produire le backend concret.

Douze méthodes async préexistantes sur les vues, tranches, résultats, champs de
captures et parties disjointes passent à O2 en 23,128 s :
`validation/public-view-handles-async-regression-o2.log`.
La régression élargie passe 132 méthodes à O2 en 154,293 s :
`validation/public-view-handles-regression-o2.log`. Elle couvre les types et
contrats publics de handles, les charges allouées et empruntées, les découpes
UTF-8 sync/async, les expressions empruntées, les écritures calculées,
let/let mut et les remplacements. Elle ne représente pas une exécution de
l'intégralité des tests du dépôt. La compilation Python des six modules
modifiés et des trois fichiers de tests/campagnes concernés réussit aussi.

Les journaux intermédiaires restent conservés. Les premières fixtures utilisaient
une découpe mutable directe non reconnue ; elles utilisent maintenant les
tranches issues de split_at_mut. Une attente de diagnostic readonly a été
alignée sur le diagnostic effectif, sans changer l'attente de refus. Les erreurs
sur le type après match et sur l'argument &u8 de tableau étaient des défauts du
compilateur, corrigés dans ce lot.

## Fautes injectées

Campagne finale : `validation/public-view-handles-mutations-contract-o2.log`,
runner `tests/run_public_view_handle_mutations.py`. Quatre fautes détectées :

1. Effacement du groupe de résultat du contrat : l'appelant opaque accepte une
   destruction prématurée.
2. Effacement de la projection lors de la conversion concrète vers publique :
   une tranche valide ne possède plus de provenance reconnue.
3. Conservation de toutes les captures après join : des drops valides de la
   capture temporaire sont refusés.
4. Effacement de la source retournée dans les contraintes : la contrainte de
   distinction nécessaire manque dans le contrat du relais concret.

Une mutation survit : changer le groupe exclusif de résultat en groupe partagé.
Les descripteurs de prêts des cases conservent aussi leur capacité mutable et
continuent de bloquer les accès testés. Aucune équivalence générale du mutant
n'est établie ; c'est une limite de couverture, pas une preuve de redondance
universelle.

La première campagne détectait deux fautes sur cinq. Le test de conversion
appelait initialement une fabrique dont le résultat était déjà public : il a
été complété par une conversion directe. Le refus concret masquait initialement
la perte de contrainte ; l'obligation sémantique du contrat est désormais aussi
vérifiée. Les journaux de ces campagnes restent disponibles.

La campagne précédente des handles &Int/&mut Int/&mut u8 est rejouée après
adaptation de deux ancres textuelles devenues ambiguës : cinq fautes détectées,
la mutation de source de case de vecteur survit toujours. Journal
`validation/public-view-handles-borrowed-mutations-o2.log`.

## Limites et suite

Mise à jour ultérieure : [SYNC_HANDLE_BRIDGES_CYCLE.md](SYNC_HANDLE_BRIDGES_CYCLE.md)
raccorde les fabriques synchrones de handles appelées depuis les états, y
compris le contre-exemple ci-dessous. Les limites initiales sont conservées
pour distinguer les étapes de validation.


Les signatures async publiques restent incomplètes. Le programme
`validation/open-public-view-handle-async-helper.crust` est refusé lorsque le
corps async appelle une fabrique synchrone de Handle<&str> ; le diagnostic
est dans `validation/public-view-handles-async-helper-probe.log`.
Le programme `validation/open-public-view-result-helper-precision.crust` était
également refusé pour un résultat textuel dynamique d'un helper synchrone dans
un corps async (`validation/public-view-result-helper-precision.log`). Cet écart
est corrigé dans [SYNC_VIEW_BRIDGES_CYCLE.md](SYNC_VIEW_BRIDGES_CYCLE.md), avec
une correction explicite de la fixture de drop depuis un enfant. Le refus de
la fabrique de handle reste une limite d'implémentation.

L'arbitrage AS14/RT6/RT7 sur la capture d'un handle lancé reste inchangé et en
attente. Select, scheduler personnalisable, mutex et les autres écarts globaux
ne sont pas résolus par ce lot. Aucun résultat nouveau ASan/TSan, second
compilateur C ou preuve formelle. Les tests couvrent des compositions finies.
Snapshots antérieurs : `/tmp/crust-before-view-handles` ; diffs reproductibles
conservés dans `validation/public-view-handles-*.py.patch`.
L'objectif global reste actif et non terminé.
