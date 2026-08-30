Run the backend (FastAPI):

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs for API docs.

Using MySQL:

1. Create a MySQL database (example name: `usp_marketplace`).
2. Set `DATABASE_URL` in a `.env` file in the `backend` folder. Example:

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/usp_marketplace
```

The app will create tables automatically on startup.
