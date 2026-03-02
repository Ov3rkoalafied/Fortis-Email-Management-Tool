# Fortis Email Management Tool

Outlook public folder email management — duplicate detection and email numbering.

## Stack

- **Backend**: Python + FastAPI + `exchangelib` (EWS/OAuth2)
- **Frontend**: React + Vite + TypeScript + TanStack Table + Tailwind CSS

## Prerequisites

### 1. Azure App Registration (one-time setup)

Your existing Azure app (`f759339d-...`) needs the following:

1. **Azure Portal → App registrations → your app → API permissions**
   - Add permission → APIs my organization uses → **Office 365 Exchange Online**
   - Select **Delegated** → check `EWS.AccessAsUser.All`
   - Click **Grant admin consent**

2. **Authentication tab**
   - Under "Advanced settings" → **Allow public client flows** → toggle **Yes**
   - Ensure redirect URI `http://localhost:8400` is listed under
     **Mobile and desktop applications** (not Web)

### 2. Python environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Node

```bash
cd frontend
npm install
```

## Running

**Terminal 1 — backend:**
```bash
cd backend
venv\Scripts\activate
python run.py
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173**

On first launch, click **Sign in with Microsoft** — a browser window will open for OAuth2 login. Only `@fortisstructural.com` accounts are accepted.

## Features

- **Duplicate detection**: groups emails by normalized body hash within a configurable time window, lets you review before deleting
- **Email numbering**: assigns `NNNN[letter] - ABBR - Title` subjects, chains emails by conversation ID / body similarity
- **Per-row overrides**: override proposed subject or project abbreviation per email before applying
- **Undo**: all changes logged to `~/.fortis_email_tool/undo/` — numbering changes are fully reversible; deletions log metadata for manual Deleted Items restore
- **Fast**: only fetches bodies for emails that actually need them (potential duplicates + unnumbered), not all emails

## Numbering format

```
NNNN        - PROJECT ABBR - Email Title      ← first in chain
NNNNa       - PROJECT ABBR - Email Title      ← second
NNNNb       - PROJECT ABBR - Email Title      ← third
NNNN+1      - PROJECT ABBR - Different Topic  ← new chain
```

## Project folder convention

Public Folders → All Public Folders → `XXXXX Project Name`
where `XXXXX` is a 5-digit project number (e.g. `19035`).
