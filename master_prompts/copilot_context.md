You are analyzing the Django app located at `{APP_NAME}/`. Read every Python
file in this directory (and its subfolders, excluding migrations/ and tests/
unless I ask otherwise) and produce a single markdown file that documents
what this app does, in the following order:

1. **Models** (`models.py` or `models/` package)
2. **Serializers** (`serializers.py` or `serializers/` package)
3. **Views** (`views.py` or `views/` package, including viewsets/APIViews)
4. **URLs** (`urls.py`)
5. **Everything else** — any remaining *.py files such as `services.py`,
   `permissions.py`, `signals.py`, `tasks.py`, `utils.py`, `managers.py`,
   `admin.py`, `apps.py`, etc. List these in the order they'd logically be
   used (e.g. permissions/managers before services, tasks last).

For EACH file, include:

- The file path (relative to the app root).
- A short 1–2 sentence summary of the file's overall purpose.
- For every class: its name, what it inherits from, its purpose, and a
  bullet list of its methods/fields with a one-line explanation of each.
- For every standalone function: its signature, what it does, its inputs
  and outputs, and any side effects (DB writes, external calls, signals
  fired, etc.).
- Notable decorators (e.g. `@receiver`, `@action`, `@permission_classes`,
  `@transaction.atomic`) and what they mean in context.

After covering all files individually, add a **"How it fits together"**
section that explains:

- The request/data flow end-to-end (e.g. URL → View → Serializer → Model).
- Which views use which serializers, and which serializers use which models.
- Any cross-file dependencies (e.g. a view calling a function from
  `services.py`, a model method triggering a signal, a serializer using a
  custom manager).
- Any notable relationships to other Django apps in this project, if
  imports reveal cross-app dependencies (e.g. `from accounts.models import
  User`) — just note the dependency, don't analyze the other app.

Formatting requirements:
- Use `##` for each file section and `###` for classes/functions within it.
- Use fenced code blocks only for short signatures (e.g. `def foo(self, x: int) -> bool:`), not full code dumps.
- Keep explanations concise and technical — this file is for AI/developer
  context, not end-user documentation.
- Do not omit private/helper functions or "obvious" CRUD methods — context
  completeness matters more than brevity here.

Save the output as:
`{APP_NAME}/.copilot/context.md`

If a `.copilot/` folder doesn't exist in this app directory, create it.
If `{APP_NAME}/.copilot/context.md` already exists, overwrite it with the
freshly generated summary rather than appending.