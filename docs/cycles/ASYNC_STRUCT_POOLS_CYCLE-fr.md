[English](ASYNC_STRUCT_POOLS_CYCLE.md)

# Pools de structures dans les états async

## Portée et règles

Ce lot poursuit les brouillons 03/04/05 et les règles ST1–ST4, ST15–ST16,
A1–A4/P8, D1, AS8–AS14. Les documents normatifs ne sont pas modifiés.
Le cas conservé dans `validation/open-async-result-factory-local_struct_pool.crust`
était refusé : le backend ne créait que des pools Int/String/Vector<Int/u8>.
Il est désormais compilé et exécuté avec le résultat 7.

Les pools locaux et injectés acceptent maintenant les structures dont le graphe
fini contient des champs Int et des champs propriétaires A<T> des familles déjà
prises en charge. Les champs Int imbriqués sont ceux du layout aplati existant.
Les structures contenant des références ne sont pas ajoutées par ce lot.

## Implémentation

- Le Source du pool, son unique stack de slots et les tables de champs résident
  dans l'état. Leurs adresses restent valides entre deux polls. Les cellules
  utilisent le même layout et les mêmes destructeurs que le backend synchrone.
- Les champs nommés sont évalués dans l'ordre écrit. Chaque valeur est sauvegardée
  avant l'argument suivant, même si celui-ci suspend. Les champs Int omis valent
  zéro ; aucun champ propriétaire absent n'est inventé.
- Les transferts de champs restent sous responsabilité d'un groupe temporaire
  jusqu'à la construction complète. Un retour anticipé ou le nettoyage d'une
  instance non lancée suspendue détruit les champs déjà préparés une seule fois.
- La provenance conservée comprend le pool racine et les sources des descendants.
  Une structure ne peut sortir d'un bloc qui ferme l'un de ces pools.
- Un résultat nouvellement construit dans un pool injecté conserve dans son
  contrat les sources de ses champs propriétaires, séparément de la source de
  la racine. Cela traverse les fabriques synchrones et leurs relais.
- Une tentative de déplacer un pool local reçoit maintenant un diagnostic
  explicite ; auparavant elle échouait sur la forme d'expression non raccordée.

## Contre-exemples et corrections intermédiaires

Les premières sondes comptaient les fermetures physiques comme les appels à
`source_close`. Un pool de structure ferme son enveloppe puis sa stack de slots :
le compteur de la sonde voit deux appels. Les attentes ont été corrigées, sans
changer le nettoyage. Un cas d'épuisement avait également supprimé le seul usage
explicite d'une allocation en retirant son drop ; une lecture a été ajoutée avant
la tentative d'allocation qui doit échouer.

Le nouveau cas de retour d'une structure construite dans un pool injecté a révélé
une provenance de champ propriétaire absente. Le contrat et son application ont
été corrigés ; les voisins dont le pool du descendant est trop court sont refusés.

Deux formes essayées pendant la construction de la fixture de graphe restent
hors périmètre : un helper empruntant le graphe propriétaire général, et l'accès
`*t.left.n` traversant deux champs A<T>. Ce dernier est conservé dans
`validation/open-async-struct-pool-owned-projection.crust`. Le test du nettoyage
récursif lit un champ Int de la racine et contrôle séparément la destruction
exacte de chacun des descendants ; il ne revendique pas la projection absente.

Les journaux intermédiaires sont conservés. La première régression élargie a
terminé 126 entrées avec une erreur d'import (`test_async_collection_creation`,
nom inexistant) ; les 125 autres entrées ont réussi. La commande corrigée utilise
`test_async_collection_new`. Deux tentatives de la suite finale n'ont pas démarré
à cause d'un nom de module masqué par une méthode dans la classe de test ; cette
erreur du harnais est corrigée, les logs `final-*` restent historiques.

## Preuves exécutées

- Première suite ciblée complète : 14 méthodes, 22 exécutions natives et
  19 programmes invalides vérifiés aux deux étapes, O0, 13,285 s.
  Journal : `validation/async-struct-pools-counted-o0.log`.
- Première campagne O2 : baseline de 14 méthodes réussie, puis huit mutations
  détectées. Journal : `validation/async-struct-pools-mutations-o2.log`.
- Suite finale avec inactif/échec de lancement/perdante Select : **15 méthodes
  réussies à O0 en 14,810 s**, 25 exécutions natives (dont l'épuisement attendu),
  19 programmes invalides et 38 contrôles de refus.
  Journal : `validation/async-struct-pools-complete-counted-o0.log`.
- Campagne finale O2 : baseline des 15 méthodes réussie en 14,945 s, puis
  **huit mutations détectées**, aucune survivante ou inconclusive.
  Journal : `validation/async-struct-pools-complete-mutations-o2.log`.
- Régression élargie : **174 méthodes réussies à O2 en 121,929 s**.
  Journal : `validation/async-struct-pools-regression-o2.log`. Ce processus
  avait chargé le code avant le dernier garde conservateur qui exclut les
  candidats de champs autres que `parameter`/`fresh` du nouveau résumé.
  Les deux campagnes ciblées finales comprennent ce garde.
- Passage supplémentaire des quatre suites de contrats/résultats sur l'état
  final : **51 méthodes réussies à O2 en 41,556 s**.
  Journal : `validation/async-struct-pools-result-contracts-o2.log`.

Tous les processus cités sont terminés. Les diff des quatre fichiers Python
modifiés sont conservés dans `validation/async-struct-pools-*.py.patch`.

Le modèle de boucle calcule indépendamment les sommes et le nombre de
nettoyages pour 0, 1 et 4 itérations. Une sonde native vérifie les valeurs,
le réemploi de l'adresse du slot détruit, la conservation de son voisin vivant,
la destruction suspendue et la fermeture. Ce sont des modèles finis, pas un
modèle indépendant complet du vérificateur.

Les mutants retirent ou corrompent les offsets, le destructeur du champ possédé,
la dépendance au pool du descendant, le nettoyage d'un champ préparé, le défaut
zéro, le contrat du résultat direct, le contrat propagé à une fabrique et
l'instantané d'un argument scalaire. Les tests et oracles sont inchangés dans les
copies temporaires. Les huit détections ne mesurent pas une couverture globale.

Les exécutions natives utilisent Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal, à O0/O2 selon le journal. Aucun nouveau
résultat ASan/TSan, mesure de performance ou preuve générale de sûreté.

## Écarts conservés

Mises à jour ultérieures : les pools locaux à champs empruntés sont couverts
par [ce cycle](ASYNC_BORROWED_STRUCT_POOLS_CYCLE.md), et les résultats locaux à
champs propriétaires par [le cycle des graphes locaux](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
La liste ci-dessous conserve le constat historique de fin de lot.

Les quatre refus actuels sont reproduits dans
`validation/async-struct-pools-remaining.log` ; aucun code invalide n'est exécuté.
Les pools/constructeurs async de structures à champs empruntés, les résultats
locaux neufs contenant des champs propriétaires ou empruntés, les projections
à travers des handles imbriqués, les graphes mixtes et les autres restrictions
consignées restent ouverts. Le résultat frais dans un pool injecté couvert ici
ne généralise pas les retours locaux ni les remplacements de champs propriétaires.
Les arbitrages sur les handles lancés restent inchangés.

Snapshot des fichiers modifiés : `/tmp/crust-before-async-struct-pools`.
L'objectif des sept brouillons reste actif et incomplet.
