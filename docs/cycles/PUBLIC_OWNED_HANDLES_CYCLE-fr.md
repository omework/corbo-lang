[English](PUBLIC_OWNED_HANDLES_CYCLE.md)

# Contrats de handles à résultat alloué

## Règles et changement

RT5/RT6, MT5/MT6, AS13, D1/D3, T6 et U1 exigent que le contrat d'un
`runtime::Handle<T>` conserve les dépendances de son résultat après l'attente.
Il ne doit pas retenir ensuite un pool qui ne servait qu'à une capture détruite.
Ce cycle applique ces règles aux allocations Int, String, Vector<Int> et
Vector<u8>. Les règles normatives ne changent pas.

Les paramètres et retours transférés des fonctions synchrones acceptent
`runtime::Handle<A<T>>` pour ces quatre contenus. Le contrat opaque distingue
le stockage des captures du stockage de l'allocation rendue. Les fabriques,
relais et jonctions entre frames différentes conservent cette distinction.
Le résultat continue de porter son pool d'origine ; le transfert conserve
son adresse. Le runtime existant extrait le Cell* avant de libérer la frame.

`runtime::Handle<Result<A<T>,runtime::Error>>` est également reconnu :
le résultat du join comporte deux niveaux d'erreur distincts. L'échec du
lancement extérieur n'est pas confondu avec celui de l'enfant lancé par la tâche.

Les descripteurs publics possèdent une entrée symbolique pour la provenance du
résultat. Elle n'est ni une capture réelle supplémentaire ni un pool généré.
Sa source est indépendante du groupe opaque des autres captures, y compris
quand les types de leurs pools diffèrent. L'inférence exploite cette entrée
sans inventer un corps de tâche ni parcourir celui d'un appelé.

## Contre-exemple et correction

`validation/open-public-handle-owned-contract.crust`, refusé auparavant,
compile et affiche 7 dans le test dédié. Son ancien diagnostic est conservé.

L'intégration a révélé une perte de type dans l'analyse des effets : une
fabrique ou un relais rendait le seul nom de la frame/du handle, au lieu de
la forme interne Task/Execution. Après un join et une sortie de bloc, un
String devenait de type indéterminé, et byte_len était refusé. Le type du
résultat Task/Execution est maintenant conservé dans cette analyse, ainsi que
l'enveloppe d'un résultat alloué déjà faillible. Reproduction :
`validation/public-owned-handle-string-block.crust` et
`validation/public-owned-handles-initial-o2.log`. Le contrôle corrigé est
dans `validation/public-owned-handles-effects-fixed-o2.log`.

Une fixture de résultat alloué faillible omettait les flèches sur sa signature
et son retour. Elle a été corrigée en retour transféré explicite, sans changement
normatif. Le journal `…-nested-o2.log` garde ce refus.

## Validation exécutée

`tests/test_public_owned_handles.py` contient neuf méthodes. Les neuf passent
à O2 en 16,311 s : `validation/public-owned-handles-typed-helpers-o2.log`.
Elles exercent 31 compilations/exécutions C, 43 variantes invalides contrôlées
aux deux entrées verify_program/compile_source, ainsi qu'un appelant opaque
admis et un appelant opaque refusé, sans corps async ni fonctions disponibles.

Les scénarios couvrent :

- Les quatre types alloués, un pool de capture Int distinct, deux relais et
  la sortie d'un bloc qui détruit ce pool de capture après le join.
- Un auxiliaire d'attente qui retourne l'allocation, avec un pool de secours
  différent. Les deux sources possibles restent protectrices chez l'appelant.
- Les refus d'allocation dans un pool réservé, de fuite d'une allocation issue
  d'un pool de bloc et de destruction sous emprunt. Les essais de reset sont
  exclusivement exécutés avec le profil historique explicite.
- L'identité d'adresse avant transfert, après join et après réemploi du slot ;
  une destruction unique de l'allocation et de la capture transférée.
- Le nettoyage après refus de lancement, le réemploi des pools et les deux
  niveaux d'erreur d'un résultat imbriqué.
- Le refus d'un mauvais A<T>, même si le consommateur détruit seulement
  la charge, et l'usage obligatoire des résultats propriétaires.

Le modèle indépendant énumère les durées de vie de trois pools et deux phases.
Avant join, les trois pools possibles doivent survivre au handle. Après join,
seuls les deux pools pouvant fournir l'allocation doivent survivre au résultat.
Il ne lit pas les résumés produits par le compilateur. Ses 16 configurations
sont exécutées avec les deux choix de branche : 32 scénarios, six exécutions
C et 26 programmes refusés aux deux entrées. Ces nombres sont inclus dans les
totaux précédents, pas additionnels.

Clang C11, pthread, avertissements fatals, UBSan fatal ; O0 et O2. La baseline
de huit méthodes passe à O0 en 15,369 s (`…-final-o0.log`). La passe O0 finale
des neuf méthodes réussit en 13,542 s (`…-complete-o0.log`). La régression élargie termine avec
104 méthodes en 105,851 s (`…-regression-o2.log`) : contrats de handles,
jonctions, annotations, contrats mixtes, appels propriétaires, obligations U1,
pools injectés et locaux. Elle précède le dernier ajout de tests des auxiliaires
typés et la reformulation du diagnostic des formes encore non prises en charge.

## Mutations

Cinq fautes injectées dans des copies temporaires sont détectées :

1. Effacer la provenance symbolique du résultat opaque : un auxiliaire valide
   qui restitue son résultat est refusé faute de provenance.
2. Remplacer les sources du résultat par celles de toutes les captures : le
   résultat valide qui survit au pool temporaire devient refusé.
3. Effacer les sources du résultat lors de la réception du handle : l'appelant
   opaque accepte à tort une allocation qui survit à son pool.
4. Retirer le contrôle du type de charge : un mauvais A<T> est accepté.
5. Effacer le mode Task/Execution dans les effets : le String rendu devient
   indéterminé et un programme valide est refusé.

Journal : `validation/public-owned-handles-classified-mutations-o2.log`.
La première campagne classait la faute 1 comme inconclusive car le script
n'attendait que l'acceptation d'un programme invalide. L'examen du journal
montre précisément le refus d'un programme valide ; ce diagnostic spécifique
est désormais reconnu comme détection d'une régression d'acceptation. Les
tests et leurs attentes ne sont pas modifiés. Le journal initial est conservé
dans `validation/public-owned-handles-mutations-o2.log`.

## Limites et suite

Ce cycle ne termine pas les contrats de résultats empruntés, les signatures
async publiques, les autres agrégats propriétaires ni les enveloppes arbitraires.
`validation/open-public-handle-borrow-contract.crust` conserve un programme
valide encore refusé, avec son diagnostic. Le refus des paramètres publics
async reste conservé dans `validation/open-public-handle-async-parameter.crust`.
Les exemples sont des obligations d'implémentation restantes, pas des règles
normatives de refus.

Pas de nouveau passage ASan/TSan ni second compilateur C ; pas de preuve
formelle ni de couverture exhaustive des ordonnancements. Select, scheduler
personnalisable, mutex et les autres écarts de la matrice restent ouverts.
Les changements sont conservés dans `validation/public-owned-handles-*.py.patch`.
Le cycle est terminé pour ce périmètre testé ; l'objectif global reste actif.
