[Français](SELECT_LAUNCHED_HANDLE_DECISION-fr.md)

<a id="select-et-handle-lancé-dans-une-branche-perdante--décision-validée"></a>

# Select and handle launched in a losing branch — validated decision

Explicit decision of the user: **refuse this case in the prototype**.
The normative rule is SL2 in [ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md).

The minimum programme is
[open-select-launched-handle.crb](../validation/open-select-launched-handle.crb).
The left branch launches worker, which borrows its local data allowance.
is suspended while waiting for this handle and that right wins, left stops
It cannot guarantee that waiting is still mandatory.
Destroying his catches would be dangerous, abandoning the handle would violate RT7 and
To wait silently would introduce a hidden join.

This programme must be refused.
I don't think it's proof that his waiting is over when the branch can lose.
Inactive tasks prepared as arguments remain destructible: this case
is distinct and covered by the synchronous task arguments cycle.

The arbitration is closed. SL2 diagnosis and refusal test in both stages
are followed in [SYNC_TASK_ARGUMENTS_CYCLE.md](cycles/SYNC_TASK_ARGUMENTS_CYCLE.md).
The restriction of the effects of suspension remains conservative; validation
does not claim to recognize all proven branches without residual obligation.

The case of an inactive task capturing a handle already launched remains separate
open in [ASYNC_HANDLE_CAPTURE_DECISION.md](ASYNC_HANDLE_CAPTURE_DECISION.md).
