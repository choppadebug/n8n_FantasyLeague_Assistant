# Fantasy League Assistant

**A self-hosted Serie A fantasy football assistant built with n8n, JavaScript, Docker, Google Gemini, and Telegram.**

Fantasy League Assistant collects projected lineups, player availability, and editorial recommendations, matches them against your fantasy squad, and sends position-specific Telegram reports. Scheduled execution and dynamic retrieval of the matchday's first kickoff help time reports around the start of each round.

Deterministic data processing consolidates the evidence, then an AI recommendation branch proposes a formation, starting XI, and ordered bench with explanations. Code validates the selected players before the AI report is sent to Telegram.

## Features

- **Scheduled execution:** an n8n Schedule Trigger checks hourly from 12:00 through 21:00 in the workflow's configured timezone.
- **Dynamic matchday start:** fixture dates from the lineup API determine the earliest kickoff, without a manually entered matchday start date.
- **Kickoff window:** a Code node checks whether the first match starts within the next two hours, and an If node controls the squad-matching branch.
- **Lineup information:** projected starters, substitutes, starting probabilities, injuries, suspensions, opponents, and home/away fixtures.
- **Editorial recommendations:** top picks, players to avoid, surprises, positional tiers, and match-specific advice.
- **Squad matching:** name normalization handles accents, punctuation, capitalization, and some surname-initial variations.
- **Telegram delivery:** four HTML-formatted reports covering goalkeepers, defenders, midfielders, and forwards.
- **AI lineup advice:** Gemini recommends a formation, 11 starters, and seven substitutes in priority order, with Italian explanations, alternatives, and risks.
- **Validated AI output:** a structured parser and deterministic checks reject invalid formations, unknown or duplicate players, role mismatches, and injured or suspended selections before AI delivery.
- **Reproducible deployment:** Docker Compose pins the n8n image and keeps persistent state separate from the workflow export.

## Demo

Position reports show starting probability, projected lineup status, fixture, editorial flags, and positional tier. Injured players receive a prominent availability warning, with further recommendations omitted. A separate AI report includes the suggested formation and starting XI, an ordered seven-player bench with reasons, an overall rationale, possible changes, and risks.

Illustrative report excerpt:

```text
FANTACALCIO — GIORNATA 11
PORTIERI

Caprile — 100% · Titolare
    Cagliari vs Frosinone · 5ª fascia

Perri — 100% · Titolare
    Torino vs Lecce · SEMI TOP
    Scommessa
```

This is a historical example, not current matchday advice.

### Telegram report

![Telegram report](assets/telegram-report.png)

### AI lineup recommendation

![AI Telegram report with formation, starting XI, and ordered bench](assets/telegram-ai.png)

## How it works

The workflow loads a local squad file and retrieves Fantamaster lineup data. It derives the matchday number and first kickoff from that response, then combines lineup information with recommendations extracted from editorial articles.

```mermaid
flowchart TD
    A[Schedule or manual trigger] --> B[Load squad JSON]
    A --> C[Retrieve lineup and fixture data]
    B --> C
    C --> D[Find first kickoff and check time window]
    D --> E{Within two hours of kickoff?}
    E -->|Yes| F[Match squad against lineups]
    E -->|Yes| G[Generate article sources]
    C --> G
    G --> H[Retrieve and parse editorial articles]
    B --> I[Merge squad and player evidence]
    F --> I
    H --> I
    I --> J[Format position reports]
    J --> K[Send to Telegram]
    I --> L[Prepare LLM Input]
    L --> M[Basic LLM Chain]
    N[Google Gemini Chat Model] -.-> M
    O[Structured Output Parser] -.-> M
    M --> P[Validate AI Lineup]
    P --> Q[Format AI Telegram]
    Q --> R[Send AI report to Telegram]
```

The diagram reflects the current export: article retrieval also has a direct connection from the lineup request, so the kickoff check does not gate every branch. The workflow generates a matchday report key, but does not currently use it to suppress repeat reports. Multiple scheduled executions can qualify within the two-hour window.

