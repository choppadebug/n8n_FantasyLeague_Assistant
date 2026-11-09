# Publish sanitized workflows

Keep n8n exports in `workflows/`, which is ignored by Git. Generate publishable
copies with the dependency-free script (Python 3.10 or newer):

```powershell
python scripts/anonymize_workflows.py
python scripts/anonymize_workflows.py --check
```

Run from the repository directory. The script also resolves its input/output
directories correctly when launched from elsewhere. Each source JSON is copied
to the corresponding path under `published-workflows/`; originals are never
rewritten. Use generic filenames because filenames are preserved.

It removes credential references, webhook IDs, workflow/instance metadata,
static data, pinned execution data, tags and node annotations. Sticky-note
contents are replaced. Telegram chat IDs become `YOUR_TELEGRAM_CHAT_ID` and
published workflows are inactive. Known secret fields, authorization/header
values (including `x-goog-api-key`), common token/key formats including Google/Gemini
API keys and `?key=` URL parameters, email addresses, and common user-directory
paths are redacted, including matches embedded in strings.

This is a practical sanitizer, not a guarantee against arbitrary personal text,
custom secrets or unusual encodings. Review the generated diff and screenshots.
Code with embedded sensitive values can be changed by redaction; configure
credentials separately after importing. Node IDs and connections are preserved.
`--check` compares every generated export with its private source and fails on
missing/stale outputs or unexpected published JSON. It writes nothing. If a
source was deleted, review and remove its old published copy yourself.

## Stop tracking private originals

`.gitignore` does not untrack files already in Git. Run this once if needed:

```powershell
git rm -r --cached --ignore-unmatch -- workflows/
```

This removes originals from the index, leaving the local files intact. It does
not remove earlier commits. The command has already been applied during setup.

## Remove old workflows from local history before the first push

These commands are for the repository that has never been pushed. They rewrite
local commit IDs. No history rewrite or push was performed during setup.

First regenerate, review, and commit the files intended for publication:

```powershell
python scripts/anonymize_workflows.py
python scripts/anonymize_workflows.py --check
git add .gitignore README.md .env.example docker-compose.yml docs/ scripts/ published-workflows/ assets/ data/squad.json
git diff --cached --stat
git commit -m "Prepare sanitized workflows and deployment documentation"
git status --short
```

Continue only after reviewing the staged content and confirming there are no
remaining tracked changes. In particular, review screenshots separately.

Make a private backup of the repository (including `.git`) and ignored originals
before the rewrite. A Git bundle also preserves all committed refs, but does
not include ignored or uncommitted files:

```powershell
New-Item -ItemType Directory -Force backups
git bundle create backups/before-workflow-cleanup.bundle --all
python -m pip install git-filter-repo
python -m git_filter_repo --force --invert-paths --path workflows/
```

The backup bundle contains the old private history: keep it local. `--force`
allows filtering this existing working repository instead of a fresh clone.
The path filter removes `workflows/` from all rewritten history while retaining
`published-workflows/`. If private exports ever used other tracked paths, include
each of those with another `--path` in the same command. Ignored local originals
remain on disk after the rewrite.

Verify that the following first two commands print nothing, then validate the
published copies again:

```powershell
git log --all --oneline -- workflows/
git ls-files -- workflows/
git check-ignore "workflows/My workflow.json"
python scripts/anonymize_workflows.py --check
```

Filtering normally removes the `origin` remote. Inspect remotes, and add it only
if absent:

```powershell
git remote -v
git remote add origin https://github.com/choppadebug/n8n_FantasyLeague_Assistant.git
git push -u origin HEAD
```

If `origin` already exists, skip `git remote add` (or correct its URL with
`git remote set-url origin ...`). Use a normal first push to an empty remote;
no force push is needed. If the remote already contains commits and rejects the
push, inspect them before deciding how to combine histories.

See the [git-filter-repo manual](https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt)
for path filtering and history-rewrite behavior.

## Before subsequent pushes

```powershell
python scripts/anonymize_workflows.py
python scripts/anonymize_workflows.py --check
git add published-workflows/
git diff --cached
git commit -m "Update published workflow"
git push
```

The script does not stage, commit, push, install hooks or rewrite Git history.
