[English](MATCH_MUTABLE.md)

# Validation du match mutable

**Actualisation des emprunts mutables :** [MA1–MA6](MUTABLE_ACCESS-fr.md)
remplace l’exclusivité déduite du seul `&mut`. Les exemples et verdicts d’exclusion
rapportés dans les anciens cycles ci-dessous sont historiques ; ils ne définissent
pas la compatibilité actuelle des accès. Permissions, validité, synchronisation
et fins de branche se vérifient séparément.


`match &mut writer` réserve l'accès au porteur jusqu'à la fin du bras. Chaque
liaison de champ `&mut Int` peut écrire dans sa cible avec `.set()`. Le porteur
reprend ensuite la protection de cette cible jusqu'à son dernier usage ou
celui d'une référence vers lui. P9 précise cette extension de B1 et B2.

Le vérificateur utilise une réservation dans le cadre des emprunts pendant
le bras. Le C généré charge le pointeur stocké dans le champ et écrit dans
l'Int référencé. Les bras sont exhaustifs et autorisent les lectures,
les copies scalaires, les blocs et les écritures par projection. Ces écritures
n'ajoutent aucune transition de propriété ou d'état du nettoyage à fusionner.

## Cas et limites

- Une allocation soumise à un match mutable exige `let mut`. Un emprunt
  mutable existant, par exemple un paramètre `&mut Writer`, suffit aussi.
- Le modèle de test place la lecture d'origine avant ou après deux frontières,
  la fin du bras et le dernier usage du porteur. Une lecture dans le bras
  échoue même après le dernier `.set()`. Après les deux frontières, elle lit
  la nouvelle valeur.
- Un retour conditionnel peut permuter les cibles de deux champs. Les deux
  cibles sont distinctes dans chaque exécution mais leurs ensembles statiques
  se recouvrent. Le prototype refuse les deux projections utilisées dans le
  même bras. La projection d'un seul champ est vérifiée et exécutée. Cette
  restriction de l'analyse conserve la représentation actuelle des provenances.
- Les champs partagés et les copies scalaires restent lisibles. La projection
  demeure dans son bras. Les bras gardent une grammaire restreinte. La section sur les appels Void
  décrit son extension ultérieure.

## Observations exécutées

Les 10 tests dédiés incluent 9 sources distinctes admises et exécutées ainsi
que 19 sources distinctes refusées par `verify_program` et `compile_source`.
Ils vérifient aussi les adresses du porteur et de la cible, la mutation à travers
deux appels successifs, le refus d'un drop ou reset prématuré, le nettoyage
unique et les variantes présentes ou absentes à l'exécution.
La suite globale passe 739 tests en 309,930 s. La configuration
`CRUST_SANITIZE=undefined` passe 67 tests en 31,921 s avec le motif
`test_mutable*.py`. Les deux suites se terminent sans test ignoré.

Trois injections ciblées sur des copies sont détectées. Remplacer la
réservation du sujet par un cadre vide admet une lecture prématurée.
Remplacer le mode de la projection par `ref` refuse une écriture valide.
Supprimer le paramètre `write=node.mutable` du contrôle d'accès du sujet
admet des entrées sans droit d'écriture et peut déclencher l'invariant
d'exclusivité en présence d'un alias partagé.

Deux programmes ont été exécutés en C avec Clang en `-O0`, `-O2`, `-Os` et
`-O2 -fsanitize=undefined -fno-sanitize-recover=all`. Les huit exécutions
confirment les valeurs et les destructions attendues. La première source
utilise la cible après le match, la seconde après le dernier accès au porteur.
[Sources et sorties brutes](../validation/mutable-match-targeted.json).

## Réexamen des règles

I1–I5 et V1–V5 encadrent l'emprunt explicite, les copies et l'écriture sur
place. S1–S6, T1–T11 et U1 encadrent la fin de scope et le suivi des réceptions
et derniers usages. D1–D4 et B1–B5 encadrent la durabilité, les unions de cibles
et l'accès exclusif pendant les appels. L1–L7, A1–A6, P8–P9 et E1 encadrent
les pools, la libération et le nettoyage. P1–P7 et E2 restent couverts par les
règles existantes de placement et de stockage. Les deux modèles de test
exercés ici sont le modèle à deux frontières et le cas de permutation des
cibles, avec des résultats attendus calculés à partir de l'ordre des usages
et de la variante construite.

Les tests et les injections échantillonnent ces interactions. La corrélation
entre cibles conditionnelles, les écritures autres que `.set()` dans un bras
et les autres compilateurs C restent hors de cette campagne. UBSan couvre les
exécutions instrumentées. ASan, déjà indisponible sur l'hôte lors du cycle
précédent, n'a pas été rejoué.