### Data sources

| Source | Use |
|---|---|
| `https://publicapi.fantamaster.it/lineups/` | Matchday, fixtures, projected lineups, probabilities, and availability |
| `https://newsapi.fantamaster.it/wp-json/wp/v2/posts` | Editorial articles retrieved using matchday-based slugs |

The editorial parser extracts recommended players, players to avoid, surprise picks, and positional tiers using JavaScript in n8n Code nodes. This extraction remains deterministic; Gemini receives the consolidated player records afterward.

Each player's starting probability, medical availability, tier, and editorial flags remain separate. Source URLs are retained, and conflicting recommendations are preserved for human evaluation.

## AI recommendations and validation

The AI branch starts at `Merge Evidence`, alongside the existing position-report branch. It uses the same consolidated roster rather than retrieving additional news or browsing independently.

### Input and selection logic

`Prepare LLM Input` requires 25 squad records and checks that at least 11 players are not marked injured or suspended. It builds a compact JSON input containing names, roles, teams, opponents, venue, projected status, starting probability, tiers, flags, availability, and editorial source labels. Raw article bodies and source URLs are omitted from the model payload.

`Basic LLM Chain` asks Gemini to use only that evidence. The prompt balances attacking upside with lineup reliability, prefers an offensive formation when justified, and considers same-role bench cover with a maximum of three substitutions under the configured fantasy rules. It explicitly distinguishes real-match starting probability from the probability of receiving a fantasy rating, treats unknown data as uncertainty, and acknowledges conflicting editorial advice.

The requested output contains `formation`, `starters`, `bench`, `rationale`, `tips`, and `risks`. Explanations are in Italian, and each substitute has a reason for their place in the ordered bench. The prompt also instructs the model to treat supplied descriptions as untrusted data and ignore instructions embedded in them.

### Validation before delivery

| Step | Implemented checks |
|---|---|
| Input preparation | Exactly 25 roster records and at least 11 non-injured/non-suspended players |
| Structured Output Parser | Parses the model response against the object structure inferred from the configured JSON example |
| Formation and starters | One of `4-3-3`, `4-4-2`, `3-4-3`, `3-5-2`, `4-5-1`, `5-3-2`, or `5-4-1`; one goalkeeper and the exact positional counts for 11 starters |
| Player eligibility | Exact roster-name membership, correct role, no duplicate names across starters and bench, and no injured or suspended selections |
| Bench | Exactly seven substitutes, 18 unique selected players overall, and a backup goalkeeper when at least two eligible goalkeepers exist |
| Telegram formatting | Escapes dynamic text for HTML and rejects an AI report longer than 3,900 characters |

`Validate AI Lineup` checks the model's selections against the original `Merge Evidence` records, then adds a validation summary before `Format AI Telegram` and the second Telegram node. Invalid selections throw an error before the AI send node. The existing position reports use a separate branch; an AI failure does not undo messages already sent.

These checks establish structural and roster validity. They do not prove that a lineup maximizes fantasy points, that a rationale is factually supported, or that bench order gives sufficient cover for every scenario. The three-substitution strategy and scoring tradeoffs are prompt instructions, not a simulated or mathematically verified substitution plan. The input precheck requires 11 eligible players, while the final recommendation needs 18; insufficient eligible bench players can therefore cause later validation to fail. No automatic repair or model retry loop is configured in the export.

## Repository structure

```text
n8n_FantasyLeague_Assistant/
|-- README.md
|-- .gitignore
|-- .env.example
|-- docker-compose.yml
|-- published-workflows/
|   `-- My workflow.json       # Sanitized, importable n8n workflow
|-- scripts/
|   |-- anonymize_workflows.py # Generate public copies from private exports
|   `-- test_anonymize_workflows.py
|-- data/
|   `-- squad.json             # Tracked example roster, not n8n runtime data
|-- assets/
|   |-- telegram-report.png
|   `-- telegram-ai.png
`-- docs/
    |-- deployment.md          # Deployment, migration and backup instructions
    `-- publishing.md          # Sanitizing exports and cleaning local Git history
```

