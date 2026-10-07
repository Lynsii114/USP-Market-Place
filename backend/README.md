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

This backend uses MySQL/phpMyAdmin only. SQLite is disabled.

1. Create a MySQL database, for example `usp_marketplace`.
2. Set `DATABASE_URL` in a `.env` file in the `backend` folder:

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/usp_marketplace
```

The app will create tables automatically on startup.

Email verification:

For local development (`DEBUG=1`), the backend sends verification emails through SMTP when `EMAIL_HOST`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD` are configured. If the SMTP username or password is missing, verification codes are printed in the backend terminal instead. Configure `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0`, `EMAIL_HOST_USER` as your Gmail address, `EMAIL_HOST_PASSWORD` as your current Google App Password, and `DEFAULT_FROM_EMAIL` as the same address. Remove spaces from the app password if Google displays it in groups. If Gmail closes the connection using port 587, try its implicit-SSL endpoint instead: set `EMAIL_PORT=465`, `EMAIL_USE_TLS=0`, and `EMAIL_USE_SSL=1`. Do not set both TLS and SSL to `1`.

Resend is also supported. Set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` in `.env`; the Resend sender must be verified in your Resend account. Choosing `EMAIL_PROVIDER=resend` uses its HTTPS API even if Gmail SMTP settings are also present. With `EMAIL_PROVIDER=auto` (the default), configured SMTP takes precedence; Resend is selected automatically only when SMTP is not configured.

Resend SMTP is supported as well. Set `EMAIL_HOST=smtp.resend.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_HOST_USER=resend`, `EMAIL_HOST_PASSWORD` to your Resend API key, and `DEFAULT_FROM_EMAIL` to a verified sender. SMTP takes priority when `EMAIL_HOST` is configured.

Testing with non-USP email addresses:

For local testing, any valid email address is allowed by default. To restore USP student email-only registration, set `ALLOW_NON_USP_EMAILS=0` in `backend/.env` and restart the backend. Non-USP test accounts do not receive a student ID.

Verification codes are sent to the exact email address used at registration. For actual delivery, configure SMTP or Resend as described above; without an email provider, codes are printed in the backend terminal.

Authenticator security:

After email verification, add the displayed secret to Microsoft Authenticator using the `Other account` option. Every password login then requires the six-digit rotating code from Microsoft Authenticator.

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

Sellers can select Cash, MyCash, or M-PAiSA for a listing. MyCash and M-PAiSA require a valid phone number; Cash does not. The API never includes the receiving number in public listing responses. It is included only for the listing's seller or the buyer while that listing is actively reserved for them. This listing preference is informational and does not change the simulated checkout method or authorize a real transfer. The access check follows the API's existing caller-supplied user-ID convention; because requests are not authenticated, it does not prevent a client from forging another user's ID.

Password reset:


Users can select `Forgot password?` on the login page. The backend sends a six-digit reset code to the registered email. The code expires after 10 minutes, allows at most five attempts, and can only be used once. After resetting the password, Microsoft Authenticator is still required at login.
