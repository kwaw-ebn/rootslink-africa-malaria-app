# Rootslink Africa Malaria Outreach Prototype

This package contains a GitHub Pages frontend and a Render FastAPI backend.

## Architecture

GitHub Pages frontend
→ HTTPS requests
→ Render FastAPI backend
→ PostgreSQL database

The application is designed for non-identifying malaria outreach and education program data.

## Folder structure

- `frontend/index.html` — complete Rootslink Africa frontend
- `frontend/.nojekyll` — GitHub Pages helper
- `backend/main.py` — FastAPI API
- `backend/requirements.txt` — Python dependencies
- `backend/render.yaml` — Render blueprint
- `backend/.env.example` — environment-variable examples

## Backend workflow

The backend provides:

- `GET /health`
- `GET /api/outreaches`
- `POST /api/outreaches`
- `PATCH /api/outreaches/{id}/status`
- `DELETE /api/outreaches/{id}`
- `DELETE /api/outreaches`
- `POST /api/malaguide/analyze`
- `POST /api/malaria/ask`

The backend calculates outreach priority when a record is saved.

## Deploy the backend to Render

1. Create a GitHub repository for the backend files, or keep the whole project in one repository.
2. Create a PostgreSQL database for the prototype.
3. Create a new Render Web Service connected to the repository.
4. Set the root directory to `backend` if the whole project is in one repository.
5. Build command:
   `pip install -r requirements.txt`
6. Start command:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add `DATABASE_URL` using the PostgreSQL connection string.
8. Add `CORS_ORIGINS` using the exact GitHub Pages origin after it is known.
   During initial testing you may use `*`, then restrict it before sharing.
9. Confirm:
   `https://YOUR-SERVICE.onrender.com/health`
   returns `{"status":"ok"}`.

## Connect the frontend

Open `frontend/index.html` and find:

`const API_BASE_URL = ...`

Replace:

`https://YOUR-RENDER-SERVICE.onrender.com`

with the actual Render service URL.

Commit the change.

## Deploy the frontend to GitHub Pages

Option A: separate frontend repository

1. Copy `frontend/index.html` and `.nojekyll` to the repository root.
2. Push to `main`.
3. GitHub → Settings → Pages.
4. Deploy from branch `main`, folder `/root`.

Option B: one repository

Move/copy the frontend files to a branch or folder configured for Pages, or use a GitHub Actions Pages workflow.

## Approval-demo test

Before Monday, test from two browsers or devices:

1. Device A saves a New Outreach.
2. Device B refreshes and sees the same record.
3. Verify Overview totals.
4. Save a High or Medium record and confirm it appears in Follow-up Tracker.
5. Change follow-up status and refresh the second device.
6. Delete one record and verify it disappears everywhere.
7. Save a temporary record and test Clear All Data.
8. Test MalaGuide field-note examples.
9. Test Malaria Q&A.
10. Open all six Education Center modules.

## Prototype note

Do not store names, phone numbers, medical record numbers, or other identifiable health information in this prototype. Use community/institution-level outreach information.
