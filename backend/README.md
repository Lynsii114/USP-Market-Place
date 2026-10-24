Run the backend (Django):

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/api/health to check the API.

## Secret key and Railway environment variables

Before starting locally, copy `.env.example` to `.env` if it does not already
exist. Replace its `SECRET_KEY` placeholder with a unique random secret and use
`DEBUG=true` for local development. `backend/.env` is ignored by Git; never commit
it. To generate a key, run the following locally and store the output privately:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

In your Railway backend service's **Variables**, set:

- `SECRET_KEY`: a separately generated random secret.
- `DEBUG`: `false` (also the default when unset).
- `DATABASE_MODE`: `railway` (locally, keep `DATABASE_MODE=local`).
- `ALLOWED_HOSTS`: your backend hostname, for example
  `your-service.up.railway.app`, with additional hostnames separated by commas.
  Use hostnames without `https://`, paths, or ports.

Railway environment variables take precedence over `.env` values. A missing,
empty, whitespace-only key or the retired `dev-secret-key` fallback stops Django
with a configuration error. Local development also requires a key in `.env` or
the environment. `DEBUG` accepts `true`, `1`, `yes`, or `on` (case-insensitive);
other values disable it. Railway mode requires `ALLOWED_HOSTS`; local mode
defaults to local hosts.

From `backend`, verify the loaded key without displaying it or accessing the
database, then run Django's system checks:

```powershell
python manage.py check_secret_key
python manage.py check
python -m unittest discover -s marketplace/tests -p test_security_configuration.py
```

The first command prints `SECRET_KEY loaded successfully (value hidden).` on
success. Run `python manage.py check_secret_key` inside the Railway service to
verify its deployed configuration too.

## Deploy the backend to Railway

Use branch `Railway-deployement-trial` and set the backend service's **Root
Directory** to `/backend`. The backend-only Dockerfile installs the Python
dependencies and starts Gunicorn. The repository-root Dockerfile also uses
Gunicorn, but still builds the frontend; `/backend` avoids that unnecessary
frontend build when Vercel hosts it separately.

Set these in the **backend service's Railway Variables**, replacing angle-bracket
placeholders privately (do not paste placeholders as real credentials):

```dotenv
DATABASE_MODE=railway
DEBUG=false
SECRET_KEY=<a-unique-random-production-secret>
ALLOWED_HOSTS=<your-backend>.up.railway.app,healthcheck.railway.app
CORS_ALLOWED_ORIGINS=https://<your-frontend>.vercel.app
CSRF_TRUSTED_ORIGINS=https://<your-frontend>.vercel.app
DB_HOST=nozomi.proxy.rlwy.net
DB_PORT=39149
DB_USER=root
DB_DATABASE=railway
DB_PASSWORD=<your-existing-Railway-MySQL-password>
AUTO_ENSURE_SCHEMA=0
```

When the backend and database are in the same project/environment, use Railway's
variable reference picker for `DB_PASSWORD` to reference the existing MySQL
service's `MYSQLPASSWORD`, rather than putting it in source.
If the service is named `MySQL`, the reference is `${{MySQL.MYSQLPASSWORD}}`.
For services in the same Railway project/environment, you can instead reference
that MySQL service's private `MYSQLHOST` and `MYSQLPORT` together. Do not mix a
private host with the public proxy port above. No new database is needed.

The current public backend is in project `disciplined-serenity`, while the
existing MySQL service is in `shimmering-endurance`. This deployment therefore
uses the public proxy host/port above and stores the existing database password
privately in the backend's Railway Variables. Same-project `${{MySQL.*}}`
references do not connect these two projects. Do not move, recreate, or reset
the existing MySQL service to fix a missing backend variable.

`DATABASE_MODE=railway` uses only `DB_*`; it never falls back to local credentials
if a required value is missing. Railway's `RAILWAY_ENVIRONMENT_ID` selects this
mode automatically when `DATABASE_MODE` is not set. Locally, `DATABASE_MODE=local`
uses the existing `LOCAL_DB_*` values and loopback host restriction. The custom
`usp_backend.mysql_backend` engine is preserved for both modes.

Railway mode **always disables automatic schema creation/upgrades**, even if
`AUTO_ENSURE_SCHEMA=1` was inherited. The Docker startup commands run no
migrations, seeds, or schema commands. Leave Railway's **Pre-deploy Command**
empty and remove any old migration/seed commands from service overrides. The
existing database must already contain the tables and columns the app expects;
missing schema will need a separately reviewed update, not an automatic fix.

Leave Railway's custom **Start Command** empty to use the Dockerfile. If an
override is needed, wrap it in a shell so Railway expands `$PORT`:

