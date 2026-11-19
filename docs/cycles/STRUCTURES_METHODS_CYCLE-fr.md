[English](STRUCTURES_METHODS_CYCLE.md)

# Cycle documentaire — structures et méthodes

Date : 5 novembre 2026.

## Demande et périmètre

Consigner le dernier chantier avant de poursuivre l'arbitrage. Pas
d'implémentation, pas de modification des tests. AGENTS.md et
VALIDATION_GUIDELINES.md ont été lus. Ce rapport n'est pas un cycle complet
de validation exécutable au sens des guidelines.

## Décisions consignées

STRUCTURES_METHODS.md regroupe ST1–ST18 et ME1–ME4. LANGUAGE_RULES.md intègre
l'extension et I6, l'objectif explicite de lisibilité de l'intention pour la
génération par IA. Le README et la matrice distinguent conception et comportement
effectivement implémenté.

Points importants de fidélité à la discussion :

- La décision finale interdit l'extraction par déplacement des champs non Copy
  et les états partiellement initialisés. Les cas initialement acceptés de
  nettoyage partiel et de jonction après déplacement ne sont plus normatifs.
- Une omission à `pool.new` reste permise si un défaut du type initialise
  effectivement le champ : ce n'est pas un état partiel exposé au programme.
- Le défaut Int=0 et la déduction récursive sont retenus ; la déclaration de
  défaut sur le champ a été rejetée. Les tags et défauts personnalisés sont reportés.
- Les copies deviennent `pool.copy(original)` ou `copy(original)` avec
  provenance de pool. Le prototype existant de tableaux inline n'est pas modifié.
- Le partage d'un nom entre champ et méthode a finalement été refusé.
- L'emprunt automatique du receveur a été accepté ; un transfert du receveur
  reste visible avec `(-> valeur).methode()`.
- La proposition UTF-8 n'a pas reçu d'accord : elle n'est pas ajoutée aux règles.

## Interactions à vérifier ultérieurement

Scénarios de conception, non exécutés :

1. Construction nommée : omissions avec/sans défaut, doublons, champs inconnus,
   types incompatibles et effets d'arguments gauche → droite.
2. Deux réservations mutables de champs directs disjoints admises ; accès à
   un englobant incompatible refusé ; chemins imbriqués et alias indirects.
3. Résultat pointant un champ direct : porteur réservé ; contrat retournant
   seulement une référence partagée vers une cible extérieure : porteur libérable.
4. Réemprunt d'un champ mutable : conserver la cible et le parent de capacité,
   empêcher usage/remplacement du champ avant dernier usage du résultat.
5. Argument `&mut Struct` impossible pendant un prêt incompatible de champ,
   même si le corps appelé n'accède qu'à un champ distinct.
6. Réaffectation de référence : anciennes dépendances retenues s'il existe
   d'autres prêts ; nouvelle cible valide sur tous les chemins.
7. Extraction non Copy refusée directement, dans une branche, par un appel ou
   à travers un chemin imbriqué ; pas de nettoyage partiel à générer.
8. Remplacement complet : nouvelle allocation avant destruction de l'ancienne,
   pression de capacité, refus en présence d'un futur usage emprunté de l'ancienne.
9. Copie : nouvelles identités de slots et contenu indépendant ; champs
   références partagées encore dépendants des cibles ; champ &mut non copiable.
10. Méthodes : emprunt automatique compatible avec la signature et les prêts ;
    consommation sans flèche et collision de nom champ/méthode refusées.
11. Contrats et transferts enfant → parent, tableaux contenant des structures,
    champs tableaux et captures async : règles existantes à composer, sans
    assimiler leurs preuves antérieures à des preuves de ces nouveaux cas.

## Questions et limites

La grammaire et le backend restent à implémenter. La distinction de `copy` entre
valeurs inline et allocations avec provenance doit être intégrée sans changer
silencieusement les règles déjà retenues pour les tableaux. Les détails ABI,
modules, visibilité, surcharge et destructeurs personnalisés ne sont pas réglés
par ces décisions. Aucun gain de sûreté globale ou de fiabilité de génération
par IA n'est démontré par cette seule consignation.

