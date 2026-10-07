# Data Export

Turn four sample inventory records into a CSV attachment for the configured operator. This app demonstrates response serialization and CSV generation.

## Technologies

- fastapi
- uvicorn
- pydantic
- jinja2
- Python 3.12
- SQLite
- stdlib urllib.request
- Mailtrap for email delivery

## Start locally

Use Python 3.12, the version used for the included checks. Commands below assume a POSIX shell; on Windows activate `.venv\Scripts\activate` instead.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c constraints.txt
cp .env.example .env
# Edit .env using the comments beside each variable.
python run.py
```

Open http://localhost:8000. Set your own `ADMIN_PASSWORD` (16 or more random characters); the operator username is `admin`. The entire app requires operator authentication except /health. Credentials are supplied by whoever runs the project and are never included in this repository.

For an immediate local trial, use `MAIL_MODE=log` and `APP_ENV=development`. The full message, including any attachment, is saved as an `.eml` file under `.data/mail-preview/`; no email is sent. Keep these files private. The default configuration uses a sandbox. [Email setup](docs/email-setup.md) explains both sandbox and live sending.

## Try it

Set OPERATOR_EMAIL and sign in as admin. Inspect the four seeded records at /items, then press Email inventory CSV or call POST /exports with HTTP Basic authentication. The response reports the row count and email state.

## How it works

`app.py` serializes SQLite rows through `InventoryItem` and uses `csv.DictWriter` to create a UTF-8 attachment. The destination is configured by the operator, not supplied by a public form.

`core.py` stores the request and intended email in one SQLite transaction before attempting the HTTP API. `/admin` shows request references and send states without publishing submitted content. Server-side credentials never appear in the page or API schema.

All form submissions have origin checks. Non-browser clients can omit Origin; operator authentication still applies. Each client is limited to 12 requests per hour and each recipient to 3. Forwarded IP headers are ignored; behind a reverse proxy, clients may share a limit. Add infrastructure-level limits before handling significant public traffic.

## Email states and retries

`accepted` means the email API accepted the message, not that it reached the inbox. `logged` is only a local preview. `failed` leaves the saved request intact; fix configuration and run:

```sh
python retry_email.py
```

The command retries pending messages and known failures. A connection loss while sending is `unknown`, and an interrupted process can leave a message `sending`. Neither state is automatically retried: inspect provider logs before manually reconciling it. There is no delivery-webhook integration.

## Tests and production startup

```sh
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pytest -q
python run.py --production
```

Tests use local mail doubles or preview files. Actual sending is optional and requires the operator’s own credentials; it is not a prerequisite for publishing this source. Runtime and test versions are pinned in the requirement files and `constraints.txt`. CI runs these checks on Python 3.12.

Production uses Uvicorn. Put it behind HTTPS, set `APP_URL` to the public origin, and keep `DB_PATH` on a persistent private volume. Use one application process for this demo. Basic authentication must be protected by HTTPS outside localhost. `--production` disables log-mode sending even if it remains selected in `.env`.

## Scope

The dataset is fixed and small; there are no arbitrary SQL queries, uploads, or spreadsheet-format exports. Stored request data and mail previews have no automatic retention cleanup. No database service, scheduler, Redis, or external account is required for local tests.

## License

MIT; see [LICENSE](LICENSE).
