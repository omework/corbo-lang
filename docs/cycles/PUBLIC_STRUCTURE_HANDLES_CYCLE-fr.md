[English](PUBLIC_STRUCTURE_HANDLES_CYCLE.md)

# Handles publics de structures : type du stockage et champs empruntés

## Règles et périmètre

Ce lot applique V1, T1/T6, B1–B5, D1, L1/L2/L6, AS9/AS12,
MT5/MT6 et les obligations explicites d'attente. Aucune règle normative n'est
modifiée. `runtime::Handle<T>` pour une structure locale et
`runtime::Handle<A<T>>` pour une allocation en pool sont distincts. Une
conversion de représentation de handle ne promeut pas le stockage du résultat.

Le contre-exemple `validation/open-public-local-structure-handle.crust`, refusé
par le registre des signatures au cycle précédent, est maintenant accepté
et exécuté. Ce lot couvre des structures représentées par le backend, leurs
emprunts Int partagés/mutables, les graphes possédés finis testés, et une
charge propriétaire dans un Result imbriqué. Il ne généralise pas toutes les
signatures possibles du langage.

## Implémentation

Le registre des handles publics reçoit les structures déclarées. Un type
nominal inconnu n'est pas accepté par défaut. Le descripteur public décrit
séparément les captures temporaires, la source du résultat et les champs
empruntés conservés après attente. Le groupe de résultat porte les chemins
complets, y compris les références dans les descendants possédés.

Les conversions vérifient la forme du résultat, puis sa provenance local/pool.
Les annotations et signatures publiques produisent des exigences de stockage
transmises dans les contrats. Une fonction appelée avec une tâche inactive
peut exiger le stockage local de son futur résultat ; son pont C décrit cette
exigence, et son appelant async la contrôle avant de choisir la variante.
La décision ne repose pas seulement sur le type de résultat interne `owned`.

Les champs conservés après join/await sont projetés dans l'analyse de résultats,
le flot des contraintes, le vérificateur concret et les métadonnées du backend.
Les relais synchrones peuvent travailler uniquement depuis le type public,
sans définition de tâche ni corps de fonction chez leur appelant. Les captures
et champs propriétaires conservent aussi les dépendances de leurs pools.

L'unification de deux types de tâches utilise le type public attendu ou le
stockage concret connu. Le vérificateur conserve désormais le stockage et
l'ascendance de la branche précédente lorsqu'il construit sa représentation
intermédiaire. Le backend distingue aussi les branches à résultat local et
en pool, même si elles lancent la même routine et que le handle n'est pas
annoté. Le mélange est refusé au lieu d'être assimilé à une conversion.

## Vérification exécutée

Quatorze méthodes dans `tests/test_public_structure_handles.py` :

- Fixture initiale, retour via une tâche entrante ou construction depuis une
  structure transférée ; refus du drop avant l'attente et avant le dernier usage.
- Deux relais par type public puis retour de la structure ; vérification d'un
  appelant sans aucun corps de fonction ni définition async.
- Matrice local/pool dans les annotations synchrones et async, les arguments
  de fabriques et leurs résultats, même si l'appelant détruit le résultat.
- Emprunt mutable et réemprunt partagé d'un parent mutable : accès incompatible
  refusé pendant les usages du porteur, puis écriture admise après son drop.
- Graphe à racine locale et descendant possédé contenant une référence ;
  protection de la cible et réemploi du pool descendant après nettoyage.
- Refus d'exporter un handle dépendant d'un pool enfant détruit au retour.
- Deux types de routines réunis sous un type public, branches true/false,
  et mélange local/pool refusé avec ou sans annotation.
- Fabrique d'une tâche créant une racine locale neuve dans une destination
  durable ; résultat enveloppé dans Result et maintien de deux niveaux d'erreur.
- Échec de lancement injecté aux deux niveaux, destruction unique et réemploi
  répété de pools de capacité un (états et données).

`validation/public-structure-handles-final-count-o0.log` : **14 méthodes,
24 exécutions natives, 26 programmes invalides et 52 contrôles de refus**, en
21,958 s. S'y ajoutent les contrôles de contrats et l'appelant isolé : un script
admis et son voisin refusé par `Compiler.block`, sans exécution C autonome.

Le harnais natif utilise Clang C11/pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal à O0/O2. Les échecs de soumission sont injectés
dans le C généré sans changer les résultats attendus. py_compile réussit.
Aucun nouveau résultat ASan/TSan ni preuve générale de sûreté.

