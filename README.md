# USP Buy & Sell

This project is split into two isolated parts:

- `backend/`: Django Python API
- `frontend/`: React/Vite web app

Keep Python files and backend dependencies inside `backend/`. Keep React files and Node dependencies inside `frontend/`.

## Project structure

```text
usp-marketplace/
├── frontend/
├── backend/
├── Dockerfile
├── README.md
├── backend.cmd
├── backend-demo.cmd
└── frontend.cmd
```

## Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8000
```

API health check: `http://127.0.0.1:8000/api/health`

Database health check: `http://127.0.0.1:8000/api/health/database`

### Local showcase demo

The showcase seed commands use an isolated SQLite database at `backend/inventory-demo.db`; they do not add demo data to MySQL or Vercel. To view that data in the local web app, start the API with the same SQLite settings:

```powershell
.\backend-demo.cmd
```

Then start the frontend with `.\frontend.cmd` and open `http://localhost:5173/`. Re-run the seed commands from the repository root if needed:

```powershell
backend\venv\Scripts\python.exe backend\manage.py seed_inventory_demo --settings=usp_backend.local_settings --count 1000
backend\venv\Scripts\python.exe backend\manage.py seed_report_demo --settings=usp_backend.local_settings --count 1000
```

The normal `backend.cmd` continues to use the database configured for the regular backend; it will not show records stored only in the isolated demo database.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

App URL: `http://localhost:5173/`

## Vercel environment variables

Frontend project:

```text
VITE_API_URL=https://usp-market-place-h5f5-gm540cfl3-usp-marketplace.vercel.app/api
VITE_MICROSOFT_CLIENT_ID=your-entra-application-client-id
VITE_MICROSOFT_TENANT_ID=your-usp-tenant-id
```

Backend project:

```text
DEBUG=0
SECRET_KEY=your-long-random-django-secret
DB_HOST=your-aiven-mysql-host
DB_PORT=your-aiven-mysql-port
DB_DATABASE=your-aiven-database-name
DB_USERNAME=your-aiven-username
DB_PASSWORD=your-aiven-password
DB_SSL=VERIFY_CA
DB_SSL_CA_CERT=-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----
AUTO_ENSURE_SCHEMA=0
LOCAL_DB_SYNC=0
LOCAL_DB_SYNC_ON_START=0
DB_CONNECT_TIMEOUT=10
DB_READ_TIMEOUT=10
DB_WRITE_TIMEOUT=10
DB_CONN_MAX_AGE=60
DJANGO_ALLOWED_HOSTS=.vercel.app,your-backend-domain.vercel.app
CORS_ALLOWED_ORIGINS=https://usp-market-place.vercel.app
CORS_ALLOWED_ORIGIN_SUFFIXES=.vercel.app
CSRF_TRUSTED_ORIGINS=https://usp-market-place.vercel.app
```
