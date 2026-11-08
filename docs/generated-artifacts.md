# Защита генерируемых артефактов

`psa render` owns `03_evidence.md`, `04_options.md`, `decision.md`, `05_strategy.md`, and `06_validation-plan.md`. Source drafts in `drafts/` remain human-editable.

After rendering, `render-manifest.json` stores SHA-256 hashes for the generated files. `psa validate` and the validation-stage gate compare the files with that manifest. A hand edit or deletion is reported; a normal `psa render` stops before overwriting it.

## Existing projects

For a project rendered before the manifest existed, adopt the current files once:

```powershell
psa render demo --adopt-existing
```

This records hashes and leaves Markdown untouched. If the existing manifest is corrupt, this explicit command replaces only the manifest baseline and preserves the Markdown; its output calls this out.

## Intentional regeneration

Put intended content changes in `drafts/` and run `psa render <project-id>`. If generated Markdown was edited directly, move those changes into the drafts. To deliberately discard direct edits, authorize and record the action:

```powershell
psa render demo --discard-generated-edits --by "Owner" --reason "Restoring generated output after moving the change to drafts"
```

The discarded file names and old/current hashes, actor, and reason are appended to `events.jsonl` before regeneration. MCP exposes equivalent `psa_render_adopt_existing` and `psa_render` operations. Neither path gives the server arbitrary file or shell access.