```sh
/bin/sh -c "exec gunicorn usp_backend.wsgi:application --bind 0.0.0.0:$PORT"
```

The Dockerfile uses the same command with a local Docker port fallback of 8000
and `exec` for correct shutdown. Gunicorn runs on Linux; use `runserver` locally
on Windows. This workspace cannot validate a Docker build without Docker.

Set Railway's healthcheck path to `/api/health`. Include
`healthcheck.railway.app` in `ALLOWED_HOSTS` for Railway's probe. The exact
database-free `/api/health` path is exempt from HTTPS redirects so internal HTTP
probes receive 200. Test other public endpoints with HTTPS: Railway mode trusts
the proxy's `X-Forwarded-Proto` header, redirects HTTP to HTTPS when `DEBUG=false`,
sets secure cookies and security headers, and enables one-hour HSTS. HSTS
subdomain coverage and preload remain disabled until all relevant domains are
known to support HTTPS; `check --deploy` reports these two advisory warnings.
CSRF middleware is enabled; existing API view exemptions and bearer-token
authentication are preserved.

CORS allows only the explicit origins configured above. Include `https://` and
any port, without a path. Separate multiple origins with commas. Add individual
Vercel preview origins explicitly if needed; all `vercel.app` sites are not
trusted automatically. CORS responses vary by Origin to prevent cache confusion.

In **Vercel**, set the public build variable and rebuild the frontend:

```dotenv
VITE_API_URL=https://<your-backend>.up.railway.app/api
```

The local frontend still defaults to `http://127.0.0.1:8000/api`. Never put
database passwords, backend secrets, or other private values in `VITE_*`
variables: they are included in browser bundles.

The existing Vercel project is `usp-marketplace/usp-market-place`, with Root
Directory `frontend`. `.vercelignore` excludes the backend, local environment
files, virtual environments, and database backups from CLI frontend uploads.
Local `.vercel` project-link metadata is ignored by Git. Configure `VITE_API_URL`
for both Production and Preview, and build the updated
`Railway-deployement-trial` branch when deploying without merging into `main`.

Before publishing, run the configuration tests above. In a configured Railway
service shell, run these checks (neither command queries or modifies tables):

```sh
python manage.py check_secret_key
python manage.py check --deploy
```

After you choose to deploy, test the public health and CORS endpoints:

```powershell
curl.exe -i https://<your-backend>.up.railway.app/api/health
curl.exe -i -X OPTIONS https://<your-backend>.up.railway.app/api/health -H "Origin: https://<your-frontend>.vercel.app" -H "Access-Control-Request-Method: GET"
```

`/api/health` tests the application without touching the database.
`/api/health/database` runs only `SELECT 1`; you can call it separately when you
want to check live connectivity. That is not a schema compatibility check.
No live connectivity or table compatibility was verified by the offline checks.

Database:

The regular backend uses local XAMPP MySQL/MariaDB. The optional showcase demo uses a separate, isolated SQLite database.

1. Start MySQL in XAMPP and create a database in phpMyAdmin.
2. Copy `.env.example` to `.env` if needed and set these local connection values:

```dotenv
LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=3306
LOCAL_DB_DATABASE=usp_marketplace
LOCAL_DB_USERNAME=root
LOCAL_DB_PASSWORD=
```

The current local installation uses `usp_marketplace_local`; keep that value to retain its copied data. Local mode accepts only loopback database hosts. Set `DEBUG=true` locally; the local frontend defaults to `http://127.0.0.1:8000/api`.

Set a unique `SECRET_KEY` and your `ADMIN_PASSWORD` in `.env`, then log in using `ADMIN_EMAIL` (default `Admin@usp.ac.fj`) and that password. Restart the backend after changing `.env`.

Local mode can create/upgrade tables on startup when `AUTO_ENSURE_SCHEMA=1`.
Railway mode never performs this automatic schema work.

## Messaging schema migrations

`Conversation` uses a named composite unique constraint on `(item_id, buyer_id,
seller_id)`. `Message` stores `conversation_id`, `sender_id`, `receiver_id`,
`body`, `is_read`, and `created_at`. Railway's existing MySQL table also has a
required legacy `sender_username` column, which sends now populate. Migration
`0003` adopts that column if it already exists or adds it with a blank default
if it does not, preserving existing message rows. The API endpoints are
`POST /api/items/<item_id>/conversation`, `GET /api/users/<user_id>/conversations`,
`GET|POST /api/conversations/<conversation_id>`, and
`GET /api/users/<user_id>/messages/unread`.

