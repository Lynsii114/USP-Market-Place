USP Market Place — React frontend + FastAPI backend

Quick start:

Frontend
```
cd frontend
npm install
npm run dev
```

Backend
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Next steps: add database models, authentication, and Docker setup.
