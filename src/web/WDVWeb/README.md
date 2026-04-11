# AquaSmart Web Dashboard (WDVWeb)

A real-time web dashboard for AquaSmart water dispenser kiosk users to view their credit balance.

## Architecture

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  RPi Kiosk   │──────▶│  Firebase RTDB   │◀──────│  Next.js Web     │
│  (Python)    │ write │  /users/{username}│ read  │  (this project)  │
│              │       │                  │ live   │                  │
│ storage.py + │       │  {               │       │  AuthContext →   │
│ firebase_sync│       │    username,     │       │  onValue()       │
│              │       │    email,        │       │  listener        │
│              │       │    phone,        │       │                  │
│              │       │    points,       │       │  Dashboard shows │
│              │       │    is_guest      │       │  credit balance  │
│              │       │  }               │       │                  │
└──────────────┘       └──────────────────┘       └──────────────────┘
                              │
                       Firebase Auth
                       (email + password
                        for web login)
```

### RTDB Schema

Exactly mirrors the RPi `User.to_dict()` output, minus `password`:

```
/users/{username}
  ├── username  : string   (e.g. "sajedhm")
  ├── email     : string   (e.g. "sajedhm@gmail.com")
  ├── phone     : string   (e.g. "09634905586")
  ├── points    : number   (e.g. 19)
  └── is_guest  : boolean  (false for registered users)
```

### How Web Login Links to Kiosk Account

1. User registers at the **kiosk** (pays ₱10 activation fee, gets welcome bonus)
2. RPi calls `firebase_sync.sync_user(user.to_dict())` → pushes profile to RTDB
3. User creates a **web account** at `/register` using the **same email** from their kiosk registration
4. Web login: Firebase Auth authenticates email + password
5. `AuthContext` queries RTDB: `orderByChild("email").equalTo(authenticated_email)`
6. Real-time listener on `/users/{username}` displays live credit balance

## Setup

### 1. Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project (or use existing)
3. Enable **Authentication** → **Email/Password** provider
4. Enable **Realtime Database** → Start in **test mode** (you'll configure rules below)

### 2. Firebase RTDB Rules

Set these rules to allow authenticated users to read only their own data, while the RPi (or admin) can write:

```json
{
  "rules": {
    "users": {
      ".indexOn": ["email"],
      "$username": {
        ".read": "auth != null",
        ".write": "auth != null && auth.token.admin === true"
      }
    }
  }
}
```

> **Quick start (development only):** Use test-mode rules `{ ".read": true, ".write": true }` and tighten before deployment.

### 3. Environment Variables

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your Firebase project credentials from:
**Firebase Console → Project Settings → General → Your Apps → Web App**

### 4. Install & Run

```bash
cd src/web/WDVWeb
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 5. RPi Companion Setup

On the Raspberry Pi, install pyrebase4:

```bash
pip install pyrebase4
```

Edit `src/rpi/WDVHost/firebase_sync.py` and fill in `FIREBASE_CONFIG` with the **same** Firebase credentials.

Then after any `storage.save_user()` call, also call:

```python
from firebase_sync import sync_user
sync_user(user.to_dict())
```

Or do a one-time bulk sync:

```python
from firebase_sync import sync_all_users
count = sync_all_users()
print(f"Synced {count} users to Firebase")
```

## Deploy to Vercel

### Option A: Vercel CLI

```bash
npm i -g vercel
cd src/web/WDVWeb
vercel
```

When prompted, set environment variables for all `NEXT_PUBLIC_FIREBASE_*` values.

### Option B: Vercel Dashboard

1. Push your repo to GitHub
2. Go to [vercel.com/new](https://vercel.com/new) and import the repo
3. Set **Root Directory** to `src/web/WDVWeb`
4. Add all `NEXT_PUBLIC_FIREBASE_*` environment variables in Vercel project settings
5. Deploy

## RPi Alignment

| Aspect | RPi (existing) | Web (this project) |
|--------|---------------|-------------------|
| User key | `accounts/{username}.json` | `/users/{username}` |
| Fields | username, email, phone, password, points, is_guest | Same minus password |
| Auth | Username + plaintext password | Firebase Auth (email + password) |
| Credit update | `AppState.add_cash()` → `storage.save_user()` | Read-only via `onValue()` |
| Sync direction | RPi → Firebase RTDB | RTDB → Web (real-time) |

The web dashboard is **read-only** — it displays credit but never modifies it. All credit changes originate from the kiosk (coin/bill insertion, dispensing).

## Project Structure

```
src/web/WDVWeb/
├── .env.local.example      # Firebase config template
├── .gitignore
├── next.config.ts
├── package.json
├── postcss.config.mjs
├── tailwind.config.ts       # Custom colors matching RPi theme.py
├── tsconfig.json
└── src/
    ├── app/
    │   ├── globals.css       # Base styles
    │   ├── layout.tsx        # Root layout with AuthProvider
    │   ├── page.tsx          # Auto-redirect to /login or /dashboard
    │   ├── login/
    │   │   └── page.tsx      # Email + password login
    │   ├── register/
    │   │   └── page.tsx      # Web account creation
    │   └── dashboard/
    │       └── page.tsx      # Credit balance + account info
    ├── context/
    │   └── AuthContext.tsx    # Firebase Auth + RTDB real-time bindings
    └── lib/
        └── firebase.ts       # Firebase SDK initialization
```
