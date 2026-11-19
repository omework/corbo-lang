[English](ASYNC_OWNED_STRUCT_SYNC_CALLS_CYCLE.md)

# Appels synchrones depuis async avec structures propriétaires

Suivi : le refus de restitution après remplacement signalé plus bas est
traité pour les cas décrits dans
[RETURNED_OWNED_REPLACEMENT_CYCLE.md](RETURNED_OWNED_REPLACEMENT_CYCLE.md).

## Périmètre et règles

Ce lot applique les règles existantes T1/T6, D1/T11, B1/B2/B4/B4a,
ST1/ST7/ST15, L1/L2/L6 et AS5/AS8/AS9/AS12/AS13. Il complète les
brouillons 01, 03, 04 et 05 sans modifier leur sémantique normative.

Les états async peuvent transmettre aux auxiliaires synchrones les graphes
finis propriétaires déjà pris en charge : champs Int et A<Int>, A<String>,
A<Vector<Int/u8>> ou structures de cette famille. Les auxiliaires peuvent les
consommer ou les restituer, directement ou dans les deux enveloppes Result
prises en charge. Les flèches restent nécessaires ; les appels sont contrôlés
par leurs contrats. Le backend émet séparément le corps du bridge.

Les adresses ne changent pas. Les champs ne deviennent pas des allocations
indépendamment possédées par le bridge. Les pools des descendants restent
retenus après réception du résultat. La construction générale de structures
dans les états async ne fait pas partie du support terminé.

## Changements et contre-exemples

- `validation/open-async-owned-struct-sync-call.crust` était refusé à la
  signature. Le bridge décrit maintenant les champs propriétaires et leurs
  sources, sans les déplacer ni les enregistrer comme nettoyages séparés.
  Un Result en erreur ne provoque aucune lecture de champ à travers NULL.
- Les signatures propriétaires admettent les feuilles String/Vector<Int/u8>
  déjà représentées par le runtime. Cela n'active pas les Pool<Structure>
  dans les états async : leur construction demande un raccordement distinct.
- L'analyse des retours accepte les marqueurs explicites de résultats calculés,
  notamment `return <-identity(->h);`. Un retour propriétaire non marqué reste
  refusé. Le suivi du stockage consulte aussi les candidats des champs.
- Le nouvel essai d'emprunt `let view=&*h.value` dans async a révélé un refus
  d'expression pourtant valide. Les projections partagées et mutables de
  champs A<Int> sont raccordées. Elles réservent aussi le porteur contre sa
  consommation ; la variante mutable réserve la cible à travers `yield`.
- Un helper peut remplacer un champ propriétaire puis consommer le porteur.
  Le test exerce deux pools distincts et constate les destructions de l'ancien
  champ, du nouveau champ, puis du porteur, chacune une fois.

## Vérifications exécutées

Les commandes natives utilisent Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan bloquant (`-fno-sanitize-recover=all`).
Les tests et mutations sont dans `tests/test_async_owned_struct_sync_calls.py`
et `tests/run_owned_struct_sync_mutations.py`.

- O0 : treize méthodes passent en 8,389 s dans
  `validation/async-owned-struct-sync-call-complete-o0.log`. La quatorzième,
  ajoutée ensuite, passe séparément en 1,264 s dans
  `validation/async-owned-struct-sync-call-nested-o0.log`.
- O2 final : quatorze méthodes passent en 10,294 s, avec **23 exécutions
  natives**, **15 programmes invalides** vérifiés dans les deux stages
  (**30 contrôles de refus**), et une interrogation de contrat dans le profil
  reset historique. Journal :
  `validation/async-owned-struct-sync-call-final-counted-o2.log`.
- Régression sur le code final : **114 méthodes**, 76,035 s, O2, code terminal 0.
  Elle couvre appels propriétaires sync, captures/retours de structures async,
  réemprunts de champs, retours de champs, stockage des réemprunts, contraintes,
  résultats propriétaires et handles publics propriétaires. Journal :
  `validation/async-owned-struct-sync-call-regression-o2.log`.
  Les deux derniers ajouts au fichier de tests ciblés sont postérieurs à cette
  régression ; ils ne changent pas le compilateur.
- `py_compile` réussit sur les modules modifiés et les deux fichiers de tests.
  Les diffs du compilateur sont conservés dans
  `validation/async-owned-struct-sync-call-*.py.patch`, par rapport à la copie
  antérieure `/tmp/crust-before-async-owned-struct-sync-call/`.

