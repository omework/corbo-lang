[Français](ASYNC_HANDLE_CAPTURE_DECISION-fr.md)

<a id="capture-dun-handle-autonome-par-une-tâche-inactive"></a>

# Capture of an autonomous handle by an inactive task

AS14 and RT7 allow the transfer of a handle in an inactive task
the auditor establishes the autonomy of the task already started.
can be expected by the task that captures it if its body is executed.
If the launch is destroyed before the start or if its launch fails,
its cleaning abandons the handle and the runtime supports the cleaning
from the autonomous task to its termination.

Historical Witnesses `validation/open-inactive-task-captured-handle.crb`
and `validation/open-public-handle-async-parameter.crb` illustrate drop
before start and fail launch. Support for capture
and abandonment remains to be integrated into the compiler and runtime.

For a handle that still requires a wait, RT7 requires that the obligation
be respected on each path. The treatment of a capture in a
inactive task whose start and wait would be proven remains
to be specified.
