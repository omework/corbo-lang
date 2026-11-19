[English](PUBLIC_BORROWED_HANDLES_CYCLE.md)

# Contrats publics de handles à résultat emprunté

## Règles et périmètre

AS12/AS13, RT5, MT3/MT5, B1–B5 et D1 imposent de conserver les cibles
du résultat après join, sans prolonger les captures qui ne servent plus.
Ce cycle raccorde les signatures synchrones `runtime::Handle<&Int>`,
`runtime::Handle<&mut Int>` et `runtime::Handle<&mut u8>` à ces règles.
Les règles normatives ne changent pas.

Le contrat public sépare les captures actives pendant l'exécution des
projections pouvant fournir le résultat. Un groupe distinct conserve la
capacité exclusive dont dérive un résultat partagé. Les relais ne recalculent
pas ces groupes comme s'il s'agissait de nouvelles captures. Aucun état
supplémentaire, pool ou pointeur de résultat n'est ajouté au runtime.

Le compilateur projette les dépendances avant d'effacer le nom concret de
la tâche. Les appelants utilisent ensuite le contrat sans parcourir le corps.
Un groupe opaque vide est ignoré ; il ne crée pas de cible fictive. Les cibles
effectives et leurs parents nécessaires sont conservés. Le C extrait toujours
le résultat avant la libération de la frame, avec la représentation existante
de la référence (allocation ou adresse inline).

## Contre-exemples et corrections

- `validation/open-public-handle-borrow-contract.crust`, auparavant refusé,
  est maintenant exécuté et affiche 7. Son ancien diagnostic est conservé.
- Un auxiliaire d'attente partagé pouvait rencontrer un groupe exclusif vide
  et refuser un programme valide. Les groupes publics optionnels sont traités
  sans inventer de provenance.
- Le raccordement de `&mut u8` a révélé l'absence de l'emprunt direct d'une
  case de Vector dans le backend synchrone, et une perte de sa source dans
  l'analyse des contraintes. Les accès Int/u8 évaluent et vérifient l'indice,
  réservent le vecteur pendant cette évaluation, puis exposent son adresse.
- Le stockage symbolique d'un paramètre octet avait un nom de liaison différent
  du nom de son entrée de scope. La recherche du scope utilise désormais
  l'identité de la liaison.
- Un auxiliaire retournant l'octet après join traitait sa cible symbolique
  comme une allocation Int. La cible octet conserve désormais sa représentation
  inline. Les contraintes distinguent aussi les octets des tableaux fixes
  sans source de pool. Reproduction conservée dans
  `validation/public-borrowed-handle-byte-finish.crust`.

## Vérifications exécutées

`tests/test_public_borrowed_handles.py` contient dix méthodes. Elles passent
à O2 (`validation/public-borrowed-handles-byte-helper-o2.log`, 14,043 s)
et à O0 (`validation/public-borrowed-handles-complete-final-o0.log`, 15,159 s).
Configuration : Clang C11, pthread, avertissements fatals, UBSan fatal.
Le complément final de références partagées vers une case de tableau ou un
champ inline passe aussi à O2 (`…-shared-inline-o2.log`, 2,216 s) et O0
(`…-shared-inline-o0.log`, 2,348 s), en plus des variantes mutables initiales ;
il ne modifie pas le compilateur.

Les scénarios comprennent :

- Fabrique, deux relais, auxiliaire join, puis utilisation du résultat.
- Références partagées et mutables, cases de tableaux fixes, champs Int,
  champs partagés détachables et réemprunts conservant un porteur mutable.
- Captures détruites après join alors que le résultat reste utilisé ; drop,
  écriture et reset historique prématurés refusés aux entrées de vérification
  et de compilation ; accès rétablis après le dernier usage.
- Appelant opaque avec uniquement les contrats, sans catalogue de fonctions
  ni définitions async : une variante admise et deux refus de drop prématuré.
- Réutilisation des pools, nettoyage unique des valeurs capturées après
  leur dernier usage, et refus de lancement injecté.
- Octet retourné depuis une case de vecteur ou de tableau, écrit à travers
  le résultat ; erreur de lancement restituant une autre cible valide.
- Vecteurs Int/u8 : emprunt readonly/mutable, croissance concurrente refusée,
  transfert pendant l'évaluation de l'indice refusé, indice hors limites
  provoquant un diagnostic runtime.

