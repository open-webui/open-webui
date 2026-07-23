# System Prompt Versioning — Changelog

## New Features

### Full Model Snapshot per Version
Every model save now stores a complete snapshot (`params`, `meta`, `name`, `base_model_id`, `is_active`) — not just the system prompt. View it in the **Detail** tab of the versioning modal.

### Difference View (Parameter Changes)
Click **View & Compare** → **Difference** tab → select two versions → **Compare**. The diff shows:
- System prompt changes (classic git-style diff)
- Parameter Changes (structured list of what else changed: temperature, skills, tools, knowledge, capabilities, etc.)

### Per-Version Comments
Add comments to any history entry via the **Detail** tab — useful for documenting why a change was made. Each comment shows the author and timestamp. You can delete your own comments.

### Search & Date Filter
Filter the history list by:
- **Text search** (commit message or author name)
- **Date range** (from / to)

Works both in the compact history list and inside the **View & Compare** modal.

### Paginated History
"Load More" button below the history list — no hard limit on how many versions you can browse through.

### Confirm Before Restore
Restoring a version now shows a confirmation dialog — no accidental overwrites.

### Editor Auto-Refresh After Restore
After restoring a version, the model editor UI reloads all fields (name, system prompt, advanced params, skills, tools, knowledge, capabilities) — no F5 needed.

## Bug Fixes

- **Unwanted form submit**: All buttons inside the model editor form now have `type="button"`. Previously, many buttons defaulted to `type="submit"` and triggered an unwanted model save. Fixed in: "View & Compare", "Detail"/"Difference" tabs, "Close", "Compare", "Load This Prompt Into Editor", "Send" (comment), "Delete comment", "Restore", "Delete version".
- **Full snapshot restore**: Restoring a version now restores `params`, `meta`, `name`, `base_model_id` from the snapshot — not just the system prompt.