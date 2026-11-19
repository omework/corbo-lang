[English](ASYNC_DETACHED_FIELD_RETURNS_CYCLE.md)

# Cycle — références partagées détachées retournées en async

## Règles et périmètre

Application de ST13, ST11/ST12/ST14, B1–B5, D1, AS12/AS13 et MT3, sans
modification normative. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des
brouillons et les règles de champs/résultats ont été consultés. Le chantier
global des sept brouillons reste ouvert.

Un champ `&Int` retourné depuis une tâche conserve la cible extérieure et
ses parents de réemprunt. Il ne réserve plus artificiellement le slot de la
structure qui contenait cette référence. Les champs Int directs et les
capacités `&mut Int` conservent leurs réservations de porteur. Une jonction
réunit les deux sortes de dépendances quand ses branches les mélangent.

Les résumés async et les contrats des relais synchrones distinguent ces
projections. Dans les états, une origine de cible partagée ne bloque pas
une mutation indépendante du porteur. Le remplacement des champs références
dans ces états reste refusé, conformément à la restriction d’implémentation
précédente : cette extension ne suppose pas ces effets déjà pris en charge.

Le bridge des helpers synchrones convertit le `Cell *` d’un emprunt Int en
adresse de sa valeur avant de le restituer à l’ABI `int *` des états.
Un bloc synchrone peut aussi fournir une référence Int ; sa destination est
vérifiée avant le nettoyage, sans promouvoir une cible locale.

## Scénarios et modèle

`tests/test_async_detached_field_returns.py` exerce les écritures directe,
nommée et `&*`, les captures partagées/mutables, les enfants async, helpers,
méthodes, relais synchrones après join, mutations indépendantes du porteur,
destruction et réemploi de son pool, dernier usage de la cible, ancêtres
mutables et résultats mélangeant cible externe et champ direct.

Les voisins invalides détruisent ou modifient prématurément la cible,
détruisent un porteur encore nécessaire, copient un champ mutable ou font
sortir une référence vers une allocation locale. Le contrôle du reset est
uniquement historique (`allow_legacy_reset=True`) ; l’API publique reste retirée.
Un échec de lancement est injecté par EAGAIN, sans changer les attentes de
libération des captures.

Le modèle indépendant `test_async_detached_field_model` associe chaque résultat
à son stockage logique (porteur ou cible), puis compare une opération qui
invalide ce stockage avant/après le dernier usage. Ses douze combinaisons
prédisent huit exécutions et quatre refus, vérifiés aux deux entrées du
compilateur. Les valeurs attendues sont calculées sans consulter les contrats.
Les deux modèles précédents des chemins de champs sont aussi rejoués.

## Preuves exécutées

Les journaux cités sont dans `validation/`.

- `async-detached-fields-block-o0.log` : onze méthodes, 7,662 s, OK,
  avant les tests supplémentaires de sortie de bloc et d’ascendance.
- `async-detached-fields-regression-o2.log` : 61 méthodes, 51,261 s, OK ;
  champs async, réemprunts, contrats et expressions empruntées.
- `async-detached-fields-final-o0.log` : 25 méthodes, 26,051 s, OK ;
  l’import initial du modèle redécouvrait aussi les douze méthodes de sa fixture.
  Ces répétitions ne sont pas des scénarios nouveaux. L’import a été corrigé.
- `async-detached-fields-models-o2.log` : trois méthodes, 28,563 s, OK ;
  douze combinaisons du nouveau modèle et 24 de chacun des deux modèles antérieurs.
- `async-detached-fields-mutable-neighbor-o2.log` : le réemprunt partagé valide
  d’un champ mutable, avec porteur conservé, réussit également.
- `async-detached-fields-complete-final-o0.log` : treize méthodes, 20,389 s,
  OK, avec le modèle et tous les compléments ciblés.
- `async-detached-fields-complete-mutations-o2.log` : baseline finale de douze
  méthodes, 16,652 s, OK ; 27 exécutions C dont un échec de lancement injecté,
  32 programmes invalides vérifiés aux deux entrées (64 contrôles).
  Quatre mutations détectées, deux survivantes ; code de sortie 1 attendu
  pour ce bilan non entièrement détecté.
