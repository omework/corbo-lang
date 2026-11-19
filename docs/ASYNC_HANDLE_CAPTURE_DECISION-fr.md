[English](ASYNC_HANDLE_CAPTURE_DECISION.md)

# Capture d'un handle autonome par une tâche inactive

AS14 et RT7 autorisent le transfert d'un handle dans une tâche inactive
quand le vérificateur établit l'autonomie de la tâche déjà lancée. Le handle
peut être attendu par la tâche qui le capture si son corps s'exécute.
Si celle-ci est détruite avant le démarrage ou si son lancement échoue,
son nettoyage abandonne le handle et le runtime prend en charge le nettoyage
de la tâche autonome à sa terminaison.

Les témoins historiques `validation/open-inactive-task-captured-handle.crb`
et `validation/open-public-handle-async-parameter.crb` illustrent le drop
avant démarrage et l'échec de lancement. La prise en charge de la capture
et de l'abandon reste à intégrer au compilateur et au runtime.

Pour un handle qui exige encore une attente, RT7 impose que l'obligation
soit respectée sur chaque chemin. Le traitement d'une capture dans une
tâche inactive dont le démarrage et l'attente seraient prouvés reste
à préciser.
