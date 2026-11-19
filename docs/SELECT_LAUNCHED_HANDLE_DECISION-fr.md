[English](SELECT_LAUNCHED_HANDLE_DECISION.md)

# Select et handle lancé dans une branche perdante — décision validée

Décision explicite de l'utilisateur : **refuser ce cas dans le prototype**.
La règle normative est SL2 dans [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md).

Le programme minimal est
[open-select-launched-handle.crb](../validation/open-select-launched-handle.crb).
La branche left lance worker, qui emprunte son allocation locale data. Si left
est suspendue pendant l'attente de ce handle et que right gagne, left cesse
d'être pollée. Elle ne peut donc pas garantir l'attente encore obligatoire.
Détruire ses captures serait dangereux, abandonner le handle violerait RT7 et
attendre silencieusement introduirait un join caché.

Ce programme doit être refusé. La présence syntaxique de await dans left ne
prouve pas que son attente est terminée quand la branche peut perdre. Les
tâches inactives préparées comme arguments restent destructibles : ce cas
est distinct et couvert par le cycle des arguments de tâches synchrones.

L'arbitrage est clos. Le diagnostic SL2 et le test de refus aux deux étapes
sont suivis dans [SYNC_TASK_ARGUMENTS_CYCLE.md](cycles/SYNC_TASK_ARGUMENTS_CYCLE.md).
La restriction des effets de suspension reste conservative ; la validation
ne prétend pas reconnaître toutes les branches prouvées sans obligation résiduelle.

Le cas d'une tâche inactive capturant un handle déjà lancé reste séparément
ouvert dans [ASYNC_HANDLE_CAPTURE_DECISION.md](ASYNC_HANDLE_CAPTURE_DECISION.md).
