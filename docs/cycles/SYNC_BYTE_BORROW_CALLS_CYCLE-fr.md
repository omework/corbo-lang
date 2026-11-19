[English](SYNC_BYTE_BORROW_CALLS_CYCLE.md)

# Cycle — appels synchrones avec emprunts partagés u8

## Exigences et périmètre

Suite de [SYNC_BORROW_CALLS_CYCLE.md](SYNC_BORROW_CALLS_CYCLE.md), sans modification
normative. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept brouillons,
B1–B5, D1/D3 et AS1/AS2 ont été reconsultés, ainsi que TX1/TX2/TX5/TX12 dans
UTF8_STRINGS.md. Le mécanisme de contrats existant reste la source du contrôle
à l’appel ; les corps servent ensuite à la génération du C.

Les appels depuis les états async et les blocs natifs prennent désormais des
paramètres et résultats `&u8`. L’ABI utilise un `const unsigned char *` direct,
avec une place symbolique empruntée pour la génération synchrone. Aucun octet
ni allocation n’est copié pour matérialiser la référence.

Les arguments peuvent être des références nommées, des octets de littéraux,
de tableaux et de String, un réemprunt partagé de `&mut u8` (nom passé directement à un paramètre partagé ou `&*` explicite), un résultat
synchrone emprunté ou une variable locale u8 explicitement empruntée par `&`.
L’accès à une référence n’est pas aplati par un second `&`. Le pointeur et les
prêts sont préparés avant l’argument suivant ; la suspension d’un argument
ultérieur ne les libère pas. Un return interrompant la préparation n’appelle
pas la fonction externe.

Le résultat substitue les cibles `utf8_parameter` du contrat aux prêts des
arguments effectivement préparés. Les deux cibles de `choose` sont conservées ;
le second paramètre de `first` n’est pas conservé après l’appel. Le suivi des
résultats async compose désormais ces contrats, y compris à travers un enfant.
Cette précision n’écourte pas les captures pendant l’exécution : elle concerne
les prêts restant attachés au résultat après sa terminaison.

Un emprunt d’un octet local dans l’état ne peut être retourné. Les dépendances
protègent aussi contre le drop, les mutations et les réemplois prématurés après
`join`. Le contrôle de reset est seulement exercé dans le profil historique
`allow_legacy_reset=True` ; reset reste retiré de l’API du prototype.

## Contre-exemples et raccordements supplémentaires

La sonde conservée dans `validation/sync-byte-artifacts.log` révélait un refus
valide : le prépassage des blocs natifs ne déduisait pas `&u8` depuis `&a[0]`
lorsque `a` était un String. L’indexation de str, String et Vector<u8> est
maintenant reconnue comme u8. Le prépassage préserve également le `&` dans
le type de résultat de join pour les modes text et byte_ref. Il reste un
prépassage de types : la vérification mémoire ordinaire contrôle les captures.
Le cas String est exécuté et décliné avec drop prématuré refusé.

Les premières fixtures comportaient quatre problèmes distincts de compilateur :
yield dans un bloc natif, print direct d’un String, un marqueur BEFORE laissé
dans le cas admis, et un drop d’une variable du parent dans un bloc argument
sans transfert d’entrée. Ils ont été corrigés selon les règles existantes.
Une édition trop large avait ensuite changé le print d’un paramètre Int en
vue String ; ce défaut de fixture est aussi conservé dans les journaux initiaux.
Aucune attente sémantique n’a été modifiée pour rendre une implémentation fautive
acceptable.

## Vérification et oracles

`tests/test_sync_byte_borrows.py` contient douze méthodes : dix-neuf compilations
et exécutions C attendues valides et quarante-sept variantes attendues refusées,
plus deux vérifications positives sans C (contrat opaque et reset historique).
Les valeurs et contraintes attendues sont écrites sans consulter les résumés
inférés. Les choix 0/1 de `choose` doivent rendre 7/8 ; `first` garde uniquement
la première source. Les séquences imposent une lecture avant libération, une
mutation après dernière utilisation et le réemploi effectif d’un pool de
capacité un. L’échec de pthread_create injecté doit rendre Err et permettre
le nettoyage.

Interactions examinées : B1–B5 × AS2/AS9/AS12/AS15 × L6 × MT6/RT8 × TX5 ;
arguments suspendus et interrompus, appels imbriqués, parents mutables,
continuations et retours de boucle, capture et retour d’un enfant, join,
source du résultat, drop/reset et réemploi. Les tests existants de vues UTF-8
et de prêts Int/mutables sont réexécutés. Les modèles d’alias et transactions
UTF-8 existants sont inclus dans la sélection UTF-8 ; aucun nouveau modèle
général de concurrence ni preuve formelle n’est revendiqué.

Les C passent par Clang, C11, pthread, `-Wall -Wextra -Werror`,
`-Wno-unused-function`, `-fsanitize=undefined -fno-sanitize-recover=all`,
aux niveaux indiqués ci-dessous. Pas de nouvelle preuve ASan/TSan ni d’un
second compilateur. Les blocages ASan des cycles précédents restent des limites.

## Mutations et artefacts