La première régression de 155 méthodes, en 173,953 s, contient 30 échecs
sur la formulation des diagnostics d'annotation : les programmes invalides
étaient refusés mais le préfixe `annotation de handle` avait disparu. Ce préfixe
est rétabli sans affaiblir les assertions. Le complément ciblé de 21 méthodes
passe ensuite à O0 en 23,352 s, incluant les quatorze méthodes du lot et les
annotations historiques. Les journaux sont conservés.

La régression finale passe **157 méthodes en 180,070 s** à O2 avec
CRUST_SANITIZE=undefined :
`validation/public-structure-handles-final-regression-o2.log`. Elle inclut
les handles publics scalaires, propriétaires, empruntés et vues, les exigences
de stockage, les arguments de tâches, les références détachées, les enveloppes
locales, les graphes locaux retournés et les relais de handles concrets.
Tous les processus de validation cités sont terminés. Les runners de mutations
conservent un code de sortie 1 à cause de leurs survivantes, comme détaillé
ci-dessous ; les suites non mutées passent.

## Mutations : résultats et limites explicites

`validation/public-structure-handles-final-mutations-o2.log` contient une
baseline de quatorze méthodes à O2 en 21,922 s, puis **six fautes détectées
et une survivante**. Le runner finit avec le code 1 à cause de cette survivante ;
ce n'est pas une campagne intégralement verte.

Sont détectées : perte des champs dans le contrat de résultat, perte de leur
projection concrète, descripteur public sans champs, oubli du stockage local
d'un argument tâche, omission de l'exigence publique local/pool et oubli du
stockage de la branche précédente. Les détections sont des assertions, souvent
un rejet incorrect d'un programme valide ; elles ne représentent pas six
corruptions mémoire exécutées.

La première campagne détectait cinq fautes et en laissait deux survivre.
La projection concrète n'était pas exercée par la fabrique testée : son contrat
reconstituait déjà les champs chez l'appelant. Le test d'annotation directe
exerce cette frontière et détecte cette mutation. L'investigation est conservée
avec son refus du programme valide.

La suppression des prêts de champs ajoutés à la liste des prêts après attente
survit toujours au test ciblé. Elle survit aussi aux douze méthodes alors
présentes dans la suite, exécutées dans une copie mutée en 12,598 s. Dans ces
scénarios, les métadonnées des champs du résultat conservent la protection.
Cela n'établit pas que la mutation est équivalente dans tous les programmes ;
la couverture de sensibilité de cette représentation reste partielle.

`validation/public-structure-handles-historical-mutations-o2.log` détecte
**cinq des six fautes historiques** des handles empruntés. La suppression de
`projection_assets` pour un index de vecteur survit au test sélectionné.
Cette survivante est conservée comme limite ; aucun résultat historique plus
fort n'est déduit de cette campagne. Ces campagnes finies ne donnent pas un
taux général de couverture de la sûreté.

Les premières tentatives ont aussi révélé deux erreurs de fixtures : une
écriture via le parent mutable avant le drop encore à venir du porteur, et
un parseur de script isolé sans registre de noms de structures. Les fixtures
suivent désormais les règles existantes ; les journaux intermédiaires restent
présents. Le défaut réel d'unification des branches est reproduit dans
`open-public-structure-branch.crust`, puis corrigé.

## État restant

`validation/public-structure-handles-remaining.log` confirme aux deux étapes
la fermeture des cinq exemples de handles publics de structures de ce lot.
Deux cas valides restent explicitement ouverts :

- `open-public-structure-async-relay.crust` : passer un handle déjà lancé à une
  fonction synchrone depuis un état async. La signature d'argument n'est pas
  encore raccordée ; ce n'est pas une interdiction normative.
- `open-nested-field-replacement.crust` : remplacer les dépendances d'un champ
  descendant par appel depuis async.

SL2 reste appliquée : `open-select-launched-handle.crust` est refusé aux deux
étapes. La capture d'un handle lancé dans une tâche inactive reste un arbitrage
distinct en attente. Le placement général, les signatures générales et le
remplacement public du scheduler ne sont pas achevés. Aucun reset n'est
réintroduit. L'objectif global reste actif.

Les patches des sept modules sont archivés sous
`validation/public-structure-handles-*.py.patch`. Le snapshot de référence est
`/tmp/crust-before-public-structure-integration/`, sauf handle_types.py et
async_lowering.py dont la préparation commencée avant ce lot est incluse depuis
`/tmp/crust-before-public-structure-handles/`.