- `async-detached-fields-destruction-o2.log` : une méthode, 2,593 s, OK ;
  six variantes vérifient exactement `destroy v`, `reclaim v`, puis
  `destroy data`, `reclaim data`, sans double destruction.

La régression native élargie `async-detached-fields-native-o2.log` termine
avec 291 méthodes réussies en 239,123 s. Elle a démarré avant les deux derniers
compléments de tests d’ascendance et de réemprunt mutable valide ainsi que les
assertions de trace ; ceux-ci sont couverts par les passages ciblés finaux.

Les harnais utilisent Clang C11, pthread, avertissements fatals et UBSan fatal,
avec O0/O2 selon le journal. Aucun résultat nouveau ASan/TSan, second compilateur,
mesure de performance ou preuve formelle n’est revendiqué.

## Mutations et échecs conservés

La première campagne ciblée détecte trois fautes et en laisse trois survivre.
L’ajout du voisin valide du champ mutable révèle ensuite la faute qui tentait
de traiter une capacité mutable comme une référence copiable : le contrôle
de copie rejette ce programme valide. Les survivantes d’ascendance et de
frontière de bloc restent protégées par d’autres contrôles dans les cas exercés ;
aucune équivalence générale n’est établie.

Les anciennes campagnes ont leurs ancres adaptées à la factorisation des
projections, sans modifier leurs oracles : sept fautes de réemprunt et six
fautes de contrats détectées. La campagne des retours de champs détecte sept
fautes ; l’omission de la capacité cible explicite reste survivante comme au
cycle précédent. Les journaux sont `async-detached-fields-reborrow-mutations-o2.log`,
`async-detached-fields-contract-mutations-o2.log` et
`async-detached-fields-return-mutations-o2.log`. Un code de sortie 1 des
campagnes comportant des survivantes n’est pas présenté comme un succès global.

Les journaux initiaux sont conservés :

- `initial-o0` : destruction explicite d’une source non transférable dans la
  fixture ; bridge C avec représentation de pointeur incorrecte, corrigé.
- `targeted-o0` et `complete-o0` : résultat emprunté de bloc refusé ; deux
  assertions d’un test de champs mutables rangées par erreur dans le test
  voisin. La fixture est corrigée sans assouplir les attentes mémoire.
- Le programme enregistré `open-async-detached-field-return.crust` omettait
  l’import `-> v;` nécessaire avant drop dans le bras enfant. Le test ajoute
  cet import explicite ; il ne supprime pas la règle de scope.

## Contre-exemple encore ouvert et limites

Suivi : le contre-exemple de stockage ci-dessous est désormais corrigé et
testé dans [STORED_FIELD_REBORROWS_CYCLE.md](STORED_FIELD_REBORROWS_CYCLE.md).
Le défaut et le journal ci-dessous décrivent son état à la fin du présent cycle.

`open-struct-field-reborrow-stored-shared.crust` construit un porteur partagé
à partir d’un réemprunt d’un champ mutable d’un autre porteur. Ce programme
valide reste refusé lors de la construction (`champ 'data' : &Int requis`),
avant d’atteindre le test d’ascendance souhaité. Le journal
`async-detached-fields-ancestry-o2.log` conserve cet échec. Ce cas requiert
le raccordement des représentations de références lors de leur stockage.

La couverture du présent lot reste limitée aux champs Int/&Int/&mut Int et
aux formes de contrats exercées. Les graphes plus généraux, les changements
de dépendances des champs depuis les états, le runtime public complet,
Select, les gardes de mutex et le placement général restent ouverts.
Les modèles sont finis ; les tests n’explorent pas tous les ordonnancements.

Le source et le C de démonstration sont conservés dans
`validation/async-detached-field-fixed.crust` et `.c`. Les diffs avec les
snapshots précédant le lot sont `validation/async-detached-fields-*.py.patch`.
