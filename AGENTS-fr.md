[English](AGENTS.md)

# Consignes de travail pour Corbo

Avant tout travail de validation, d'audit de sûreté ou de modification des tests,
lire et suivre [VALIDATION_GUIDELINES.md](docs/VALIDATION_GUIDELINES.md), fourni par
l'utilisateur. Ce document définit le processus de validation du projet.

Les règles de langage retenues sont consignées dans
[LANGUAGE_RULES.md](docs/LANGUAGE_RULES.md). Ne pas déduire la sémantique uniquement
du compilateur et ne pas modifier les règles normatives sans accord explicite.

Rechercher des contre-exemples et rapporter des preuves d'exécution précises,
leurs limites et les écarts non résolus. Une suite de tests réussie ne constitue
pas une preuve générale de sûreté.

Maintenir [VERIFICATION_MATRIX.md](docs/VERIFICATION_MATRIX.md) et consigner les
résultats exécutés, contre-exemples et limites dans un rapport de cycle.

À chaque étape significative, afficher à l'utilisateur la checklist actualisée :
travail terminé et validé, étape en cours, reste à faire et arbitrages ouverts.
Ne pas cocher une validation tant que son exécution n'est pas terminée.

Priorité confirmée par l'utilisateur : ce chat se concentre sur l'implémentation
et l'intégration des fonctionnalités du compilateur. Conserver les tests
fonctionnels et de non-régression nécessaires, la matrice et les limites connues.
La recherche adversariale approfondie et les campagnes de mutations sont
confiées à un autre lab ; ne pas les lancer systématiquement dans ce chat.
Distinguer les résultats testés ici de l'audit indépendant, dont l'état ne doit
pas être supposé.
Les passes de ce chat portent sur les cas déjà énumérés et les régressions
directement liées aux changements. Ne pas étendre systématiquement la campagne
à de nouveaux contre-exemples ou combinaisons ; corriger et consigner les défauts
rencontrés dans ce périmètre.

## Distinguer les modifications du core et des API

Avant chaque modification, qualifier explicitement son périmètre : core/grammaire
ou API/bibliothèque standard. Séparer les mécanismes du langage des API de la
bibliothèque.

- Une modification du core/de la grammaire touche la syntaxe, les règles du
  langage ou les mécanismes généraux du compilateur. Valider les mécanismes
  affectés et les régressions pertinentes.
- Une modification d'API/de la STD touche des interfaces ou implémentations de
  bibliothèque utilisant les mécanismes existants. Effectuer des tests
  fonctionnels ciblés et les régressions directement liées. Ne pas relancer
  automatiquement toute la suite du compilateur, son auto-reconstruction ou
  une vaste campagne de sûreté pour une modification d'API.
- Si une modification d'API révèle une limite du compilateur, identifier
  explicitement le correctif distinct du core et valider ce mécanisme de façon
  proportionnée. Ne pas étendre le chantier d'API à des travaux sans rapport
  dans le compilateur.

Appliquer les consignes de validation proportionnellement à cette distinction.
Conserver la couverture convenue des plateformes pour les comportements
spécifiques affectés ; une modification d'API n'impose pas à elle seule de
reconstruire le compilateur sur chaque plateforme.