## Appels Void dans un bras

Une projection peut être fournie par son nom à un paramètre d'emprunt
compatible. L'appel suspend la projection pendant le réemprunt et le bras
peut l'utiliser au retour. Le porteur reste réservé pendant l'appel et
jusqu'à la sortie du bras. L'interface de cette étape limite les arguments
aux projections nommées et le résultat à Void. Cette limite permet à la
fonction d'utiliser son propre stockage local tout en conservant les
provenances et le nettoyage des allocations du bras.

Le modèle de test place les accès à la cible dans le bras après le retour,
après le bras avant le dernier usage du porteur, puis après la fin de la
protection. Le retour de l'appel restaure la projection et laisse les deux
premiers accès interdits. Les tests combinent un relais par sous-appel, un
bloc dans le bras, des écritures successives, le contrôle de l'aliasage et
du mode, le reset après usage et la destruction unique. Un appel dans un
bras impossible est contrôlé sur ses types et ses modes à partir de la
déclaration des champs. Le compilateur spécialisé ne génère aucun appel
pour cette projection sans cible. Un appel qui diverge termine uniquement
son bras quand une autre variante peut continuer.

Le cycle ajoute 6 tests dédiés. Ils couvrent 4 sources distinctes admises
et exécutées et 11 refusées par les deux stages. Trois injections sont
détectées sur des copies, portant sur la réservation du porteur, le mode
partagé et la disponibilité du type dans un bras impossible. Le C généré
pour le relais et les écritures après appel produit les valeurs et traces
attendues sous Clang en O0, O2, Os et O2 avec UBSan. Les substitutions et
observations sont conservées dans
[les résultats bruts](../validation/mutable-match-calls.json).

Les interactions P9 et B1–B5 concernent l'exclusivité, la reprise de la
projection et le résultat Void. S4 et S5 bornent le bras et l'appel, D1–D4
et T9–T11 encadrent les cibles possibles, V4 et V5 encadrent l'écriture en
place. L1–L7, A2 et A5 encadrent le nettoyage après la fin de la protection.
Les autres familles du réexamen précédent restent couvertes par la
régression globale. Les appels à résultat et les arguments autres que les
projections relèvent de décisions ultérieures. Les quatre exécutions C
couvrent une famille de compilateurs et un seul programme composé.

La régression globale passe 745 tests et la configuration UBSan ciblée
passe 73 tests avec le motif `test_mutable*.py`. Les six injections
précédentes sur les champs mutables sont détectées après actualisation
du point d’injection du parent de projection. Les deux suites terminent
sans test ignoré. UBSan instrumente les binaires des tests concernés.

## Résultat Int reçu dans le bras

`let valeur = lire(vue)` reçoit un Int copié dans une liaison locale.
L'appel garde les règles de passage par nom des projections. Le bras peut
réutiliser la projection au retour. La valeur copiée reste disponible après
une nouvelle écriture par la projection, sans prolonger son emprunt.
La réservation du porteur couvre toujours le bras.

Les tests lisent 10 via une projection passée à un paramètre `&Int`, écrivent
20 via la même projection, puis observent 10 dans la copie et 20 dans la
cible. Le nom local est refusé hors du bras. Un accès direct à la cible reste
interdit dans le bras après la copie. Un bras impossible conserve le type
du résultat sans exécuter l'appel et reste soumis à la vérification de
l'arité. Le résultat Int suit les règles de copie de V3 et d'appel de B4
ainsi que la portée du bloc de S4. Les règles d'exclusivité et de nettoyage
ont la même application que pour les appels Void.

La suite globale passe 747 tests et la suite ciblée sous UBSan en passe 75.
Le corpus ciblé comprend 6 sources distinctes admises et exécutées et
14 refusées par les deux stages. Les quatre exécutions C en O0, O2, Os et
O2 avec UBSan confirment les valeurs et l'ordre de destruction du cas
de copie. L'injection qui supprime le résultat typé du bras impossible
est détectée. [Résultats bruts](../validation/mutable-match-int.json).

## Réemprunt mutable reçu dans le bras

Une déclaration `let mut autre = reemprunter(vue)` reçoit un `&mut Int`.
La chaîne d'emprunts du résultat conserve la projection parente et la
réservation du porteur. Tant qu'un usage de `autre` reste à venir, une
lecture, une écriture ou un appel utilisant `vue` est refusé. Après le
dernier usage, `vue` peut de nouveau servir dans le même bras. La liaison
reçue reste locale. Les appels du bras peuvent prendre son nom comme
argument, avec les mêmes contrôles de mode et d'exclusivité.