Le modèle de durées de vie énumère les huit placements parent/enfant des pools
racine, enfant et feuille. Son attendu est calculé par comparaison de profondeurs
de scopes, indépendamment des métadonnées du compilateur. Un seul placement
permet au résultat de sortir ; les sept autres sont refusés par les deux stages.

Trois sondes C détiennent exclusivement une tâche non lancée : avant appel,
après restitution et pendant la suspension d'un argument suivant. Elles vérifient
l'identité des deux allocations, leur destruction unique enfant avant parent et
le réemploi des deux slots. Ce harnais n'introduit aucune annulation publique.

Les échecs de lancement sont injectés dans les chemins Result simple et
imbriqué. Le dernier test distingue succès, échec du lancement de l'enveloppe
et échec du lancement de sa tâche enfant : sorties 7, 30 et 20 respectivement,
avec une seule destruction du graphe dans chaque cas.

Le contrôle `reset` n'ajoute pas l'opération au langage public. Il consulte le
contrat historique de disjonction entre le pool reçu, la source du résultat et
la source de son champ après relais. Il ne remplace pas les tests de durées de
vie et de drop exécutés dans le profil normal.

## Mutations et échecs conservés

La première campagne a détecté trois fautes et laissé survivre deux mutations
dans les méthodes sélectionnées :
`validation/async-owned-struct-sync-call-mutations-o2.log`.

- Sans graphe de champs du bridge, un simple relais opaque continuait de
  fonctionner. L'audit sur les onze méthodes de cette version détecte cinq
  échecs de programmes valides qui inspectent les champs. Journal :
  `validation/async-owned-struct-sync-call-survivor-audit.log`.
  Le ciblage final utilise ce chemin d'inspection ; il détecte un support perdu,
  pas une corruption mémoire exécutée.
- La mutation de destruction anticipée ciblait le retour d'une variable,
  tandis que l'essai retournait directement un appel. La faute finale est
  injectée sur le chemin de retour calculé effectivement exercé. Le premier
  résultat reste classé survivant dans sa campagne, avec ce défaut de ciblage.

La campagne finale passe sa baseline de treize méthodes à O2 en 8,578 s puis
détecte les **cinq fautes** : omission du graphe, lecture de NULL dans Err,
oubli du nettoyage de l'argument préparé, destruction prématurée du résultat
calculé et perte du prêt d'un champ propriétaire. Journal :
`validation/async-owned-struct-sync-call-mutations-final-o2.log`.
Le test du Result double a été ajouté ensuite et passe à O0/O2 ; il ne change
ni les mutations ni les cinq méthodes qui les détectent.

Les échecs initiaux sont conservés : huit échecs de sous-cas dans la première
passe (signatures de collections, contrôle trop restrictif du marqueur de retour,
attendu de diagnostic omettant « immuable »), puis le cas de projection non
raccordée dans la passe élargie. Journaux `initial-o0`, `second-o0`,
`expanded-o0`, `fields-o0` et `final-o0` avec le même préfixe de lot.
Les corrections d'attendus n'ont pas changé les propriétés admises/refusées.

## Écarts encore ouverts

Deux programmes valides restent refusés, avec preuves actuelles dans
`validation/async-owned-struct-sync-call-open-limits.log` :

1. `validation/open-async-local-owned-struct-helper.crust` : un helper crée une
   structure sur sa data stack et la rend à async. Avant la garde explicite,
   `verify_program` acceptait mais `compile_source` refusait la sortie du
   stockage local. Aucun binaire de ce cas n'a été exécuté. Les deux stages
   signalent maintenant le stockage du receveur non raccordé. La solution
   attendue reste l'injection de ce stockage, pas le refus normatif du programme.
2. `validation/open-async-return-replaced-owned-field.crust` : un helper remplace
   le champ par une allocation d'un autre pool, puis restitue le porteur.
   Le vérificateur refuse encore la restitution après remplacement. Il faut
   propager le graphe après l'appel jusque dans les résultats async, sans
   réutiliser simplement la photographie du graphe à sa capture initiale.

Restent aussi les agrégats généraux avec emprunts, enums et constructions
async hors des familles indiquées. Les pools de champs sont suivis de manière
conservatrice ; aucune précision générale de suppression des anciennes sources
après remplacement n'est revendiquée.

Tous les processus de test cités sont terminés. Les modèles et sondes sont
finis ; ce lot ne prouve pas la sûreté générale. Aucun nouveau résultat ASan
ou TSan n'est revendiqué. Les arbitrages de handles capturés et de branches
Select perdantes ne sont pas modifiés ; l'objectif global reste ouvert.