The initial migration records the legacy marketplace model state and creates
only tables that are absent; it leaves existing tables and rows in place. The
messaging repair migration adds missing messaging columns only when the
affected table is empty, and adds the unique index only if there are no
duplicate conversation tuples. It stops with an error and preserves all rows
when required values cannot be inferred safely or duplicates exist. Neither
migration runs automatically on Railway startup.

Before any production rollout, back up the Railway MySQL database and verify
the schema against that backup. Review the pending operations without applying
them by running this from `backend` with the production variables loaded in a
Railway shell:

```sh
python manage.py migrate --plan
```

Only after the plan and backup are reviewed should migrations be applied
explicitly. This change does not alter the local XAMPP or SQLite startup paths;
they continue to use their existing `AUTO_ENSURE_SCHEMA` behavior and do not
run these Django migrations automatically.

## Local showcase demo

To use the local demo data instead of the MySQL database, start the backend from the repository root with `backend-demo.cmd`. This runs Django with `usp_backend.local_settings` and reads/writes only `backend/inventory-demo.db`. Start the frontend with `frontend.cmd` and open `http://localhost:5173/`.

Seed up to 1,000 active listings and 1,000 completed demo orders into that SQLite database:

```powershell
backend\venv\Scripts\python.exe backend\manage.py seed_inventory_demo --settings=usp_backend.local_settings --count 1000
backend\venv\Scripts\python.exe backend\manage.py seed_report_demo --settings=usp_backend.local_settings --count 1000
```

These commands are repeat-safe: rerunning them does not add duplicate generated listings or orders. The demo records remain separate from the regular local MySQL database.

## Email delivery

Registration verification, password resets, and account notification emails use
the same `send_email()` function. The transport is selected by deployment mode:
local development uses Gmail SMTP; Railway uses the Resend HTTPS API at
`https://api.resend.com/emails`. Railway never reads or falls back to the local
SMTP credentials. Local mode does not require the Resend API key.

For local Gmail SMTP, set `EMAIL_HOST=smtp.gmail.com`, port `587`, TLS on, SSL
off, the Google or Google Workspace account in `EMAIL_HOST_USER`, and its app
password in `EMAIL_HOST_PASSWORD`. Gmail app passwords are often displayed in
groups with spaces; settings removes those spaces before login. `DEFAULT_FROM_EMAIL`
should match the authenticated Google account. If the sender uses a custom
domain, the mailbox must be hosted by Google Workspace and allowed to send via
SMTP. Never commit the app password or local `SECRET_KEY`.

Railway uses `RESEND_API_KEY` and `RESEND_FROM_EMAIL`; the sender domain must be
verified in Resend. Missing credentials fail clearly without falling back to
another provider or printing verification/reset codes to a terminal.

Gunicorn starting successfully does not test email delivery. A Resend error on
Railway means production credentials or provider access need checking. Verify
the active deployment and inspect its email logs after a delivery attempt.
Railway Variables override `backend/.env`. Docker excludes `.env`, so configure
production secrets directly in Railway.

Configure these values before starting locally or deploying:

| Variable | Local `backend/.env` | Railway backend Variables |
| --- | --- | --- |
| `EMAIL_HOST` / `EMAIL_PORT` | `smtp.gmail.com` / `587` | Not used |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | `1` / `0` | Not used |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Google account and private app password | Not used |
| `DEFAULT_FROM_EMAIL` | Sender matching the Google account | Not used |
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` | Not used | Private Resend key and verified sender |
| `FRONTEND_URL` | `http://localhost:5173` | `https://www.uspmarketplace.online` |

Use a sender such as `USP Marketplace <no-reply@your-verified-domain.example>`,
replacing the example domain with one verified in your Resend account. A Gmail
address or an unverified domain cannot substitute for a verified Resend sender.
Use separate API keys per environment when possible. Keep keys in ignored `.env`
files or Railway Variables; never put them in Git, Vercel `VITE_*` variables,
terminal arguments, or chat. Resend's onboarding/test sender has recipient
restrictions and is not suitable for sending to arbitrary student addresses.

The app still uses six-digit codes with the existing expiry and verification
logic. Email return links open the configured frontend so users can enter their
codes; clicking a link does not bypass verification or reset a password.
Production frontend URLs must use HTTPS. No database or authentication settings
need to change for this email-provider switch.

Restart local Django after changing `.env`. Keep the SMTP app password only in
the ignored local environment file. Configure the Resend variables in Railway;
those settings take effect after the service redeploys. `--check-only` reports
the effective local SMTP or Railway Resend transport without displaying
secrets or sending email.

From `backend`, check configuration without sending mail or accessing a database:

