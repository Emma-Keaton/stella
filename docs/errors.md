# Error Handling

Stella is built to fail honestly and recover gracefully. Every error that
reaches you is written in plain English — never a raw stack trace — and offers
concrete next steps.

## Plain-English errors

When something goes wrong, Stella translates the underlying exception into a
clear message plus what you can do about it. For example:

| Underlying error | What Stella tells you |
|------------------|-----------------------|
| `FileNotFoundError` | "Stella could not find the file or folder it was looking for. Check the path is correct and try again." |
| `TimeoutError` | "Stella waited too long for a response. The service may be slow or your internet connection is unstable." |
| `ConnectionError` | "Stella could not reach a service. Check the service is running and your network is working." |
| HTTP 401 | "Stella could not log in to a service. Check your API key or login details." |

The translation lives in `core/error_reporter.py::translate_error`.

## Fix it yourself

When an error appears, Stella offers a **Fix it yourself** action. This prompts
Stella to analyse the issue and update its own code so it can handle the task
better next time. The response includes:

- the plain-English description,
- the error type and original message,
- a suggestion for how Stella will improve.

## When your local AI can't handle the task

Not every task is within reach of the model running on your device. When that
happens, Stella does not pretend it can succeed — it tells you plainly and
offers alternatives, such as:

- switching to a cloud AI provider (Settings → AI Provider),
- using a smaller or different local model that fits your device,
- adjusting the timeout so Stella waits longer.

## Report to admin

If the fix is beyond what your local instance can do, you can push the error
into Stella's GitHub repository as an issue. Stella (the admin's agent) sees
the issue, fixes the code, and alerts the admin, who then instructs it to push
the update. Your device receives the fix through the normal self-update flow.

- `ErrorReporter.submit_issue(...)` records the report locally and returns a
  pre-filled GitHub issue URL (title, error, plain-English summary, device
  specs, and stack trace) so you can submit it with one click.
- Bug reports are stored in `feedback/bug_reports.json` with a `global_fix`
  flag. Resolved reports roll into the next update's changelog
  (`feedback/changelog.json`).

## Error recovery in the agent loop

The agentic loop (`agent/loop.py`) treats a failed tool call as an observation,
not a dead end: the error text is handed back to the model so it can adapt
instead of retrying blindly. A repeat-detector stops the model from issuing the
identical call more than twice. `agent/error_handler.py` classifies errors
(transient / not-found / fatal) and decides whether to retry, skip, replan, or
abort — using a cloud analyst when available and a deterministic local
heuristic when offline.
