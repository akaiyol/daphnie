# Cross-device project continuity

Status: explicit Markdown/Git handoff, implemented for Mac and Linux/WSL2. Two-checkout tests exercise transfer and failure handling. Physical Windows execution and live agent recall still need verification.

## What is shared

Keep the public package and private project memory in separate Git repositories. One private memory repository belongs to one project and information owner. It contains `INDEX.md`, `notes/`, historical Markdown under `history/`, and `HANDOFF.json`. The metadata pins the package origin and exact commit, records the active device and timestamps the handoff. Notes retain source, date, status and uncertainty. Use the existing flavour boundaries when deciding which records to retrieve.

`connect` adds a project-specific pointer to the existing private configuration at `~/.codex/daphnie/INDEX.md`. The operating contract already reads relevant pointers there. It preserves other project configuration. This is instruction-based retrieval, not a host-enforced trigger or proof of automatic recall. Start a fresh chat after connecting. Agents should read the project index and current checkpoint when the active project matches, then only relevant evidence.

The script does not copy Codex authentication, generated memory stores, session databases, application settings, release authority or unrelated projects. Codex local memories remain generated machine-local state. Project-specific historical summaries can be reviewed and copied as Markdown evidence; doing so does not recreate the original chats or their automatic memory indexing.

Private Markdown is the portable memory source of truth. Controller databases retain absolute registered paths and release state; they are not a portable runtime. A future structured-memory transfer must acquire the memory lock, use SQLite's backup API, capture associated note files consistently, verify integrity, and restore only into a stopped store with rollback. No database transfer is implemented here. Existing private stores are preserved.

## First computer

Prerequisites: Python 3.9+, Git, authenticated GitHub CLI, one reviewed package checkout and a private GitHub memory repository. Authenticate separately on each computer; never sync authentication files.

From the package checkout, initialize memory outside the public package:

```sh
python3 scripts/handoff.py --memory "$HOME/.local/share/daphnie/projects/daphnie" init --project daphnie
```

Review and migrate only this project's existing notes into `notes/` or `history/`. Write `notes/CURRENT.md` with current decisions, progress, unresolved issues, validation evidence and next steps. Keep private file references relative inside the memory repository. Historical records may retain old paths as provenance; those paths are not runnable configuration on the second computer.

Commit the reviewed memory files. Create a private repository through GitHub or `gh repo create`, attach it as `origin`, and push its `main` branch. Never attach private memory to the public package origin. The handoff script verifies GitHub's private flag through `gh api` before each network handoff and refuses a different push URL. The check is a point-in-time guard; repository access controls and later visibility changes remain the owner's responsibility. The content check rejects a few obvious credential formats; it is not comprehensive secret detection.

Connect the local project memory:

```sh
python3 scripts/handoff.py --memory "$HOME/.local/share/daphnie/projects/daphnie" connect
```

Keep existing Daphnie skill links if they already point to the canonical checkout. For a new installation use `python3 scripts/check.py`, then `python3 scripts/install.py --destination "$HOME/.agents/skills"`. Do not install duplicate copies of the same skill into multiple discovery directories. The installer refuses existing conflicting entries.

## Windows PC

Install WSL2 from Administrator PowerShell using `wsl --install`, complete the Linux user setup, and restart if requested. Install Git, Python 3 and GitHub CLI inside WSL; sign into GitHub there. In the desktop app, choose WSL as the agent environment and restart the app. Choose WSL for the terminal as well, so commands and paths agree. Keep code and private memory under the Linux home directory.

Clone the public package into `~/code/daphnie` and the private memory repository into `~/.local/share/daphnie/projects/daphnie`. Run the package checker and installer inside WSL. Run `connect` there to create the machine-local pointer. The code and note contents sync; local links and absolute configuration paths are created separately.

Verify that the app discovers `$daphnie` and can read the private project index. The WSL CLI and Windows desktop app may have different Codex homes; do not assume the CLI install alone configures the app. If needed use the app's selected environment and its actual skill/configuration locations. Do not solve this by copying the entire Codex home.

## Switching computers

Before starting work, from that computer's package checkout:

```sh
python3 scripts/handoff.py --memory "$HOME/.local/share/daphnie/projects/daphnie" start --device laptop
```

Use `--device pc` on Windows. The command requires clean checkouts, fetches private memory, advances only by fast-forward, brings the package to the saved commit, and publishes the active-device claim. Start the chat only after it succeeds. Invoke `$daphnie` in the package project. Memory outside its permitted workspace may need to be attached or granted access through the host.

Before leaving, update the private checkpoint and relevant notes. Review, test, commit and push package changes separately; public publication is never implicit in the handoff script. Then:

```sh
python3 scripts/handoff.py --memory "$HOME/.local/share/daphnie/projects/daphnie" finish --device laptop
```

The command requires `notes/CURRENT.md` and an origin-published package commit, commits scoped memory changes, then pushes the released handoff. Switch only after the push succeeds. This is an explicit handoff, not continuous background synchronization. It checks checkpoint existence, not whether a human or agent saved all relevant context.

## Recovery

`status` shows local metadata; it does not contact GitHub or prove the remote agrees. An active-device claim has no automatic expiry. If a computer is lost or unavailable, first recover its unsynced work if possible, confirm it will stop writing, then deliberately clear `active_device` in the private repository, commit and push. Starting with a new device must not silently override that claim.

A failed push leaves a local commit. Inspect local and remote history, fetch, and retry a normal `git push origin HEAD:main` if it is a fast-forward. A failed start may have advanced the local package but does not grant a successful handoff. If histories diverged, preserve both and reconcile explicitly. Never use a force push or reset to hide the failure. The code and memory repositories do not form a distributed transaction; package publication can succeed while memory publication fails. The pinned package hash identifies the last completed handoff.

Git preserves past memory revisions. Deleting a note removes it from the current checkout after synchronization, not from historical commits or other backups. Explicit forgetting needs separate history/backup retention handling.

## Verification

Run the package checker and `python3 -m unittest discover -s tests -p 'test_*.py'`. The handoff tests use local bare remotes and two independent checkouts. They cover notes, package revisions, deletion, active-device conflicts, dirty work, unpublished commits, failed pushes, mismatched push URLs, public-repository refusal and idempotent configuration. They do not establish Windows execution, hosted GitHub races, complete credential detection, behavioural recall or filesystem isolation.

See the [decision and source review](../research/2026-11-11-cross-device-continuity.md).
