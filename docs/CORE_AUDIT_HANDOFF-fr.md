[English](CORE_AUDIT_HANDOFF.md)

# Corbo — Guide pour l’audit indépendant du core

La référence de langage est le core du **11 novembre 2026**. Ce guide sert
à un agent indépendant qui cherche des programmes mettant en défaut
l’application des règles. Pour chaque passe, indiquer la version exacte
du compilateur examinée, par exemple le commit et les modifications locales.

## Documents de référence

| Document | Usage |
| --- | --- |
| [Grammaire EBNF](../CORE_GRAMMAR.ebnf) | Déterminer si la forme source appartient au core. |
| [Règles N1–N8](LANGUAGE_RULES.md#noyau-mémoire--grille-de-lecture) | Identifier l’invariant et lire les clauses normatives auxquelles il renvoie. |
| [Règles async et multithread](ASYNC_MULTITHREAD_RULES.md) | Interpréter les captures, suspensions, contrats de branche et attentes. |
| [Checklist](IMPLEMENTATION_CHECKLIST.md#vérification-sémantique-du-core) | Repérer les prises en charge partielles et les refus déjà recensés. |
| [Matrice de vérification](VERIFICATION_MATRIX.md) et [rapport de cycle](cycles/CORE_COMPOSITION_CYCLE.md) | Retrouver les témoins existants, les résultats exécutés et leurs limites. |
| [Consignes du projet](../AGENTS.md) et [guidelines de validation](VALIDATION_GUIDELINES.md) | Suivre le processus de reproduction et de rapport. |

La grammaire et les règles donnent le comportement attendu. La checklist
et la matrice documentent l’état de l’implémentation. SelectGroup et le
scheduler personnalisé sont reportés. Utiliser la syntaxe du core et le
runtime intégré, en particulier `A<T>`, les déplacements par valeur et
les signatures de closure `fn(...) -> R`.

## Mission à donner à Claude

> Cherche des contre-exemples reproductibles dans le core Corbo. Pour
> chaque candidat, cite la règle normative et déduis l’issue attendue
> avant de consulter le résultat du compilateur. Priorise un programme
> accepté alors qu’une règle exige son refus. Relève aussi un refus
> inattendu, un écart de génération C ou une ambiguïté de spécification
> quand les éléments le justifient. Réduis chaque cas et fournis une
> variante témoin qui change une seule condition pertinente. Remets un
> rapport et les sources minimales. L’intégration des correctifs fait
> l’objet d’une passe distincte.

## Axes de recherche

- **N1–N3** — type et initialisation, responsabilité du nettoyage, copie,
  emprunt et déplacement. Suivre l’ancienne liaison et le receveur.
- **N4–N5** — durée de vie et compatibilité des accès. Suivre une référence
  à travers une closure, une branche concurrente ou une valeur retournée.
  Identifier la cible, la zone empruntée et le dernier usage.
- **N6** — chemins et ordre d’évaluation. Examiner une sortie de bloc,
  un remplacement ou une attente sur certains chemins. Écrire la suite
  d’événements attendue avant de lancer le compilateur.
- **N7** — destruction et récupération. Suivre l’ordre des événements et
  vérifier qu’un slot réutilisé ne réactive pas l’ancien accès.
- **N8** — frontières. Faire passer une obligation à travers une fonction
  relais et comparer le résultat au cas direct. Inclure la provenance,
  les effets sur les champs ou entrées et, le cas échéant, l’attente.

## Reproduction

Depuis la racine du dépôt, sur un fichier Corbo autonome avec `main` :

```sh
python3 prototype/crust.py check cas.crb --syntax-only
python3 prototype/crust.py check cas.crb
python3 prototype/crust.py emit-c cas.crb -o /tmp/crust-audit-cas.c
```

La première commande vérifie la syntaxe. La deuxième exerce le vérificateur.
La troisième sert à isoler un écart de génération après acceptation. Pour
un témoin que la spécification autorise, utiliser aussi
`python3 prototype/crust.py run cas.crb` si l’issue attendue est observable à
l’exécution. Un programme interdit accepté par `check` suffit pour
signaler un défaut du vérificateur. L’exécuter n’est pas nécessaire.

Point de départ pour se familiariser avec les deux entrées :
[invalid_reference_field_drop.crb](../examples/invalid_reference_field_drop.crb)
est un témoin connu qui passe l’analyse syntaxique et doit être refusé
à cause d’un emprunt encore utilisé.

## Format d’un constat

1. **Règle et raisonnement attendu** — N1–N8, clause précise, chemin d’exécution
   ou obligation de durée de vie en cause.
2. **Source minimale et variante témoin** — fichiers complets, avec le
   changement qui explique la différence attendue.
3. **Résultat observé** — version, commandes, codes de sortie et diagnostics.
   Ajouter la sortie, la trace ou l’extrait de C généré quand ils établissent
   le constat.
4. **Nature du constat** — programme interdit accepté, programme autorisé
   refusé, écart de génération ou de runtime, ou règle insuffisamment
   précise. Signaler les limites et les résultats non reproduits.
5. **État connu** — indiquer si la matrice ou un rapport contient déjà ce cas.