## Vérifications de cette passe

Un contrôle documentaire vérifie les identifiants, leurs entrées dans la matrice,
les fichiers visés par les liens locaux et les délimiteurs des blocs de code.
Il ne vérifie ni les ancres Markdown ni la sémantique ou l'exécution des snippets.
Résultat exécuté : 22 identifiants ST/ME uniques et I6, 23 lignes correspondantes
de matrice (22 N et un objectif A), 151 liens locaux vers des fichiers existants,
et blocs de code équilibrés dans les cinq documents concernés.

Programmes compilés/exécutés, tests de langage, modèles indépendants, génération,
mutations et sanitizers : aucun dans cette passe. ST1–ST18 et ME1–ME4 sont
non implémentés et non vérifiés par exécution ; I6 est un objectif de conception,
sans preuve générale de correspondance intention/code.

## ST7 et ST10–ST13 — Déréférencement explicite d’un champ partagé

`print(*v.inner.target)` était refusé pour un champ `&Int`.
Le compilateur le traitait comme un réemprunt de champ mutable.
Il réutilise désormais la lecture vérifiée du champ partagé pour
obtenir sa cible avant de charger l’Int. La lecture garde la
résolution du chemin, les cibles possibles et leurs restrictions.
Le résultat scalaire est indépendant du porteur et de la cible.

Le test exécute les lectures directe et via une fonction, change
la cible, détruit l’ancienne cible, puis utilise le scalaire après
destruction du porteur et de la nouvelle cible. Drop et reset de
la nouvelle cible avant sa dernière lecture sont refusés, comme
la tentative d’en tirer un réemprunt mutable. Cinq tests ciblés
passent sous Clang C11, -O2 et UBSan fatal. La désactivation de
la branche ajoutée, dans une copie temporaire, reproduit le
refus de l’appel valide. Aucun nouveau modèle indépendant.
La suite des fondamentaux est en cours. Le prêt d’une
sous-structure inline entière reste ouvert.

### Réemprunt partagé explicite et contrat détaché

`&*v.view.target` suit le même chemin de provenance que la référence
partagée stockée dans le champ. L’analyse des contrats conserve la
cible extérieure avec `detached_field_parameter`. Le vérificateur
des arguments évalue aussi ce réemprunt comme une référence, y compris
pour les projections nominales mutables déjà prises en charge.

L’oracle natif exerce le passage immédiat en argument, le retour via
deux fonctions, la réaffectation du champ, le drop et le réemploi du
porteur dans un pool de capacité un. Il lit ensuite l’ancienne et la
nouvelle cible. Écriture sur l’ancienne cible, drop de la nouvelle et
reset prématuré du pool sont refusés. L’écriture après dernier usage
passe. Quatre tests ciblés passent sous UBSan fatal, dont une mutation
d’un champ d’agrégat via un réemprunt mutable passé directement à
une fonction. La désactivation de l’inférence du contrat détaché
dans une copie temporaire réintroduit le refus du retour valide.
L’exécution des tests de champs élargis a été lancée. Aucun nouveau
modèle indépendant. Les emprunts de sous-structures inline entières
restent ouverts.

### Réaffectation conditionnelle avant retour du réemprunt

Les 72 tests de champs lancés au cycle précédent passent. Un oracle
supplémentaire exécute les deux branches d’une réaffectation
conditionnelle via un relais synchrone. Le contrat contient exactement
l’origine du champ avant l’appel et celle du paramètre affecté.
Le porteur est détruit avant lecture du résultat. Dans le profil
historique, les deux pools distincts sont protégés jusqu’à cette
lecture et leur reset est permis ensuite. Deux exécutions natives
sous UBSan et quatre refus statiques ont passé. Les suites plus
larges encore en cours couvrent des révisions antérieures.

### Réemprunts mutables de champs distincts dans un appel

