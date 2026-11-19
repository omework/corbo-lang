[English](ASYNC_LOCAL_CAPTURES_CYCLE.md)

# Structures locales capturées par les tâches enfants

## Périmètre et règles

Ce lot applique les brouillons 03/04/05/07, T1/T6, V5, L1/L2/L7,
B1/B2/B4, AS2/AS8/AS9/AS12 et les règles ST17/ST18 de copie. Il ne modifie
aucune règle normative. Il étend les familles de structures déjà prises en
charge par le backend async ; il ne rend pas tous les agrégats compilables.

Le cas conservé dans `validation/open-async-local-helper-child-capture.crust`
est désormais accepté par les deux étapes et exécuté : une structure construite
localement dans le parent est empruntée par l'enfant, qui suspend puis lit son
champ. Les captures partagées, mutables et propriétaires, leurs relais, une
copie dans l'enfant et la restitution du paramètre propriétaire sont testés.
Les appels depuis du code synchrone utilisent la même distinction de stockage.

## Implémentation

Le compilateur mémorise une variante par fonction async et ensemble de
paramètres provenant d'une data stack locale. La signature source et le contrat
nominal restent communs. Les appels choisissent statiquement la variante ; le
runtime ne devine pas le type de stockage au moment de l'exécution.

Dans une variante, les paramètres concernés portent une origine externe de
data stack. Cette origine suit les relais et sélectionne les bridges synchrones
adaptés, notamment pour `copy`. Elle n'est pas ajoutée aux sources que l'enfant
doit fermer : le parent conserve la responsabilité du stockage. Les copies
créées dans l'enfant utilisent sa propre plage et sont nettoyées avec son scope.
Les prêts et les sources retenus par les résultats restent suivis séparément.

Les variantes sont générées jusqu'à épuisement des nouvelles demandes. Les
bridges synchrones découverts pendant leur génération sont également émis.
Le nombre de slots internes tient compte du maximum entre les variantes.

**Un seul pool d'états est conservé par fonction nominale.** Lorsque plusieurs
représentations existent, chaque slot utilise une union C contenant les états
possibles. La taille et l'alignement conviennent donc à toutes les variantes.
Elles partagent la capacité, les générations et les entrées de réveil du même
pool. Créer une variante ne multiplie pas la capacité spécifiée par l'utilisateur.

La frontière `T` / `A<T>` reste explicite. Un paramètre déclaré `->A<Point>` ne
reçoit pas une structure locale. Un contre-exemple supplémentaire annonçant
`-> <- A<Point>` tout en retournant son paramètre local a été trouvé et corrigé :
les retours directs et calculés contrôlent maintenant cette distinction.

## Preuves exécutées

`tests/test_async_local_captures.py` contient treize méthodes. Le passage final
O0 réussit en 6,010 s : **14 exécutions natives**, **11 programmes invalides**
contrôlés aux deux étapes (**22 vérifications de refus**).
La baseline finale O2 réussit en 8,149 s. Les compilations utilisent Clang C11,
pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan fatal.

- Capture partagée enregistrée et relais à travers deux enfants.
- Capture mutable : mutation après attente admise ; lecture, écriture ou drop
  concurrents du parent refusés.
- Transfert propriétaire, relais et destruction d'une tâche inactive ; usage
  après transfert refusé.
- Même routine appelée avec une structure locale et une structure de pool,
  avec copies indépendantes et valeurs originales préservées.
- Capacité explicite d'un slot réutilisée pendant quatre tours alternant les
  variantes locale et pool.
- Restitution du paramètre propriétaire à son parent sans double destruction.
- Référence mutable retournée : le parent reste réservé jusqu'au dernier usage.
- Source locale trop courte et substitutions implicites de `T` en `A<T>` refusées.
- Refus de lancement injecté : les captures propriétaires sont détruites une fois.
- Sondes C à la suspension, puis terminaison normale ou destruction exclusive
  d'une tâche non lancée. Elles contrôlent les cellules, les sources distinctes
  de l'original et de sa copie, les valeurs, la fermeture des deux plages et
  le retour des pools d'états à l'état vide. Elles vérifient aussi le pas des
  slots par rapport à la représentation des états.

