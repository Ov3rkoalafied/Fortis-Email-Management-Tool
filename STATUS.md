# Project Status

**Last updated:** 2026-03-02
**Status:** Paused — awaiting IT admin consent

---

## What's Built

Full working implementation committed to `main`:

- **Backend** (`backend/`): Python FastAPI + `exchangelib` (EWS/OAuth2)
  - Auth: MSAL OAuth2, token cache, `@fortisstructural.com` domain check
  - EWS client: batch-fetch emails (minimal fields first, bodies only when needed)
  - Duplicate detection: body hash + sliding time window
  - Email numbering: chain assignment via conversation ID / body match / new chain
  - Undo: JSON logs for numbering (reversible) and deletions (metadata for manual restore)
- **Frontend** (`frontend/`): React + Vite + TypeScript + TanStack Table + Tailwind CSS v4
  - Auth screen, project input, per-project email table, apply buttons, status banners

---

## Blocker

**Admin consent required for `EWS.AccessAsUser.All` permission.**

Your tenant (`fortisstructural.com`) requires an IT admin to grant consent for this
Azure app permission before any user can sign in.

### What the admin needs to do (5 minutes)

1. Go to **https://portal.azure.com** → App registrations → **Email Numbering Tool**
2. Click **API permissions** in the left sidebar
3. Click **"Grant admin consent for Fortis Structural"**
4. Confirm Yes

That's it. Once done, any `@fortisstructural.com` user can sign in without further IT involvement.

**Alternative:** If the admin prefers, they can also approve via the Microsoft consent URL directly —
share this with them and have them open it while signed in as an admin:

```
https://login.microsoftonline.com/2e5f16a8-8000-492c-a0fb-73e46d3aaf77/adminconsent?client_id=f759339d-4358-445b-9276-f7f5c8513016
```

---

## Resuming the Project

Once admin consent is granted, pick up from **Step 5** of the setup:

1. Start backend: `cd backend && venv\Scripts\activate && python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open **http://localhost:5173** → click **Sign in with Microsoft**
4. Verify EWS connection: **http://localhost:8000/api/test/connection**
   - Should return `{"status": "ok", "user": "...", "sample_folders": [...]}`
5. Enter a project number and load emails

---

## Known Issues / Next Steps After Unblocking

- [ ] Verify EWS public folder access works end-to-end (first real test)
- [ ] Test duplicate detection against a real project folder
- [ ] Test email numbering / chain assignment
- [ ] Tune chain matching logic based on real data (may need iteration)
- [ ] Package as `.exe` (PyInstaller) for easy team deployment — no Python/Node needed
- [ ] Add undo UI (history view + revert button — backend already supports it)
- [ ] Progress streaming for large folders (currently shows spinner only)
