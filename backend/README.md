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

Set `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0`, `EMAIL_HOST_USER` to your Gmail address, `EMAIL_HOST_PASSWORD` to your Gmail app password, and `DEFAULT_FROM_EMAIL` to the same address in `.env` to send verification codes through SMTP. Remove spaces from the app password if Google displays it in groups. Gmail requires 2-Step Verification and a 16-character App Password; your normal Gmail password will not work. For local development, leave `EMAIL_HOST` unset and the code will be printed in the backend terminal.

Resend is also supported. Set `RESEND_API_KEY` and `RESEND_FROM_EMAIL` in `.env`; the Resend sender must be verified in your Resend account. Resend is used automatically when `RESEND_API_KEY` is present.

Resend SMTP is supported as well. Set `EMAIL_HOST=smtp.resend.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_HOST_USER=resend`, `EMAIL_HOST_PASSWORD` to your Resend API key, and `DEFAULT_FROM_EMAIL` to a verified sender. SMTP takes priority when `EMAIL_HOST` is configured.

Authenticator security:

Registration is limited to USP student addresses in the form `S12345678@student.usp.ac.fj`. After email verification, add the displayed secret to Microsoft Authenticator using the `Other account` option. Every password login then requires the six-digit rotating code from Microsoft Authenticator.

Payment checkout demo:

Checkout simulates authorization for demonstration only. It is not connected to Visa, MyCash, or M-PAiSA and never charges or stores real payment credentials. Use only these test values:

- VISA success: card `4242 4242 4242 4242`; any cardholder name, future `MM/YY` expiry, and three-digit security code.
- VISA insufficient-funds decline: card `4000 0000 0000 9995`; use the same expiry and security-code format.
- MyCash or M-PAiSA success: any demo mobile number and authorization code `123456`.
- MyCash or M-PAiSA insufficient-funds decline: any demo mobile number and authorization code `000000`.
- Cash: no payment details are needed; checkout records a simulated cash-on-handoff payment.
- To force a failed attempt with any selected method, check **Force payment failure** before selecting **Pay Now**.

Successful simulated payments create an order and update listing stock. Failed payments create no order and leave stock unchanged. Do not enter actual card numbers, CVVs, wallet PINs, or one-time passcodes.

Password reset:

Users can select `Forgot password?` on the login page. The backend sends a six-digit reset code to the registered USP email. The code expires after 10 minutes, allows at most five attempts, and can only be used once. After resetting the password, Microsoft Authenticator is still required at login.