`tests/run_sync_byte_mutations.py` exige d’abord une baseline verte. Les cinq
copies temporaires perdent respectivement : le prêt d’argument préparé, la
seconde cible d’un retour, le bon pointeur rendu, la sélection précise des
paramètres dans le résultat async, et le prêt d’un u8 local. Les cinq fautes
sont détectées. L’ignorance du contrat produit un faux refus du programme
valide qui détruit la source non retournée : c’est une détection sémantique,
pas une preuve de sécurité. Les tests ne sont pas modifiés dans ces copies.
Aucun taux général de détection ne se déduit de ces cinq mutations choisies.

Le runner des mutations du cycle précédent a d’abord arrêté sur une ancre
non unique, après sa baseline verte. Le nouveau branchement byte_ref contient
aussi `loans.extend(held)`. L’ancre est maintenant qualifiée par l’appel à
`sync_borrow_argument`. Cet arrêt est une campagne non exécutée, pas une
mutation détectée. Le journal initial est conservé séparément.

`validation/sync-byte-native-return.crust` et son C sont conservés.
`validation/sync-byte-native-artifacts.log` montre la sortie 65 puis B,
une destruction/récupération de chacun des String a/b et l’ABI de pointeur
partagé. Le test alloue b dans le pool de capacité un après destruction de a.

## Limites et suite

Les paramètres propriétaires des appels synchrones depuis les états, les
agrégats généraux, les pools créés directement dans ces états et les autres
écarts des sept brouillons restent ouverts. Ce lot raccorde &u8 ; il ne
prétend pas généraliser toutes les signatures de vues, de champs ou de
conteneurs. Les données de preuve finies ne démontrent pas la sûreté générale.

## Diagnostic de régression UTF-8

La sélection de quatre-vingts méthodes a terminé avec un échec d’assertion
sur le texte d’un diagnostic. Le programme était bien refusé. Le remplacement
`return &t[1]` → `return t[1]` dans la fixture modifiait simultanément leaf
(async) et octet (synchrone). L’inférence du contrat d’octet rejetait son retour
u8 au lieu de &u8 avant le diagnostic async attendu. La fixture modifie
maintenant seulement la première occurrence, celle de leaf, en conservant
l’exigence de refus et son diagnostic. Le journal de cette régression reste
conservé ; le test corrigé est réexécuté dans le lot ciblé final.

La précision supplémentaire pour les arguments nommés &mut u8 s’applique
lorsqu’un &u8 est attendu. Elle ne change pas l’inférence générale du type
d’une variable mutable en type partagé. Les tests couvrent les deux notations
(parent et &*parent), leur usage puis la reprise de mutation, et les conflits
avant le dernier usage.

## Résultats exécutés

| Campagne | Résultat | Journal dans validation/ |
| --- | --- | --- |
| Régression native O2 avant les derniers raccordements de type/capacité nommée | 119 méthodes, 175,793 s, OK | `sync-byte-regression-o2.log` |
| Sélection UTF-8 O2 | 80 méthodes, 167,596 s, un échec de diagnostic de fixture décrit ci-dessus | `sync-byte-utf8-regression-o2.log` |
| Lot u8 + parser natif O0 puis O2, après correction de type natif | 18 méthodes, 13,723 s / 18,248 s, OK | `sync-byte-final-o0.log`, `sync-byte-final-o2.log` |
| Union des deux pools à travers join, ajout ultérieur | Une méthode à O0 et O2, OK | `sync-byte-conditional-o0.log`, `sync-byte-conditional-o2.log` |
| Lot u8 complet, avec arguments mutables nommés | 12 méthodes O0, 10,885 s, OK | `sync-byte-named-parent-o0.log` |
| Lots u8 et Int/mutables réunis | 28 méthodes O2, 20,755 s, OK | `sync-byte-named-parent-o2.log` |
| Contrôle final après restriction de la conversion au contexte attendu | 15 méthodes O2, 16,805 s, OK ; test de parent partagé O0, 1,570 s, OK | `sync-byte-final-interactions-o2.log`, `sync-byte-final-shared-o0.log` |
| Mutations finales &u8 O2 | Baseline complète 12 méthodes verte, cinq fautes détectées | `sync-byte-final-mutations-o2.log` |
| Mutations antérieures Int/mutables réexécutées | Baseline 16 méthodes verte, cinq fautes détectées | `sync-byte-borrow-final-mutations.log` |
| Inspection d’artefact natif O2 | 65 puis B, destructions et réemploi du pool, pointeurs C const | `sync-byte-native-artifacts.log` |
| Syntaxe Python et liens locaux | Huit fichiers Python, aucun lien local manquant | `sync-byte-structural-checks.log` |

Le passage final de quinze méthodes contient les douze méthodes u8 courantes,
le test UTF-8 corrigé et deux tests existants de prêts/reprises u8. Les autres
méthodes de la sélection de quatre-vingts ne sont pas prétendues réexécutées
après ces derniers raccordements. Les journaux intermédiaires et les échecs
restent disponibles. Le diff d’implémentation et des nouveaux tests est conservé
dans `validation/sync-byte-implementation.patch`.

Le prochain raccordement identifié reste le transfert de paramètres propriétaires
aux auxiliaires synchrones depuis un état, avec nettoyage des arguments préparés
et restitution éventuelle des identités. Le présent cycle ne clôt pas l’objectif
d’intégration de l’ensemble des sept brouillons.

Suite implémentée : [transferts propriétaires aux auxiliaires](SYNC_OWNED_CALLS_CYCLE.md). Les limites précédentes décrivent l’état de ce cycle.