Les scénarios opposent le même accès au parent placé avant ou après le
dernier usage de l'enfant, avec un retour relayé par une deuxième fonction.
Ils vérifient également que l'accès d'origine à la cible reste bloqué et
que la liaison ne se résout pas hors du bras. Dans un bras statiquement
impossible, le type du résultat est conservé pour vérifier les opérations
sans inventer de cible. Les conflits de durée de vie du résultat y
reposent sur l'impossibilité du chemin, alors que les chemins exécutables
sont vérifiés sur leurs cibles effectives ou possibles.

Les règles B1, B2, B4 et B5 se combinent avec S4 et P9. Le résultat ne
modifie ni la durée de vie de la cible ni la responsabilité du nettoyage.
D1–D4 et V5 continuent de s'appliquer à sa provenance et à son identité.
Les règles de transfert, de destruction et de pool sont couvertes par la
suite globale. La section suivante décrit l'extension qui permet de
recevoir cet emprunt hors du bras.

La suite globale passe 749 tests et la suite ciblée sous UBSan en passe 77.
Le corpus ciblé comprend 8 sources admises et exécutées et 19 refusées par
les deux stages. Quatre exécutions du C généré en O0, O2, Os et O2 avec UBSan
donnent les valeurs et la trace de destruction attendues. Une injection
qui ignore le résultat encore actif lors d'un accès au parent est détectée.
[Résultats bruts](../validation/mutable-match-return.json).

## Résultat mutable reçu après le match

```rust
let mut dehors = match &mut writer {
    Writer.Bound { data: vue } => {
        let mut autre = reemprunter(vue);
        autre
    }
};
dehors.set(30);
print(writer);
```

Inverser les deux dernières instructions fait refuser la lecture de
`writer`. Le résultat transporte ses cibles possibles et une réservation
du porteur. La réservation suit aussi les réemprunts dérivés du résultat.
Le C place le pointeur choisi dans une variable locale avant de quitter le
bras. Le vérificateur contrôle la durée de vie du porteur et des cibles
dans la portée de réception. Les contrôles d'accès, de déplacement et de
reset consultent cette réservation, y compris pour les autres champs
dont dépend le porteur.

Le modèle des tests distingue un usage restant et un usage terminé. Il
exerce la lecture du porteur, sa réaffectation et les destructions ou resets
de son pool et de celui de la cible. Une variante conditionnelle peut
sélectionner des cibles distinctes. Le résultat protège leur union et le C
modifie la seule cible choisie à l'exécution. Un appel opaque ne peut pas
réinitialiser une source du porteur ou de ses dépendances quand il reçoit
le réemprunt. Cette restriction historique a été affinée par les contrats d'ordre
décrits dans la dernière section.

Cette extension couvre la réception par `let mut` et le passage du résultat
aux appels compatibles. La section suivante étend la réservation au
retour de fonction pour un porteur emprunté en paramètre. La dernière section
étend ce périmètre au stockage du résultat dans un champ. Les bras exigent un nom final et vérifient son type.
Les cibles des variantes statiquement impossibles ne contribuent pas
au résultat.

P9, S4, B1, B2, B4 et B5 encadrent la portée et le dernier usage. D1–D4,
T9–T11 et V5 encadrent les cibles possibles, leur durée de vie et leur
identité. A2, A5 et L1–L7 encadrent le nettoyage. Le test par injection
qui retire le prêt du porteur détecte l'acceptation erronée de
`print(writer)` avant le dernier usage. Quatre configurations Clang
confirment les valeurs et la destruction dans le cas accepté.
[Cas, injection et sorties brutes](../validation/mutable-match-escape.json).

Les 7 tests dédiés couvrent 6 sources distinctes admises et exécutées et
14 refusées par les deux stages. La régression globale passe 756 tests et
la suite ciblée sous UBSan en passe 84, sans test ignoré. Le C a été
exécuté en O0, O2, Os et O2 avec UBSan sur une famille de compilateurs.

## Retour depuis un porteur emprunté en paramètre

Une fonction `ouvrir(writer: &mut Writer) -> &mut Int` peut retourner
le résultat de son match. Le contrat décrit chaque origine par le numéro
du paramètre porteur et le nom qualifié du champ. Il conserve ces origines
à travers les appels relais, même lorsque le porteur change de position
dans la signature. Chez l'appelant, le vérificateur résout le champ vers
ses cibles et recrée la réservation du porteur. Les variantes absentes de
l'allocation réelle sont écartées. Le backend vérifie que les cibles et
les porteurs observés dans le corps figurent dans le contrat.

