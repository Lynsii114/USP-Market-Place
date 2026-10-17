# Inventory fixes and local preview

## What changed

- Stock and checkout quantities must be bounded whole numbers. Negative, fractional, boolean, and overflowing values are rejected. Prices must be finite, non-negative, and within the supported range. Required text is trimmed and checked against model lengths; categories must be built-in or administrator-created.
- Seller content edits preserve inactive listings. Administrator-hidden and removed listings reject seller mutations; hidden listings cannot be purchased through stale carts or direct purchase routes. The seller UI shows moderation restrictions and an explicit Reactivate action for seller-deactivated listings.
- Unpaid orders reserve inventory until payment confirmation or cancellation. Cancellation is terminal and idempotent, preserves hidden state, and does not release a different buyer's reservation. Administrator restoration reconstructs pending reservations. Approved demo payments, like seller-confirmed payments, cannot be cancelled without a refund workflow.
- Listing deletion and purchase helpers lock inventory in transactions. Active orders prevent deletion. Seller progress updates and buyer completion lock orders, enforce payment prerequisites, and reject backward/terminal transitions.
- Protected API calls require signed bearer tokens bound to the active account. Caller IDs are checked against that identity, and public viewer parameters cannot disclose another user's payment number. Password/MFA challenges expire after ten minutes; access tokens expire after eight hours and are invalidated by credential changes. The frontend holds tokens in memory and clears them at logout; refreshing the page requires signing in again.
- Passwords now use Django's salted password hasher. Existing SHA-256 passwords are verified and upgraded at login. Production no longer enables the hardcoded development administrator password; configure ADMIN_PASSWORD and SECRET_KEY. The known development password is rejected for production administrator login.
- Restored missing API routes used by seller reviews and password-reset verification. SMTP delivery errors retain technical details in server logs rather than returning them to the browser.

No model columns were added. Existing `removed_reason` distinguishes administrator hiding (non-null) from seller deactivation (null); a future separate moderation field would make that distinction more explicit. Cash reservations still block the whole listing, matching existing behavior.

## Run locally (PowerShell)

From the repository root, run the following setup once:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Push-Location frontend
npm.cmd install
Pop-Location
backend/.venv/Scripts/python.exe backend/manage.py migrate --run-syncdb --settings=usp_backend.local_settings
backend/.venv/Scripts/python.exe backend/manage.py seed_inventory_demo --settings=usp_backend.local_settings
```

Start the backend and frontend in separate terminals:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000 --settings=usp_backend.local_settings
```

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173/. Local settings always use the ignored `backend/inventory-demo.db` SQLite file and disable cloud synchronization and automatic legacy schema upgrades. Production MySQL configuration is unchanged. The demo seed command refuses non-local settings.

Local administrator: `Admin@usp.ac.fj` / `Admin12345`. After login choose **Go back**, then **My Activity → My Listings**. Five sample listings belong to this account, including inactive and administrator-hidden examples. Existing demo records are not overwritten when reseeding.

Student accounts: `demo_seller` or `demo_buyer`, password `Demo314!`. First login displays authenticator setup; use an authenticator app as in the existing project. These accounts are local samples, not team or production accounts. For the student purchase flow, sign out of the administrator account, sign into demo_buyer, then buy a sample listing with cash. Sign back in as administrator to confirm payment under My Sales.

## Verify

From `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe manage.py test marketplace.tests --settings=usp_backend.local_settings
```

Pytest is forced to isolated in-memory test settings before collection. Existing business-flow tests use a clearly named authenticated test client; the new authentication regression tests use Django's unmodified Client to verify unauthenticated and impersonation rejection. The old dashboard test now confirms cash receipt before expecting revenue. Email tests explicitly select and mock their provider so they do not depend on a developer's email environment.

From `frontend`, run `npm.cmd run build`.

Verified locally: 79 tests passed, 31 subtests passed, and two MySQL-only concurrency tests were skipped. The production frontend build passed. Browser verification covered administrator login, authenticated dashboard loading, and My Listings showing inactive and administrator-restricted inventory with the Reactivate action.

SQLite verifies business logic, transactions, API validation, and authentication, but cannot prove MySQL row-lock behavior. Two real concurrency tests are included and explicitly skipped on SQLite. Run `manage.py test marketplace.tests` against a dedicated MySQL test configuration with schema auto-upgrade and cloud synchronization disabled before deploying. Do not point standalone scripts at a shared production database.

## Deployment and remaining limits

Deploy the updated frontend and backend together: old clients do not send credentials. Set a unique production SECRET_KEY, DEBUG=0, and a strong ADMIN_PASSWORD; rotate any previously deployed default administrator credentials. Use HTTPS. No real payment gateway or refund implementation was added. Full production security hardening, including distributed login/MFA rate limits and server-side per-token logout revocation, remains separate work. Tokens are valid until expiry unless account status or credentials change.

The changes are implementation and testing contributions, not authorship of the original inventory module. For the final report, credit the original implementation and record the corrected defects, design choices, tests, and actual contribution commit. Match those changes to the SRS/SAD when those documents are available.