For a fresh installation, setup creates these local paths, which Git ignores:

```text
.env                          # Machine-specific Compose settings
workflows/
    My workflow.json          # Private original n8n export
files/
    squad.json                # Your roster, mounted at /files/squad.json
n8n-data/                     # n8n database, credentials and encryption configuration
```

The default runtime directory is `n8n-data/`; the tracked `data/squad.json` is only the example roster. Storage paths can be overridden in `.env`. Private backups belong outside version control; `backups/` is also ignored.

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/choppadebug/n8n_FantasyLeague_Assistant.git
cd n8n_FantasyLeague_Assistant
```

You need Docker with Compose, a Telegram bot created through [@BotFather](https://t.me/BotFather), a Gemini API credential for the AI branch, and network access to the data sources and model provider.

### 2. Configure your roster

For a fresh installation, run these commands in PowerShell from the repository directory:

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force n8n-data, files
Copy-Item data/squad.json files/squad.json
```

Edit `files/squad.json` with your own players. The structure is:

```json
{
  "players": [
    { "name": "Caprile", "role": "GK" },
    { "name": "Calhanoglu", "role": "MID" },
    { "name": "Pinamonti", "role": "FWD" }
  ]
}
```

This shortened example shows the format only. The workflow expects 25 players; the supplied roster contains 3 goalkeepers, 8 defenders, 8 midfielders, and 6 forwards. Supported roles are `GK`, `DEF`, `MID`, and `FWD`.

### 3. Start n8n

```powershell
docker compose config --quiet
docker compose up -d
```