```powershell
python manage.py check
python manage.py test_email_delivery --check-only
python -m pytest marketplace/tests/test_resend_email.py marketplace/tests/test_security_configuration.py marketplace/tests/test_account_moderation.py -q -p no:cacheprovider
```

To send one explicit email to an address you control (replace the example):

```powershell
python manage.py test_email_delivery --to your-address@example.com
```

Run the same command **inside the Railway container** to test production's
network and variables through Resend. `railway run` executes locally and is not
a production network test. With CLI SSH access configured, use:

```sh
railway ssh --project disciplined-serenity --environment production --service USP-Market-Place -- python manage.py test_email_delivery --to your-address@example.com
```

The command sends through the shared email function. It does not register users,
generate real verification/reset records, or access MySQL. `--check-only` checks
that settings are present; it does not validate SMTP/Resend authentication or
sender authorization. Provider acceptance is not proof of inbox delivery:
inspect the recipient inbox and provider delivery logs. Railway needs no SMTP
port access.

Registration is restricted to USP student email addresses in the `S<number>@student.usp.ac.fj` format (for example, `S12345678@student.usp.ac.fj`). Other email addresses are rejected in all environments.

Verification codes are sent to the exact email address used at registration.
There is no fixed test recipient, recipient override, or test-only account mode.
To test manually, register through the local frontend with an email address you
control, receive the code there, and enter it in that same local flow. Repeat
through the production frontend to test Railway. Local and production accounts
remain in their existing separate databases; this email change does not copy
accounts between them.
Local email delivery requires the SMTP host, account, app password, and sender.
Railway email delivery requires the Resend API key and verified sender. Missing
configuration raises an email error instead of switching providers or printing
a verification code.

Authenticator security:

After email verification, users can choose whether to set up Microsoft Authenticator. Users who skip setup can log in with their username or email and password, and are offered setup again after login. Users who enable it must enter the six-digit rotating authenticator code after every password login. During setup, add the displayed QR code or secret to Microsoft Authenticator using the `Other account` option.

Payment checkout demo:

Checkout simulates authorization for demonstration only. It is not connected to Visa, MyCash, or M-PAiSA and never charges or stores real payment credentials. Use only these test values:

- VISA success: card `4242 4242 4242 4242`; any cardholder name, future `MM/YY` expiry, and three-digit security code.
- VISA insufficient-funds decline: card `4000 0000 0000 9995`; use the same expiry and security-code format.
- MyCash or M-PAiSA success: any demo mobile number and authorization code `123456`.
- MyCash or M-PAiSA insufficient-funds decline: any demo mobile number and authorization code `000000`.
- Cash: no payment details are needed. Checkout creates a pending order and reserves the item without reducing stock or marking it paid. The seller confirms the cash after delivery or self-pickup; cancelling/releases the pending order clears the reservation without reducing stock.
- To simulate a failed attempt with any selected method, check **Simulate failed payment (for testing)** before confirming checkout.

Successful simulated digital payments create an order and update listing stock immediately. Cash remains pending until the seller confirms receipt, at which point stock is reduced. Failed attempts create no order and leave stock unchanged. Do not enter actual card numbers, CVVs, wallet PINs, or one-time passcodes.

Listing payment details:

Sellers can select Cash, MyCash, or M-PAiSA for a listing. MyCash and M-PAiSA require a valid phone number; Cash does not. The API never includes the receiving number in public listing responses. It is included only for the listing's seller or the buyer while that listing is actively reserved for them. This listing preference is informational and does not change the simulated checkout method or authorize a real transfer. Protected requests use signed access tokens, and the server checks acting user IDs against the signed-in account.

Password reset:


Users can select `Forgot password?` on the login page. The backend sends a six-digit reset code to the registered email. The code expires after 10 minutes, allows at most five attempts, and can only be used once. After resetting the password, authenticator verification is required only for accounts that have enabled it.


### Existing databases and multiple-unit listings

The listing form stores the multiple-unit choice in `items.multiple_units`, so a
listing remains a multiple-unit listing when its remaining stock reaches one.
For an existing database with automatic schema upgrades disabled, run this once
using the appropriate settings before starting the updated backend:

```powershell
# Isolated local demo database
.\.venv\Scripts\python.exe manage.py upgrade_listing_quantities --settings=usp_backend.local_settings
```

For the regular local database, run `python manage.py upgrade_listing_quantities`
from the backend directory. The command adds the missing column
and marks existing listings with multiple stock or recorded paid units as
multiple-unit listings. Repeating it does not overwrite seller choices.

Unpaid orders hold their requested quantities. Seller-created reservations hold
one unit. Remaining units can be purchased by other buyers. Fully reserved listings are visible only to their seller and buyers holding a reservation.