Un oracle combine ST7, ST11–ST12 et B4a. Il passe deux champs
`&mut Leaf` issus d’un même porteur à une fonction qui écrit sur
les deux cibles et retourne son premier argument. Les deux ordres
d’arguments passent en C sous UBSan fatal. Après le retour, le
champ frère est réempruntable et la cible retournée reste accessible
par le résultat. Pour chacun des deux ordres, un doublon dans
les arguments, un réemprunt concurrent du champ réservé et la
destruction prématurée du porteur sont refusés.

Une mutation remplace les réservations par champ par la seule
ascendance du porteur. Elle change le diagnostic de destruction
prématurée, mais les cas invalides restent rejetés. L’oracle
distingue donc le diagnostic, sans mettre en évidence de
différence d’acceptation pour cette mutation.

### Résolution de la méthode join selon le receveur

Un `impl Point` pouvait déclarer `join`, mais `p.join()` était
interprété comme l’attente d’un handle. La résolution utilise le
type du receveur et son contrat, y compris dans un argument
emprunté. Le calcul de dernière utilisation compte le receveur
de cette syntaxe. Le véritable join d’un handle reste couvert
par la régression async.

Sous UBSan fatal, l’oracle lit le résultat de `join` comme argument
direct et via un relais, puis modifie le champ après le dernier
usage. Drop prématuré et écriture pendant le prêt sont refusés.
Désactiver la résolution typée dans une copie temporaire reproduit
le diagnostic réservé aux handles. Les tests ciblés passent.
La suite globale de la révision antérieure sur la provenance async
termine avec 1 420 tests réussis. La suite élargie des méthodes
sur cette révision est en cours. La syntaxe spéciale de
`split_at_mut` peut encore masquer une méthode homonyme.

### Résolution de split_at_mut selon le receveur

Le parseur conserve la forme de découpe à un argument comme
candidate de méthode. Il accepte les autres arités comme appels
ordinaires et laisse le type du receveur déterminer la signature.
Les contrats distinguent ainsi la méthode de structure et la
partition de Vector. Un résultat de partition ignoré reste refusé.

L’oracle natif appelle une méthode mutable sans argument, relaie
un prêt obtenu par la méthode homonyme à un argument d’un autre
type, puis exerce les deux moitiés d’un Vector dans le même
programme. Les arités incompatibles et la mutation prématurée
de la cible du prêt sont refusées. Retirer la résolution de la
forme à un argument dans une copie temporaire fait perdre le
type de retour du relais et reproduit le refus du programme valide.
La sélection des tests de découpe passe sous UBSan fatal. Les
20 tests de méthodes et les 416 tests des fondamentaux passent
sur les révisions antérieures correspondantes. La suite globale
de cette révision a été lancée.

### Méthodes homonymes dans les bras de match

Le vérificateur préliminaire des bras reconnaît les appels
`join` et `split_at_mut` sur une projection de structure.
Il utilise le résultat du contrat, puis le vérificateur
ordinaire applique les droits d’accès et le suivi du réemprunt.

Cinq tests ciblés de match passent sous UBSan fatal. L’oracle
paramétré compare `edit`, `join` et `split_at_mut` sur la
même projection. Il accepte la mutation après dernier usage
et refuse une écriture prématurée ou un appel mutable sur un
porteur emprunté en lecture. Restreindre la reconnaissance
à la forme syntaxique ordinaire dans une copie temporaire
réintroduit le refus des deux homonymes. La sélection élargie
des tests de match est en cours. Aucun nouveau modèle indépendant.

### Réemprunt de méthode retourné par le match

Le test de retour depuis `match &mut` exerce désormais les trois
formes `edit`, `join` et `split_at_mut`. Dans chaque cas, le prêt
vers le champ traverse la sortie du bras puis deux contrats
synchrones. La modification via le résultat est observable sous
UBSan. Le drop du porteur, le reset du pool de la cible dans le
profil historique et une mutation concurrente de la cible sont
refusés avant le dernier usage. Les trois variantes natives et
les neuf refus passent. Les suites plus larges sont toujours
en cours sur les révisions précédentes.

La sélection élargie de la révision précédente a terminé avec
85 tests de match réussis. Les variantes supplémentaires de
retour des deux homonymes ont été exécutées séparément.
