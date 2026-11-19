[English](LOOP_DEAD_FIELD_VALIDATION.md)

# Validation du dernier usage d'un champ emprunté sur une reprise

Ce cycle affine l'implémentation de B2, B3, D4, L2 et V4.
Le contre-exemple déclare le receveur dans un bloc et le porteur du champ
emprunté dans son enfant. La boucle est dans le bloc enfant. Le porteur
est lu avant la boucle, puis le receveur est remplacé sur `continue`.
L'ancien contrôle refusait la présence du porteur vivant même si son
emprunt ne servait plus. Les blocs distincts isolent cet écart de la
contrainte d'ordre de destruction L3.

Le vérificateur invalide les accès qui conservent une dépendance devenue
inutilisable lorsque la reprise réunit les générations du receveur.
L'entrée de nettoyage du porteur reste suivie. Le destructeur d'enum
actuel ne lit aucun champ de référence. Les emprunts qui doivent encore
servir, les accès qui pourraient être restaurés par un transfert en cours
et les dépendances que le receveur emporterait vers une de ses générations
restent refusés. Le prototype conserve aussi son refus des ordres de
destruction incompatibles.

[Test de régression](../tests/test_loop_replacements.py) pour les champs
`&Int` et `&mut Int`. Les deux programmes admis affichent l'ancienne
valeur via le porteur puis la valeur de remplacement via le receveur.
La trace contrôle la destruction unique de l'ancienne allocation, le
nettoyage ultérieur du porteur et la destruction du remplacement. Un cas
nettoie le porteur par reset, l'autre à la sortie du bloc. Six voisins
sont refusés par le vérificateur et le compilateur. Ils utilisent encore
le porteur après la boucle, à l'itération suivante ou via un alias.

La régression globale réussit ses 819 tests. Les 15 tests ciblés
passent aussi sous Clang `-O2` et UBSan sans récupération.

Le modèle de traces des six séquences générées de remplacement reste
exécuté avec la graine 20261103. Les
[mutations](../validation/loop-dead-field-mutations.json) rétablissent le refus
systématique d'un champ emprunté et rejouent les deux fautes antérieures
sur le pointeur de reprise et l'ancien accès importé. Les trois sont
détectées.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_replacements.py -q
python3 tests/run_loop_replacement_mutations.py
```

Cette validation couvre les destructeurs intégrés. L'introduction de
destructeurs qui lisent les champs demanderait de modéliser ces lectures
comme des usages protecteurs, conformément à L4. ASan reste indisponible
sur cet hôte selon la sonde du
[cycle précédent](LOOP_RESULTS_VALIDATION.md).
