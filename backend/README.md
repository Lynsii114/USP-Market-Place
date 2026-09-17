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
