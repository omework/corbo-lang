[English](MUTEX_RUNTIME_CYCLE.md)

# Mutex et gardes : mécanisme interne du runtime

## Périmètre

Ce lot implémente les primitives internes nécessaires à MT9 et au nettoyage
SL1. Les constructeurs publics restent expressément reportés. Aucun nouveau
type ou nom de méthode public n'est ajouté au langage et aucune règle normative
n'est modifiée. Ce lot ne constitue pas une implémentation source complète des
mutex : typage des gardes, déduction de transfert et vérification des emprunts
dérivés restent à raccorder.

## Mécanismes implémentés

`mutex_runtime.py` fournit un fragment C intégré après la file des tâches dans
`TASK_THREAD_RUNTIME`. Le stockage des mutex, gardes et attentes est fourni par
l'appelant ; ces primitives n'allouent pas sur le heap. Le pointeur de valeur
et le callback de destruction représentent le stockage et le nettoyage que le
compilateur devra fournir. Ce callback n'ajoute pas de destructeur utilisateur.

Le mutex synchrone utilise pthread_mutex. Sa garde mémorise le thread acquéreur ;
un drop interne depuis un autre thread rend EPERM sans libérer le verrou.
Un second drop rend EINVAL. La destruction d'un mutex encore verrouillé échoue.
Le runtime ne peut pas établir l'interdiction statique de traverser une suspension.

Le mutex async ne conserve son verrou pthread interne que pendant la mise à
jour des métadonnées. Le verrou logique peut donc rester acquis pendant une
suspension puis être libéré depuis un autre thread. Une attente est un nœud
intrusif dans un état à adresse stable. La file FIFO et la réservation du premier
attendant empêchent une nouvelle arrivée de lui prendre le verrou ; c'est un
choix d'implémentation interne, pas une nouvelle garantie publique.

La libération réserve le verrou au prochain attendant et réveille son ticket
de scheduler. Le réveil est émis après libération du verrou interne, avec une
copie du ticket à génération ; il ne conserve aucun pointeur de frame ou de nœud
d'attente hors du verrou. Les tickets suivent les préconditions de durée du
scheduler existant. Une tâche sans ticket utilise le repli Yield ; les tâches
enregistrées rendent Pending pendant l'attente.

Le nettoyage d'une attente retire son nœud, ou transmet une réservation déjà
reçue au suivant. Une fois la garde acquise, l'attente est désarmée : sa
destruction ne libère pas la garde et n'accède plus au mutex. La garde doit
être détruite séparément par le nettoyage de l'état. La destruction du mutex
appelle le nettoyage de sa valeur avant de détruire sa synchronisation.

## Résultats exécutés

- O0 : 4 méthodes, 6 sondes C natives, 2,101 s, code 0 ;
  `validation/mutex-runtime-final-o0.log`.
- O2 : 26 méthodes de mutex, file prête, réveils, Select et frontière native,
  13,026 s, code 0 ; `validation/mutex-runtime-regression-o2.log`.
- Les deux passages utilisent Clang C11, pthread et UBSan sans récupération.
  Les régressions comprennent des frames produites par le compilateur.

Les assertions testent : accès exclusif et visibilité après verrouillage sync,
refus du drop sync depuis le mauvais thread, garde async conservée pendant
yield et libérée par un autre thread, attente Pending sans remise en file
immédiate, réveil après libération, visibilité des écritures, transmission d'une
réservation abandonnée, absence de vol de réservation, destruction de valeur
une fois et refus de destruction pendant occupation.

Trois sondes utilisent le véritable mécanisme interne Select. Au choix du
gagnant, la perdante possède respectivement une attente en file, une réservation,
ou une garde acquise. La ressource reste retenue après la remise du résultat ;
le drop de Select nettoie ensuite l'état correspondant. Les callbacks de frame
de ces sondes sont écrits dans le test, pas générés depuis une syntaxe mutex.

Le premier passage comportait deux erreurs de compilation du banc C : une
constante de callbacks inutilisée était traitée comme erreur par -Werror.
Les sondes la référencent désormais explicitement. Journal initial conservé :
`validation/mutex-runtime-first-o0.log`.

## Limites et travail restant

Les contrôles de durée de vie, de non-copie des gardes, de fin des emprunts
avant unlock et d'interdiction de suspension avec une garde sync ne sont pas
implémentés par ces fonctions C. Le compilateur devra les imposer lors du
raccordement des types publics. La destruction exclusive d'un mutex suppose
qu'aucun appel concurrent ne commence ni ne reste en attente ; les entrées de
scheduler doivent survivre aux notifications concurrentes. Les sondes respectent
ces préconditions. Les fonctions C internes ne sont pas une frontière sûre pour
du C arbitraire.

Aucun programme Crust avec constructeur mutex n'est annoncé accepté ou refusé.
Pas de nouveau modèle indépendant, de campagne de mutations ni d'audit
adversarial ; les modèles déjà présents dans les régressions ont été rejoués.
UBSan ne détecte pas toutes les courses : aucun résultat ThreadSanitizer n'est
revendiqué. L'audit approfondi avec un autre agent demeure différé.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_mutex_runtime -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_mutex_runtime test_ready_queue test_task_wakes test_select_runtime test_native_thread_runtime -v
```

Snapshot : `/tmp/crust-before-mutex-runtime/`. Différences archivées :
`validation/mutex-runtime-async_runtime.py.patch` et
`validation/mutex-runtime-new-module.patch`.
