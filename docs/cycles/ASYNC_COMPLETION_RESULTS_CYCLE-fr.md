[English](ASYNC_COMPLETION_RESULTS_CYCLE.md)

# Contrats async : résultat emprunté et champs modifiés à la terminaison

## Périmètre

Aucune règle normative modifiée. Ce lot complète l'analyse nécessaire à ST10,
ST11–ST13, B4/B5 et AS12/AS13. Une tâche enfant peut modifier un champ référence
et retourner un emprunt. Son contrat de terminaison doit conserver les deux
informations, y compris quand le résultat désigne la cible précédant l'écriture.
Ce lot ne lève pas le refus du backend pour les remplacements extérieurs : leur
application aux états et aux appelants réels reste ouverte.

`AsyncStructureEffects.completion_result` conserve désormais le contrat de
résultat, en plus des champs modifiés et de la possibilité de terminer.
Les résultats `&Int`, `&mut Int` et `&mut u8` sont collectés avec les contrôles
de provenance ordinaires. Les autres familles non raccordées restent signalées
comme incomplètes ; elles ne deviennent pas des contrats vides.

À l'attente, un adaptateur symbolique sans corps publie le contrat de l'enfant
au moteur de contrats existant. Celui-ci instancie les effets et le résultat
depuis les mêmes arguments sauvegardés à la création. Les provenances des
résultats partagés détachés restent distinctes des réservations de porteurs
mutables. Un résultat de handle garde son enveloppe `join_ref`/`join_mut`.
Un échec de lancement contribue l'état initial des champs, mais aucune cible
de résultat réussi. Une tâche divergente ne crée pas de continuation normale.

## Contre-exemple découvert par le modèle

Le modèle indépendant a trouvé une perte d'effet dans six de ses seize
scénarios. Après `child(v,n).await`, écrire dans `v.spare` reconstruisait parfois
v depuis l'ancien état de son nom visible. La modification de `v.data` par
l'enfant disparaissait alors du résumé final. L'appel symbolique utilisait des
noms temporaires sauvegardés, dont l'état avait été mis à jour, mais ses alias
visibles ne l'avaient pas été.

Après l'application du contrat, les champs des alias du porteur sont désormais
actualisés depuis leur stockage symbolique commun avant de réunir les branches.
Les valeurs d'emprunts détachées avant l'écriture restent des instantanés : elles
ne sont pas remplacées par la nouvelle cible du champ.

Le programme complet conservé dans
`validation/open-async-completion-result-and-write.crust` illustre cette frontière.
Le contrat de child écrit `.data -> n` et retourne l'ancienne `.data` ; celui de
work conserve `.data -> n` et `.spare -> ancienne .data`. Le journal
`validation/async-completion-results-recorded.log` montre ces deux contrats et
le refus conservé de compilation du programme complet. Ce journal n'est pas une
exécution du programme ni une preuve de propagation des effets au runtime.

## Vérification exécutée

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_structure_effects -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_structure_effects -v
```

Les 25 méthodes passent à O0 en 0,990 s et O2 en 1,403 s :
`validation/async-completion-results-complete-o{0,2}.log`.
Vingt-trois méthodes concernent l'analyse de contrats, dont les modèles ; deux
exécutent des voisins pris en charge sous Clang C11/UBSan fatal. Le premier
voisin est un remplacement synchrone. Le second attend un résultat emprunté
puis le stocke dans un objet local via un auxiliaire synchrone : sortie 14,
drop de la cible après join admis, drop avant join refusé aux deux entrées.
Cela ne constitue pas 25 programmes de remplacement async exécutés.

Le modèle nouveau compte seize scénarios : quatre écritures possibles
(aucune, a, b, choix conditionnel), résultat avant/après écriture et attente
directe/handle lancé. Un état concret de deux champs fournit indépendamment
les ensembles attendus. Les seize résumés correspondent après correction.
Le modèle antérieur de 125 scénarios est également réexécuté. Les autres cas
couvrent permutations, alias, boucles, choix de tâches et handles, références
mutables, cible locale refusée et résultat agrégé explicitement non raccordé.

Le premier complément mélangeait deux types distincts de tâches inactives dans
un if, ce que les règles de type refusent. Il utilise désormais deux captures
différentes du même type de tâche ; un autre cas couvre deux types concrets via
leur handle public commun. Les diagnostics et échecs intermédiaires sont
conservés dans `async-completion-results-expanded.log` et `-model.log`.
L'échec du modèle n'a pas été contourné par un changement de ses attentes.

La campagne `tests/run_async_structure_effect_mutations.py` comprend onze
mutations ciblées : les sept précédentes et quatre pertes de résultat, de
réservation du porteur, d'instantané de champ ou de mise à jour des alias.
Les onze sont détectées dans la passe finale :
`validation/async-completion-results-complete-mutations.log`.
Les stades concernent ici les contrats et leurs assertions, pas onze défauts
mémoire observés dans des programmes multithreads.

La sélection de régression O2 des descripteurs capturés et des retours
d'emprunts async (champs, retours directs, liaisons locales, matchs et boucles)
passe 73 méthodes en 65,197 s :
`validation/async-completion-results-reference-regression.log`. Cette sélection
a démarré avant l'ajout final du statut incomplet pour les résultats empruntés
agrégés ; ce garde et son contre-exemple figurent dans les passes ciblées finales.
Les sélections se recouvrent et ne constituent pas un passage de toute la suite.

La compilation Python des modules et tests modifiés réussit. Les patches du
module et des tests sont conservés sous `validation/async-completion-results-*.patch`.

## Limites

Les effets transmis à un auxiliaire synchrone recevant un handle porteur de
modifications restent explicitement non raccordés. Les résultats empruntés
agrégés et les effets récursifs restent incomplets. Le contrat réunit les états
possibles après succès ou échec de lancement ; il ne constitue pas encore une
propagation générale corrélée aux branches Ok/Err de l'appelant.

Les remplacements de champs depuis les états restent refusés par le backend.
Les nouvelles informations doivent encore être attachées aux tâches et handles,
appliquées après attente, et confrontées aux durées de vie des porteurs/cibles.
Les cibles inline sans descripteur durable restent également ouvertes.
Pas de nouvelle preuve ASan/TSan, de comparaison entre compilateurs C
indépendants ni de preuve formelle. L'objectif global reste ouvert.
