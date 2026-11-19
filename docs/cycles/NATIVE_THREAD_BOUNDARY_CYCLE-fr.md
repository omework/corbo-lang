[English](NATIVE_THREAD_BOUNDARY_CYCLE.md)

# Cycle — frontière des blocs de thread natif

Suivi : ce rapport décrit l’étape avant raccordement. Le
[cycle suivant](NATIVE_BLOCK_LOWERING_CYCLE.md) remplace le refus transitoire
par la compilation des premiers blocs, et exécute le programme minimal.
Les limitations et chiffres ci-dessous sont ceux du présent cycle historique.

## Périmètre et règles

Application partielle de RT8, RT4–RT6 et AS10, sans changement normatif.
AGENTS.md, VALIDATION_GUIDELINES.md, LANGUAGE_RULES.md, l’index des sept
brouillons et les passages async/multithread ont été relus. Le précédent
échange sur le réglage du modèle n’avait pas fait progresser l’implémentation.
Ce cycle ajoute la syntaxe et les primitives internes de lancement natif.

**La primitive Crust complète n’est pas encore implémentée.** L’inférence des
captures et des résultats, les contrats, les pools d’états de ces blocs et leur
traduction restent à raccorder. Le programme valide conservé dans
`validation/open-native-thread-basic.crust` reste refusé. Son diagnostic actuel,
conservé dans `validation/open-native-thread-basic-current.log`, indique le
manque de contrats, au lieu de l’ancienne erreur de parsing. L’ancien journal
est conservé. Ce refus n’est pas une décision de langage.

## Implémentation

Le parseur produit une expression `native_thread` avec la liste ordonnée des
captures, le corps et la ligne source. L’en-tête `-> (a, b);` appartient
uniquement à l’entrée de ce bloc. Les retours et la valeur finale restent dans
ce corps, sans être transformés en retours de la fonction appelante.
Le contexte de parsing est synchrone dans le bloc, même dans un appelant async,
puis restauré après celui-ci. Un await appliqué au handle après le bloc reste
syntaxiquement possible chez l’appelant async.

Un contrôle transitoire au début de la vérification refuse explicitement ces
expressions avant les analyses génériques. Elles ne peuvent ainsi être ignorées
ou laisser leurs retours imbriqués contaminer le contrat appelant. Ce contrôle
doit être remplacé par l’analyse des contrats des blocs, et non simplement retiré.

Le runtime fournit `task_native_start` pour un handle attendu par join et
`task_native_async_start` pour une attente pollée. Ces fonctions appellent
directement la primitive pthread, sans consulter les callbacks du scheduler.
Elles partagent avec spawn les mécanismes de préparation et de nettoyage à
l’échec, mais choisissent un exécuteur synchrone dédié. Il appelle le corps une
seule fois ; un retour suspendu constitue une violation interne et provoque
un arrêt. Ce garde-fou ne remplace pas le refus statique de yield/await.

Le thread publie sa fin après la dernière utilisation de son état. Le résultat
est extrait avant restitution du slot. L’échec de lancement détruit l’état et
ses captures avant de rendre LaunchFailed. Le code système reste dans le handle.
Un bloc peut bloquer sur le join d’un autre thread natif. Aucun join implicite,
abandon de handle ou annulation n’est ajouté.

## Vérifications distinctes

`tests/test_native_thread_runtime.py` comporte cinq méthodes et dix exécutions
C par passage : neuf terminaisons normales et un arrêt SIGABRT attendu pour
une suspension impossible au niveau de l’ABI. Elles couvrent :

- Join et attente pollée, chacun avec succès et refus EAGAIN de création.
- Exécution sur un thread distinct, indépendance vis-à-vis d’un scheduler dont
  les deux callbacks de lancement refusent, et résultat composé avec emprunt.
- Absence de résultat et de libération pendant que le corps reste bloqué ;
  résultat visible après attente ; nettoyage unique ; slot réutilisable et
  ancien ticket de génération invalidé.
- Échecs de préparation des attributs d’un thread détaché, avant pthread_create,
  avec destruction des captures et des attributs initialisés exactement une fois.