Le modèle de dernier usage distingue `print(writer); dehors.set(30);`,
qui est refusé, de l'ordre inverse, qui affiche `Writer.Bound(30)`.
La même réservation bloque la destruction du porteur et le reset de
son pool. Les cibles restent protégées contre ces opérations. Un porteur
local est refusé même si son champ pointe vers une allocation de
l'appelant. Un porteur reçu par transfert est également refusé.

Les scénarios couvrent les modes et les retours de B1–B5, la durée de
vie et la provenance de D1–D4, les variantes de P9 et les effets de reset
et de destruction de A5 et L1–L7. Le résultat conserve une union statique
des champs possibles lorsque la variante est inconnue. La dernière section traite le stockage dans un champ et
la composition avec les resets.

Les six tests dédiés couvrent cinq sources distinctes admises et exécutées
et neuf refusées par les deux stages. La suite globale passe 762 tests et
la suite ciblée sous UBSan en passe 90, sans test ignoré. Quatre exécutions
du C en O0, O2, Os et O2 avec UBSan donnent les valeurs et les destructions
attendues. L'injection qui omet la réservation du porteur dans le contrat
de retour est détectée. [Résultats bruts](../validation/mutable-match-function-return.json).

## Réservations transitives et ordre des resets

Un champ peut conserver un emprunt retourné par `ouvrir`. Les prêts du
porteur sont reconstruits à partir de la chaîne, y compris pour un objet
retourné par une fonction. Un transfert vérifie la durée de vie des
porteurs dans sa destination. Les retours conditionnels conservent tous
les porteurs possibles et l'exécution n'écrit que dans la cible choisie.
Les contrats d'objets distinguent un champ qui transmet un emprunt
existant d'un champ qui réserve un porteur emprunté en paramètre.

Le contrat de contraintes distingue les sources des paramètres et
celles de leurs réservations. L'analyse mémorise les resets susceptibles
de précéder chaque usage. Deux branches exclusives peuvent l'une
réinitialiser et l'autre écrire. Après leur jonction, un usage de la vue
exige la disjonction avec les sources réinitialisées sur un des chemins.
Les retours de boucle transportent le même historique. La composition
substitue les sources aux contraintes des sous-appels dans l'ordre.
Le vérificateur du site d'appel consulte les contrats. La génération C
conserve ses vérifications lors de la spécialisation.

Le contrat garde l'effet de reset possible pour invalider chez
l'appelant les porteurs qui peuvent avoir été détruits. Le vérificateur
protège les emprunts que l'appelant réutilisera et les arguments déjà
préparés. Ces contrôles s'appliquent aux dépendances transitives.

Le modèle d'ordre du test oppose deux séquences, usage puis reset et
reset puis usage, en opérations directes et en sous-appels. Le test
contrôle aussi le contrat inféré indépendamment de l'exécution du C.
Les scénarios séparés exercent la jonction de branches, le retour de
boucle, l'emprunt qui n'est pas un argument de l'appel, l'argument déjà
préparé, la chaîne de porteurs et l'union de deux origines. Un essai
préliminaire a révélé un double comptage du prêt d'un porteur lorsque
le relais revenait par un contrat de résultat alloué. La reconstruction
écarte le prêt du parent au profit du prêt transmis dans ce cas.

B1–B5 et P9 encadrent la chaîne des prêts. D1–D4, T5 et T9–T11 encadrent
la durée de vie et la provenance à chaque transfert. S4 et S5 encadrent
les chemins et reprises, B4a la préparation des arguments, A5 et L1–L7
le reset et le nettoyage. Les sources possibles et les chemins rejoints
restent traités par union. Le contrat peut donc refuser une combinaison
qui nécessiterait de prouver une corrélation entre deux conditions
distinctes. La comparaison C porte sur une famille de compilateurs.

La régression globale passe 771 tests et la suite ciblée sous UBSan en
passe 99. Les neuf tests dédiés couvrent 12 sources distinctes admises
et exécutées et 20 refusées par les deux stages. Les deux injections
sont détectées. Elles omettent respectivement les contraintes d'ordre
aux appels opaques et les prêts des porteurs transitifs. Les huit
exécutions C couvrent deux programmes en O0, O2, Os et O2 avec UBSan,
avec contrôle des valeurs et de la trace de destruction.
[Sources et résultats bruts](../validation/mutable-match-reservations.json).
