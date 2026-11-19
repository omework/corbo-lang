[English](ANCESTOR_JOIN_VALIDATION.md)

# Validation des remplacements d'un receveur ancêtre

Ce cycle implémente les jonctions de `if` pour les règles déjà retenues
T7, T9, T11, V4 et L3. Le backend C écrit le pointeur réel dans un
temporaire de jonction à la fin de chaque branche qui continue. L'analyse
associe ce temporaire à une seule entrée de nettoyage et réunit les
provenances, origines et dépendances. Elle place cette entrée à la position
que le candidat occupait sur chaque chemin. Un cycle entre les ordres de
réception reste refusé. Les contrats de fonction suivent les modifications
des variables visibles hors du bloc et isolent les déclarations qui les
masquent.

Le cas `a ->; r = <- a;` a mis en évidence une double inscription de
l'allocation lorsqu'elle revenait à un autre receveur de son scope
d'origine. La réception retire maintenant l'inscription antérieure avant
d'ajouter la nouvelle. Après la jonction, l'ancienne garde est désarmée
sur le chemin qui a transféré son nettoyage.

Le contrat ne conserve pas l'historique d'un candidat détruit sur la
branche qui le remplace. Sans cette distinction, un reset dans cette
branche faisait refuser à tort l'accès au candidat conservé sur l'autre
branche. Le masquage d'un nom enregistre la valeur extérieure au point
de déclaration, après tout remplacement déjà effectué.

Les contrôles ciblés vérifient notamment les deux chemins d'un remplacement
conditionnel, l'adresse sélectionnée, la destruction exactement une fois,
le reset direct ou après un appel, les pools distincts, les masquages de noms,
l'exclusion d'un retour anticipé, le dernier usage des emprunts, l'ordre des
destructions et un `if` dont le receveur est local à une itération. Un modèle
indépendant compare la trace de six programmes générés à celle d'une liste
de réceptions parcourue en sens inverse, avec la graine 20261103.

La régression globale a réussi ses 804 tests en quatre groupes.
Les 15 tests ciblés passent avec Clang 20.1.3, `-O2` et UBSan sans
récupération. Les deux mutations ciblées sont détectées.

[Résultats des mutations](../validation/ancestor-join-mutations.json).
Conserver l'ancienne garde déclenche un second nettoyage sur un transfert
d'un frère vers le receveur. Omettre une provenance n'était pas détecté par
le seul scénario de retour de fonction, car le contrat conserve les deux
provenances. Un voisin qui réinitialise directement chaque pool après le
`if` détecte désormais l'omission.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_ancestor_join.py -q
python3 tests/run_ancestor_join_mutations.py
```

Le vérificateur refuse encore les jonctions où une branche laisse le
receveur indisponible, où un résultat du `if` conserve un emprunt à une
identité que la jonction doit remplacer, ou où les ordres de destruction
ne peuvent pas être réunis. Le suivi d'une liaison déclarée avant la
boucle et remplacée à travers ses sorties ou ses reprises reste à
implémenter. L'analyse des effets et provenances est conservative et
n'établit pas une preuve générale. ASan reste indisponible sur cet hôte,
comme constaté sur le programme minimal du
[cycle précédent](LOOP_RESULTS_VALIDATION.md).