- Join bloquant effectué par un bloc natif sur un autre thread natif, puis
  nettoyage des deux états avant le retour de l’attente extérieure.

L’oracle fini définit indépendamment les traces : succès `rtdw` (corps,
extraction, destruction, retour d’attente), échec `dw`. Il vérifie également
les résultats 42/20 ou 0/10, les comptes de nettoyage et de création système.
Ce n’est pas un modèle général d’ordonnancement ni une preuve de sûreté des
captures au niveau du langage. Les cibles empruntées des sondes C sont mises
en place explicitement et vivent assez longtemps par construction.

`tests/test_native_thread_parser.py` comporte sept méthodes : dix programmes
syntaxiquement admis, quinze refus syntaxiques et quatre vérifications du
refus transitoire avant analyse des effets. Les retours simples, anticipés,
propriétaires, le join, les blocs natifs imbriqués, les captures ordonnées,
les en-têtes mal formés et la restauration du contexte async sont examinés.
Une réussite de parsing n’est pas comptée comme programme Crust compilé.

Le premier passage du parseur a révélé une attente erronée dans le test :
l’opérateur est représenté par `arithmetic`, non `add`. L’assertion a été corrigée
sur la forme AST exacte ; aucune règle de langage n’a changé. Le journal initial
est conservé dans `validation/native-thread-parser-initial.log`.

## Exécutions et artefacts

| Journal dans validation/ | Résultat |
| --- | --- |
| native-thread-runtime-o0.log | 5 méthodes, 3,411 s, OK ; 10 exécutions C |
| native-thread-parser.log | 7 méthodes, 0,002 s, OK |
| native-thread-runtime-mutations.log | Cinq fautes runtime détectées |
| native-thread-parser-mutations.log | Héritage incorrect du contexte async détecté |
| native-thread-regression-o2.log | 68 méthodes, 65,491 s, OK, aucun saut ; inclut les 10 exécutions C du nouveau module |

Les sondes C utilisent Clang C11, pthread, `-Wall -Wextra -Werror`, UBSan fatal,
et `-O0` ou `-O2`. La régression exécute les deux nouveaux modules,
spawn_blocking, les obligations de handles, les initialisations typées async,
puis les méthodes du runtime liées aux threads, scheduler, workers, spawn,
nettoyages et réemploi de pool. Les noms exacts sont conservés dans le journal.

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_thread_runtime
PYTHONPATH=tests python3 -m unittest -v test_native_thread_parser
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_runtime_mutations.py
```

`validation/native-thread-abi.c` est une sonde C de l’ABI, **pas du C généré
depuis un bloc Crust**. Le diff des fichiers du compilateur et du runtime est
conservé dans `validation/native-thread-runtime.patch`. Les modules Python
modifiés et ajoutés passent py_compile. Les liens locaux des quatre documents
modifiés ont été vérifiés. Tous les processus de ce cycle sont terminés.

## Mutations et limites

Six fautes ciblées, uniquement dans des copies temporaires, ont été détectées :
passage du lancement natif par le scheduler ; acceptation d’une suspension ;
omission du nettoyage à l’échec ; publication de fin avant le corps ; libération
avant extraction ; héritage du contexte async dans le bloc synchrone. Les cinq
fautes runtime échouent sur les assertions ou traces natives attendues ; la
dernière fait accepter à tort les suspensions au parseur. Aucun taux global
de détection n’est déduit de cet échantillon.

Les contrôles statiques de captures, leur transfert effectif, les provenances
du résultat et l’obligation d’attente de la nouvelle primitive restent non
vérifiés. Les obligations existantes de spawn sont rejouées sans être présentées
comme des preuves de runtime::thread. La prochaine étape est la représentation
des blocs avec types et contrats, puis la génération de leurs états et appels
aux primitives natives établies ici.

ASan n’a pas été relancé après les blocages documentés des cycles précédents.
Aucune exécution TSan, aucun second compilateur ni preuve formelle n’est
revendiqué. L’installation publique du scheduler, les réveils et l’équité,
Select, les gardes de mutex et les autres lignes ouvertes de la matrice restent
dans l’objectif général. Ce cycle ne termine ni RT8 ni les sept brouillons.