Les sondes n'ajoutent pas d'annulation publique : elles détiennent exclusivement
une tâche non lancée. Une fois une plage fermée, elles ne lisent plus ses cellules.

Journaux finaux :

- `validation/async-local-captures-counted-o0.log` ;
- `validation/async-local-captures-mutations-final-o2.log` ;
- `validation/async-local-captures-regression-final-o2.log` : **97 méthodes**
  passent en 94,989 s sur le code final, couvrant structures capturées, champs
  empruntés, réemprunts, appels propriétaires, capacités et Select ;
- `validation/async-local-captures-regression-initial-o2.log` : **67 méthodes**
  passent en 62,120 s avant l'ajout de la garde de retour `A<T>`, couvrant les
  résultats locaux, placements parent/boucles, captures et retours propriétaires.

`py_compile` réussit. Les diffs de `crust.py` et `async_lowering.py` sont
archivés sous `validation/async-local-captures-*.py.patch`, par rapport au
snapshot `/tmp/crust-before-async-local-captures/`. Tous les processus cités
sont terminés et leurs résultats ont été récupérés.

## Mutations et échecs conservés

`tests/run_async_local_capture_mutations.py` détecte six fautes finales :

1. Oublier la variante choisie par un appel depuis async.
2. Oublier celle choisie depuis un appelant synchrone.
3. Perdre l'origine locale à l'entrée de l'enfant.
4. Utiliser la taille de l'état ordinaire comme pas de slot malgré une variante
   plus grande.
5. Autoriser le retour d'un local sous un type `A<T>` explicite.
6. Autoriser sa capture sous un paramètre `A<T>` explicite.

Les oracles source et C restent inchangés dans les copies mutées. Les refus
manquants et les assertions de représentation/stockage sont distingués des
corruptions mémoire ; ce petit ensemble ne mesure pas une couverture générale.

Deux mutations ont d'abord survécu : l'oubli du choix de variante depuis async
et la perte d'origine à l'entrée. Le test vérifiait les bonnes valeurs affichées,
mais pas le stockage de la copie. La sonde C a été appliquée à ces mutations :
le stockage doit être distinct et fermé avec l'enfant. La campagne finale les
détecte. Le premier journal `mutations-o2.log` reste conservé.

Le journal `expanded-o0.log` contient un échec UBSan dans le harnais : il lisait
`copy->alive` après fermeture de la plage de la copie. Le contrôle a été déplacé
sur les compteurs de la source, qui résident dans l'état encore observable.
L'oracle conserve la vérification de fermeture et ne déréférence plus une
cellule libérée. `corrected-o0.log` et les passages finaux passent.

Un compteur intermédiaire (`complete-o0.log`) comptait deux fois les appels
passant par `run_native`, qui délègue à `run_c_oracle`. Le passage final ne
compte qu'à cette dernière frontière et établit les **14** exécutions réelles.
Les journaux initiaux et intermédiaires ne sont pas supprimés.

## Écarts encore ouverts

Les résultats sont conservés dans `validation/async-local-captures-remaining.log`.

- `open-async-local-only-copy-annotation.crust` est valide mais encore refusé :
  `leaf(&Point)` copie son paramètre dans `let q:Point`. La variante locale
  convient, mais la validation systématique du corps ordinaire suppose une
  provenance de pool et refuse cette annotation avant de sélectionner les
  variantes réellement utilisables. Il faut traiter les exigences de stockage
  du corps, sans autoriser un appel de pool incompatible ni retirer l'annotation.
- Un résultat nouvellement construit dans la tâche exige encore une destination
  extérieure à l'état pour être transféré hors de celui-ci. La restitution du
  paramètre déjà durable couverte ici ne résout pas ce cas.
- `open-async-return-replaced-owned-field.crust` reste refusé : la mise à jour
  du graphe propriétaire retourné après remplacement d'un champ reste à raccorder.
- Les agrégats généraux avec emprunts, les signatures de handles générales et
  les arbitrages de nettoyage portant un handle lancé restent les limites des
  cycles précédents.

Les modèles, les sondes et les scénarios multithreads sont finis. Aucun nouveau
résultat ASan/TSan ni preuve générale de sûreté n'est revendiqué. L'objectif
complet des sept brouillons reste ouvert.