Open [n8n locally](http://localhost:5678) and create the owner account.

Compose pins the n8n 2.46.6 image by digest, binds port 5678 to localhost, sets the container timezone to Europe/Rome, persists n8n state in `n8n-data/`, and mounts `files/` read-only. The `.env.example` file documents optional storage-path and host-port overrides.

**Existing installation:** follow the [migration and backup instructions](docs/deployment.md) before starting Compose. A fresh instance does not automatically use your existing workflows or credentials. Never run two n8n instances against the same SQLite data directory.

### 4. Import the workflow and configure integrations

1. In the n8n editor, import `published-workflows/My workflow.json` using **Import from File**.
2. Review the imported nodes and connections.
3. Create or select an n8n Telegram credential containing your bot token.
4. Start a conversation with your bot and replace `YOUR_TELEGRAM_CHAT_ID` in both Telegram nodes. Configure the Telegram credential on both nodes.
5. Confirm that both message texts are `{{ $json.message }}` and the parse mode is HTML.
6. Create or select a Google Gemini credential in `Google Gemini Chat Model`. Store the API key in n8n credentials, not in workflow JSON or JavaScript.
7. Review the model configured in the export (`models/gemini-3.8-flash`), and select a model available to your account. The exported options set temperature to `0.2` and maximum output tokens to `4000`.
8. Confirm that the model and `Structured Output Parser` are attached to `Basic LLM Chain`, and that `Validate AI Lineup` precedes the AI formatter and send node.

The published export does not provision the local roster or transfer Telegram or Gemini credential secrets. Configure them in your own installation. The AI branch sends the prepared roster evidence to Google's model service and can incur API usage charges.

Before enabling the schedule, inspect one execution through `Prepare LLM Input`, the parser, and `Validate AI Lineup`. Confirm 11 starters, seven distinct substitutes, the expected formation counts, and a `validation.valid` result of `true`. Check that each selection exists in your roster and that both Telegram outputs render correctly. These are deployment verification steps; repository inspection alone does not demonstrate a successful live Gemini call.

### 5. Verify scheduling and run

Review the Schedule Trigger and workflow timezone before enabling scheduled execution. The current export uses `0 12-21 * * *`, with the workflow timezone set to Europe/Zurich. Kickoff calculations explicitly use Europe/Rome, which follows the same current local-time rules. Workflow timezone settings take precedence over the container's default for scheduling.

The kickoff check parses Italian fixture dates, infers the year relative to the API update timestamp, and selects the earliest match across the returned fixtures. The squad-matching branch proceeds when that kickoff is more than zero and at most 120 minutes away. A kickoff outside the configured checking hours can fall outside the reporting window.

You can execute the workflow manually to inspect its output, but the same kickoff condition still applies to the squad-matching branch. Manual execution may therefore stop short of producing reports outside that window.

Publish or activate the workflow in your n8n editor to enable its schedule. Docker and the host machine must remain running for scheduled execution.

## Implementation notes

| Technology | Responsibility |
|---|---|
| n8n | Scheduling, orchestration, integrations, and execution inspection |
| JavaScript | Kickoff parsing, name matching, editorial extraction, and report formatting |
| Docker Compose | Repeatable self-hosted configuration and persistent storage |
| Fantamaster APIs | Lineup, fixture, availability, and editorial information |
| Google Gemini and n8n LLM chain | Formation, starting XI, ordered bench, and explanation generation |
| Structured parser and validation Code node | Output structure and roster/formation eligibility checks before AI delivery |
| Telegram | Report delivery |
| JSON | Squad configuration and workflow export |

Reports preserve the original squad order, use `N/D` for unavailable probabilities, distinguish home and away fixtures, and prioritize injury warnings. A favorable editorial recommendation does not imply a high starting probability.

## Security and operational limits

- Store Telegram tokens and Gemini API keys in n8n's credential system. Keep personal chat IDs, local paths, credential references, and pinned execution data out of public workflow exports and screenshots.
- Keep `.env`, `files/`, `n8n-data/`, and backups private. The full n8n data directory includes the encryption configuration needed to recover credentials.
- Review each new export before publishing: exporting again from a configured instance can restore personal values removed from an earlier copy. See the [publication review notes](docs/deployment.md), including the Git-history consideration.
- External API schemas, article slugs, and article formatting can change. Missing articles, ambiguous names, or unavailable sources can interrupt processing or reduce report completeness.
- The current article-source configuration uses the 2026/27 season; dynamic kickoff retrieval does not automatically update those season-specific slugs.
- The kickoff check controls the squad-matching branch, while article retrieval can start independently. Repeat-report suppression is not implemented.
- AI suggestions depend on the supplied evidence and can be mistaken even when structural validation passes. Review the reasons, risks, and bench coverage before setting your team.
- The configured formation list and substitution assumptions represent this workflow's fantasy rules; check that they match your league.

## Publishing workflow changes

Save your configured n8n exports in the ignored `workflows/` folder. Generate
sanitized copies before committing or pushing:

```powershell
python scripts/anonymize_workflows.py
python scripts/anonymize_workflows.py --check
```

The script uses Python 3.10+ with no additional dependencies. It writes only to
`published-workflows/`, preserves original exports, removes private metadata and
notes, replaces chat IDs, redacts common secrets (including Google/Gemini key patterns and `x-goog-api-key` headers) and personal paths, and disables
published workflows. Review generated changes and screenshots before committing.

See [publishing instructions](docs/publishing.md) for the full process and commands
to remove private workflows from local Git history before the first remote push.

## References

- [Source repository](https://github.com/choppadebug/n8n_FantasyLeague_Assistant)
- [n8n documentation](https://docs.n8n.io/)
- [n8n Docker Compose guide](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/)
- [n8n Telegram integration](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.telegram/)
- [Fantamaster projected lineups](https://www.fantamaster.it/probabili-formazioni-serie-a-live/)
- [Fantamaster fantasy advice](https://www.fantamaster.it/consigli-fantacalcio/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

Fantamaster content and predictions belong to their respective owners. This is an independent personal automation project. External data access is subject to the providers' applicable terms and usage restrictions.

## License

No license file is currently included in this repository.
