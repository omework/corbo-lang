[English](MUTABLE_FIELD_COMPLETION_CYCLE.md)

# Remplacement de champs mutables dans les états

## Implémentation

Ce lot raccorde ST10–ST12, B1/B2/B4/B5 et AS12–AS16 sans changement
normatif. Les tâches peuvent remplacer un champ `&mut Int` d'un porteur
injecté, directement ou via helper, puis le lire ou le réemprunter. Les
modifications suivent les enfants attendus et les fabriques synchrones.
Le résultat peut être scalaire ou un réemprunt partagé/mutable du champ.

L'état conserve les réservations vers la nouvelle cible. Un réemprunt du champ
conserve en plus la capacité du champ du porteur : son remplacement et ses
accès incompatibles restent refusés jusqu'au dernier usage. Les chemins de
résultats incluent la nouvelle cible d'un champ modifié en plus de son porteur.
Les appels et retours ne copient pas les références mutables.

Une alternative inchangée dans un store conditionnel représente la cible
initiale du champ, pas un réemprunt actif de sa propre capacité. Le nouveau
marqueur interne `stored_mut_target` fait cette distinction. Les cibles
nouvelles restent retenues exclusivement et les vrais réemprunts conservent
leur réservation de champ. Les jonctions de branches et l'échec de lancement
conservent les alternatives initiales nécessaires.

## Recherche de contre-exemples

Dix méthodes dans `tests/test_mutable_field_completion.py` couvrent :

- affectation directe et helper, suspension puis mutation via le champ ;
- identité de la cible par lecture des deux allocations après destruction du porteur ;
- accès et mutation de la nouvelle cible refusés depuis le paramètre d'origine ;
- retours `&Int` et `&mut Int` : cible et champ du porteur réservés ;
- enfant attendu puis réemprunt, fabrique de handle et réemploi ;
- réemprunt nommé vivant à travers yield, accès au champ interdit avant son dernier usage ;
- remplacement conditionnel, dont l'enfant conditionnel suivi d'un accès du parent ;
- reset historique refusé avant dernier usage, accepté après destruction du porteur ;
- retour du réemprunt à travers un enfant et un relais ;
- modèle indépendant de huit cas : tâche inactive/attendue, porteur vivant/détruit,
  cible a/b. Cinq programmes exécutés, trois refusés par vérification et compilation.

Le premier voisin d'enfant conditionnel était refusé par `accès à 'v'
incompatible avec un emprunt actif`. Le contrat avait transformé l'alternative
« champ inchangé » en prêt actif de ce même champ. Le marqueur décrit ci-dessus
corrige ce refus indu. Le test exerce les deux branches et conserve le refus
d'accès direct au paramètre de la nouvelle cible.

## Mutations et amélioration de l'oracle

La première campagne détecte quatre mutations et en laisse survivre une :
la suppression du store C. Le test réempruntait ensuite le champ et écrivait
21, puis observait 21 par ce même champ. Ces observations étaient identiques
même lorsque le champ désignait encore l'ancienne allocation.

Le test lit désormais les deux allocations après destruction du porteur.
Le voisin correct produit `21, 21, 7, 21`, alors que le store supprimé modifie
l'ancienne cible. L'oracle est ainsi renforcé par l'identité des allocations ;
le compilateur n'a pas été changé pour ce défaut du test.
Les campagnes initiale et finale sont conservées séparément.

Les cinq mutations visent l'oubli de la réservation de cible, le store C,
la confusion entre champ inchangé et prêt actif, l'autorisation des lectures
sur une cible réservée et la perte de la capacité du champ réemprunté.
Ces mutations ciblées ne représentent pas un taux général de détection.

## Exécutions

Journaux `validation/mutable-field-completion-*.log`.
La première sélection réussit huit méthodes en 7,871 s (`-initial`).
Après correction du voisin conditionnel, neuf méthodes passent à O0 en
8,617 s (`-final-o0`). Une sélection O2 de 58 méthodes passe en 29,031 s
(`-final-o2`) ; elle comprend les résultats empruntés, les fabriques et les
contrats de champs async. Le retour du réemprunt enfant, ajouté ensuite,
passe séparément en 0,525 s (`-child-result`).

Les passages finaux du module incluent l'oracle d'identité renforcé :

```
PYTHONPATH=tests python3 -m unittest test_mutable_field_completion -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_mutable_field_completion -v
```

Les dix méthodes passent en 14,451 s à O0 (`-complete-o0`) et 13,963 s à O2
(`-complete-o2`). La campagne finale de cinq mutations les détecte toutes
(`-final-mutations`) ; le journal initial conserve la mutation survivante.
La compilation Python du module et des nouveaux tests réussit. Aucun changement du compilateur
après l'ajout du marqueur d'alternative initiale.

La régression finale passe 56 méthodes en 57,734 s (`-reference-regression`) :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_reference_returns test_async_field_reborrows test_stored_field_reborrows test_async_child_field_effects test_public_borrowed_handles -v
```

Les comptes sont des méthodes, parfois constituées de familles de programmes ;
les sélections se recouvrent.

C natif C11/pthreads, avertissements bloquants, UBSan fatal et niveaux O0/O2.
Les patches depuis le début du lot sont conservés dans
`validation/mutable-field-completion-*.py.patch`.

## Limites

Les porteurs restent injectés et les champs sont des références Int. Les
cibles inline générales, chemins d'agrégats plus complexes, certaines origines
de références issues d'autres champs et les stores sur les reprises de boucle
restent à généraliser. Les réservations sont conservatrices ; le résultat et
l'état des champs ne sont pas entièrement corrélés au succès du lancement.
Les anciennes cibles peuvent donc rester réservées plus longtemps que nécessaire.

Le modèle est fini et les scénarios ne prouvent pas tous les ordonnancements.
Pas de preuve générale de sûreté, de nouvelle preuve ASan/TSan ni de comparaison
entre compilateurs C indépendants. L'objectif global reste ouvert.
