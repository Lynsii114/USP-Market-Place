# USP Buy & Sell

A local marketplace with a React/Vite frontend, Django API, and MySQL/MariaDB database.

## Local setup

1. Start **MySQL** in the XAMPP Control Panel.
2. Create a database in phpMyAdmin, such as `usp_marketplace`.
3. Copy `backend/.env.example` to `backend/.env` if no `.env` exists. Set the database name, local username/password, a unique `SECRET_KEY`, and your administrator password. Keep existing credentials when updating an installation.
4. Install backend dependencies:

For local XAMPP development, start MySQL in XAMPP and run `npm run backend`
from the repository root (or `backend.cmd`). This uses `usp_backend.xampp_settings`
and the existing `usp_marketplace` database at `127.0.0.1:3306`.
The default local MySQL user is `root` with no password; override it with
`LOCAL_DB_USERNAME` and `LOCAL_DB_PASSWORD` in `backend/.env` if needed.
The local API runs at `http://localhost:8000` and the frontend at
`http://localhost:5173` using `npm run frontend`.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

5. Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

6. Start both servers in separate terminals:

```powershell
.\backend.cmd
```

```powershell
.\frontend.cmd
```

Or run `npm run dev` from the repository root after `npm install`.

Open http://localhost:5173/. The backend listens at http://127.0.0.1:8000/.

## Database and administrator login

The backend always uses local MySQL and accepts only loopback database hosts. Configure it with `LOCAL_DB_HOST`, `LOCAL_DB_PORT`, `LOCAL_DB_DATABASE`, `LOCAL_DB_USERNAME`, and `LOCAL_DB_PASSWORD` in `backend/.env`. The schema is prepared automatically when the API starts.

Sign in using the `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `backend/.env`. The default administrator email is `Admin@usp.ac.fj`. The application runs in local development mode.

On the current migrated installation, `LOCAL_DB_DATABASE=usp_marketplace_local`. Existing accounts, listings, and orders were copied there. The pre-switch data backup is stored in the ignored `.local-backups/` directory. The older `usp_marketplace` database was left intact.

Check the API at http://127.0.0.1:8000/api/health and database connectivity at http://127.0.0.1:8000/api/health/database.

## Isolated showcase demo

The optional demo uses a separate SQLite file, `backend/inventory-demo.db`:

```powershell
.\backend-demo.cmd
```

Seed demo data when needed:

```powershell
backend\venv\Scripts\python.exe backend\manage.py seed_inventory_demo --settings=usp_backend.local_settings --count 1000
backend\venv\Scripts\python.exe backend\manage.py seed_report_demo --settings=usp_backend.local_settings --count 1000
```

These commands do not modify the regular MySQL database. Start the frontend with `frontend.cmd`.

## Email and payment demonstrations

Email verification can use a configured email provider, which requires internet access. Set `EMAIL_PROVIDER=console` to print verification codes in the backend terminal for local demonstrations. Checkout simulates payments and never transfers real money.

See `backend/README.md` for authentication, email, checkout, and inventory behaviour.
