Run the backend (Django):

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/api/health to check the API.

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

The current migrated installation uses `usp_marketplace_local`; keep that value to retain its copied data. Only loopback database hosts are accepted. The API runs in development mode, and the frontend always contacts `http://127.0.0.1:8000/api`.

Set a unique `SECRET_KEY` and your `ADMIN_PASSWORD` in `.env`, then log in using `ADMIN_EMAIL` (default `Admin@usp.ac.fj`) and that password. Restart the backend after changing `.env`.

The app will create tables automatically on startup.

## Local showcase demo

To use the local demo data instead of the MySQL database, start the backend from the repository root with `backend-demo.cmd`. This runs Django with `usp_backend.local_settings` and reads/writes only `backend/inventory-demo.db`. Start the frontend with `frontend.cmd` and open `http://localhost:5173/`.

Seed up to 1,000 active listings and 1,000 completed demo orders into that SQLite database:

```powershell
backend\venv\Scripts\python.exe backend\manage.py seed_inventory_demo --settings=usp_backend.local_settings --count 1000
backend\venv\Scripts\python.exe backend\manage.py seed_report_demo --settings=usp_backend.local_settings --count 1000
```

These commands are repeat-safe: rerunning them does not add duplicate generated listings or orders. The demo records remain separate from the regular local MySQL database.

Email verification:

For local development (`DEBUG=1`), the backend sends verification emails through SMTP when `EMAIL_HOST`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD` are configured. If the SMTP username or password is missing, verification codes are printed in the backend terminal instead. Configure `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0`, `EMAIL_HOST_USER` as your Gmail address, `EMAIL_HOST_PASSWORD` as your current Google App Password, and `DEFAULT_FROM_EMAIL` as the same address. Remove spaces from the app password if Google displays it in groups. If Gmail closes the connection using port 587, try its implicit-SSL endpoint instead: set `EMAIL_PORT=465`, `EMAIL_USE_TLS=0`, and `EMAIL_USE_SSL=1`. Do not set both TLS and SSL to `1`.

Resend is also supported. Set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` in `.env`; the Resend sender must be verified in your Resend account. Choosing `EMAIL_PROVIDER=resend` uses its HTTPS API even if Gmail SMTP settings are also present. With `EMAIL_PROVIDER=auto` (the default), configured SMTP takes precedence; Resend is selected automatically only when SMTP is not configured.

Resend SMTP is supported as well. Set `EMAIL_HOST=smtp.resend.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_HOST_USER=resend`, `EMAIL_HOST_PASSWORD` to your Resend API key, and `DEFAULT_FROM_EMAIL` to a verified sender. SMTP takes priority when `EMAIL_HOST` is configured.

Registration is restricted to USP student email addresses in the `S<number>@student.usp.ac.fj` format (for example, `S12345678@student.usp.ac.fj`). Other email addresses are rejected in all environments.

Verification codes are sent to the exact email address used at registration. For actual delivery, configure SMTP or Resend as described above; without an email provider, codes are printed in the backend terminal.

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
