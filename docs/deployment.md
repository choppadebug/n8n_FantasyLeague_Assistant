# Reproducible local deployment

`docker-compose.yml` was derived from the existing n8n container's image,
mount destinations, file access restriction and restart policy. It pins the
installed n8n 2.46.6 image by digest, so repeated deployments use the same image.
Review and test image updates before changing that digest.

Two intentional changes: port 5678 binds only to localhost, and both timezone
settings use Europe/Rome. The existing container exposes port 5678 on all host
interfaces and has no explicit timezone settings.

## Fresh installation

Run in this repository's directory using PowerShell:

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force n8n-data, files
Copy-Item data/squad.json files/squad.json
docker compose config --quiet
docker compose up -d
```

The tracked `data/squad.json` contains the example football roster, not the n8n
database. Edit `files/squad.json` for your own roster (the workflow expects 25
players). The directories must exist before starting; Compose deliberately fails
on a missing mount instead of silently creating an empty data directory.

Open <http://localhost:5678>, create the owner account, and import
`published-workflows/My workflow.json`. Select or create your Telegram credential and
replace `YOUR_TELEGRAM_CHAT_ID` in the Telegram node. Store the bot token in
n8n's credential UI. Workflow import and Telegram setup are manual steps.

The ignored `n8n-data/` directory persists the database and n8n-generated
credential encryption key. Keep the entire directory private and back it up
together; preserving the database alone is insufficient to recover credentials.

## Move the existing container to Compose

The running container's data and files are in the parent project directory,
outside this repository. Do not start a fresh instance expecting it to contain
your existing workflows or credentials.

1. Copy `.env.example` to `.env`. Set `N8N_DATA_DIR=../data` and
   `N8N_FILES_DIR=../files` to reuse the inspected installation's directories.
   Confirm these resolve to the current container's two bind mounts before
   continuing. Keep `.env` private.
2. Run `docker compose config --quiet` to validate the configuration.
3. Stop the existing instance with `docker stop n8n`.
4. While it is stopped, privately back up the complete existing `data` and
   `files` directories, including hidden files and the encryption configuration.
5. Run `docker compose up -d`, then verify your workflows and credentials in
   the editor. The Compose container has a generated name; the old `n8n`
   container remains available for rollback.

Never run two instances against the same SQLite directory. For rollback, run
`docker compose down` before `docker start n8n`. This Compose file uses the
same image as the existing installation and does not perform a version upgrade.

No containers were stopped, started or migrated when preparing these files.

## Routine operation

```powershell
docker compose ps
docker compose logs --tail 100 n8n
docker compose stop
docker compose start
```

For backups, stop n8n, copy the entire configured data and files directories to
private storage, then start it again. Backups can contain credentials and
personal execution data; never commit them.

This configuration serves the editor on localhost. Remote internet hosting needs
an HTTPS reverse proxy and the corresponding n8n host/webhook settings; see the
[official n8n Compose guide](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/).

## Publication review

Keep configured exports in the ignored `workflows/` folder. Run
`python scripts/anonymize_workflows.py` to generate sanitized copies under
`published-workflows/`, then run the same command with `--check` to detect stale
copies. Import or publish the generated copies, and configure credentials and
chat IDs locally. Generated workflows are inactive until you enable them.

The sanitizer covers workflow exports, not all files in an n8n instance.
The tracked squad lists public footballers, but also reveals the chosen fantasy
roster; replace it with a generic example if you consider that private.

Earlier commits still contain private workflow exports. Ignoring and untracking
the originals does not remove those commits. Follow the [publishing and history
cleanup instructions](publishing.md) before the first remote push. No history
rewrite was performed during setup.

Review screenshots and every future n8n export separately before publication.