Le modèle indépendant énumère les positions de trois allocations par rapport
à un bloc. Avant join, les trois captures doivent survivre ; après join,
seules les deux cibles possibles du résultat doivent survivre. Il examine
32 scénarios : six exécutés et 26 refusés, avec les deux choix de branche.
Le modèle ne lit ni le C ni les résumés du compilateur.

La régression des contrats, handles, champs et appels empruntés passe
97 méthodes à O2 en 126,951 s, dans
`validation/public-borrowed-handles-regression-o2.log`. Elle précède les derniers
compléments octet/tableau et tests de frontières de vecteurs. Les passages
ciblés finaux les couvrent. La régression supplémentaire tableaux/octets/
vecteurs passe 122 méthodes à O2 en 85,743 s, journal
`validation/public-borrowed-handles-arrays-regression-o2.log`.
Les contrats publics scalaires, alloués et empruntés sont rejoués après les
derniers correctifs : 36 méthodes à O2 en 50,827 s, dans
`validation/public-borrowed-handles-contracts-final-o2.log`. Le complément
inline partagé, ajouté ensuite, possède ses deux passages ciblés ci-dessus.

Les journaux initiaux restent conservés. Certaines fixtures utilisaient
`Ok(mut view)` non reconnu, un nom de classe de test incorrect ou un usage
après drop fourni par défaut par un générateur de tests. D'autres attendaient
un libellé de diagnostic différent. Ces fixtures ont été corrigées sans
modifier les règles ni les attentes de durée de vie. Les erreurs de compilation
des cas octets décrites ci-dessus étaient, elles, des défauts d'implémentation.

## Mutations

Campagne finale : `validation/public-borrowed-handles-mutations-final-o2.log`.
Cinq fautes sont détectées dans des copies temporaires :

1. Effacement des groupes du résultat dans le contrat : drop prématuré accepté
   par l'appelant opaque.
2. Conservation de toutes les captures après join : programme valide refusé.
3. Effacement de la projection lors de la conversion au type public : résultat
   sans cible, détecté par l'invariant interne sur le programme valide.
4. Perte de la capacité exclusive derrière un résultat partagé : accès
   prématuré accepté dans le voisin avec capture directe.
5. Mauvaise représentation du résultat octet symbolique : auxiliaire valide
   refusé comme s'il devait rendre une allocation Int.

La mutation qui efface la source d'une case de vecteur dans l'analyse des
contraintes **survit** au test choisi dans l'état final. Le backend conserve
ses propres cibles et vérifications ; aucune équivalence générale n'est
établie. La première campagne détectait cette mutation par un refus incorrect
avant l'ajout du traitement des tableaux fixes. Les journaux conservent les
deux résultats, sans réutiliser l'ancien résultat comme preuve du code final.

La mutation 4 survivait initialement avec un emprunt parent nommé, qui gardait
une autre protection. Le test voisin à capture directe détecte la faute.
Pour la mutation 1, une seconde destruction dans le test masquait initialement
l'absence de refus du premier drop. Ce nettoyage redondant a été retiré du
programme invalide ; le test exige toujours le refus avant l'usage de la vue.

## Limites et suite

Signatures publiques async, autres types empruntés, enveloppes arbitraires,
agrégats généraux, Select, scheduler personnalisable et mutex restent ouverts.
Les frontières C et autres reports explicites restent hors de ce lot.
Le paramètre public async est encore refusé dans le contre-exemple
`validation/open-public-handle-async-parameter.crust`. Le contrôle CLI exécuté
sur l'état final est conservé dans `…-next-async-gap.log` : cette limite
d'implémentation reste le prochain lot, pas une nouvelle règle de refus.
Le reset est exercé uniquement avec l'option historique explicite.

Pas de nouveau résultat ASan/TSan, de second compilateur C ou de preuve formelle.
Les tests n'établissent pas tous les ordonnancements ni toutes les compositions
de contrats. La mutation survivante demeure une limite de couverture.
Les diffs sont dans `validation/public-borrowed-handles-*.py.patch`.
Ce cycle est terminé pour les formes testées, avec sa limite de mutation
survivante explicitée ; l'objectif global reste actif.
