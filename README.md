# USP Market Place

This project is split into two isolated parts:

- `backend/`: FastAPI Python API
- `frontend/`: React/Vite web app

Keep Python files and backend dependencies inside `backend/`. Keep React files and Node dependencies inside `frontend/`.

## Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

API docs: `http://127.0.0.1:8000/docs`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

App URL: `http://localhost:5173/`
