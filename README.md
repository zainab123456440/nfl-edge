# NFL EDGE

A data-driven NFL analytics platform for exploring games, player props, odds, injuries, and personalized betting research.

NFL EDGE combines live sports data, a secure user system, player-prop analysis, and an upcoming AI assistant into one centralized platform.

---

## Overview

NFL EDGE is designed as a centralized workspace for NFL research and analysis.

The platform currently provides:

* Secure user authentication
* Protected application routes
* Live NFL game data
* Player prop markets
* Prop history and line movement
* Saved props
* User-specific alerts
* Lineup CSV uploads
* Supabase-backed data storage
* A dashboard foundation for the AI assistant

The next major development phase is the **AI Assistant**, which will connect the application database, uploaded files, and application tools into a single conversational interface.

---

## Core Features

### Authentication

NFL EDGE uses Supabase authentication with a FastAPI backend.

Implemented functionality includes:

* User registration
* User login
* Session restoration
* Token refresh
* Logout
* Password reset
* Protected application routes
* Authenticated API requests

Authentication is handled through the backend rather than trusting user-supplied IDs.

---

### Games

The Games page provides access to NFL game information retrieved from the application's backend data sources.

Features include:

* Upcoming and scheduled games
* Team information
* Game details
* Game filtering
* Game statistics
* Backend-connected live data

---

### Player Props

The Props page provides a centralized view of available player prop markets.

Supported areas include:

* Passing
* Rushing
* Receiving
* Touchdowns
* Kicking
* Prop lines
* Sportsbook/bookmaker information
* Prop history
* Historical line movement

The interface is designed to make player-prop research easier without requiring users to manually inspect multiple data sources.

---

### Saved Props

Authenticated users can save props for later analysis.

Saved props are isolated by authenticated user, meaning one user cannot access another user's saved selections.

---

### Alerts

Users can create and manage personalized prop alerts.

Alerts are tied to the authenticated account and are isolated between users.

---

### Lineup File Uploads

NFL EDGE supports authenticated CSV lineup uploads.

Uploaded files are stored using user-specific storage paths so that files belonging to one account are separated from another account.

The current lineup pipeline provides the foundation for future lineup generation and optimization workflows.

---

## Data Architecture

NFL EDGE uses a FastAPI backend with Supabase as the primary data and authentication platform.

### Main Data Areas

The database contains shared NFL data such as:

* Games
* Teams
* Players
* Injuries
* Odds
* Opening odds
* Odds snapshots
* Player statistics
* Prop markets
* Current props
* Prop history
* Bookmakers

User-specific data includes:

* Saved props
* Alerts
* Uploaded files
* Future AI conversations
* Future generated lineups
* Future user preferences

Shared NFL data can be accessed by authenticated users, while private data is scoped to the authenticated account.

---

## Security

Security is a core part of the application architecture.

### User Isolation

The backend derives the authenticated user ID from the authentication token.

The application does **not** trust a `user_id` supplied by the frontend when performing user-specific operations.

For example:

```text
Browser
   ↓
Authentication Token
   ↓
FastAPI Authentication Dependency
   ↓
Authenticated User ID
   ↓
User-Scoped Database Query
```

This prevents users from simply changing a user ID in a request and accessing another user's data.

### Supabase RLS

Supabase Row Level Security is also used as an additional layer of protection for private tables.

The application therefore uses multiple layers of protection:

1. Frontend authentication checks
2. Backend authentication
3. Backend user-scoped queries
4. Supabase Row Level Security

---

## Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* SWR
* CSS / responsive UI

### Backend

* Python
* FastAPI
* Pydantic
* REST APIs

### Database & Authentication

* Supabase
* PostgreSQL
* Supabase Auth
* Supabase Storage
* Row Level Security

### Data Sources

The platform integrates sports data providers for NFL:

* Games
* Players
* Injuries
* Odds
* Player props
* Historical statistics

---

## Project Structure

```text
NFL-EDGE/
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── games/
│   │   ├── props/
│   │   ├── login/
│   │   ├── signup/
│   │   ├── forgot-password/
│   │   ├── reset-password/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── components/
│   ├── Hooks/
│   ├── lib/
│   ├── services/
│   └── types/
│
├── backend/
│   ├── dependencies/
│   ├── routes/
│   ├── services/
│   ├── schemas/
│   ├── db.py
│   ├── config.py
│   └── main.py
│
└── README.md
```

---

## Application Routes

### Public Routes

```text
/login
/signup
/forgot-password
/reset-password
```

### Protected Routes

```text
/dashboard
/games
/props
```

The root URL:

```text
/
```

redirects users to:

```text
/login
```

---

## Backend API

The FastAPI backend provides endpoints for authentication, games, props, saved props, alerts, lineups, and other application services.

Example API areas:

```text
/api/auth/*
/games/*
/props/*
/lineups/*
```

The exact API routes may evolve as additional application functionality is added.

---

## Environment Variables

Create environment files for the frontend and backend rather than committing secrets to GitHub.

Typical frontend configuration:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Typical backend configuration includes:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

ODDS_API_KEY=...
BALLDONTLIE_API_KEY=...
```

Never commit API keys, service-role keys, passwords, or other secrets to the repository.

---

## Local Development

### 1. Clone the repository

```bash
git clone <repository-url>
cd NFL-EDGE
```

### 2. Start the Backend

```bash
cd backend
uvicorn main:app --reload
```

The backend will normally be available at:

```text
http://localhost:8000
```

### 3. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:3000
```

Open:

```text
http://localhost:3000
```

The application will begin at the login screen.

---

## Development Flow

The project is being developed in several major phases.

### Phase 1 — Data Foundation

* NFL games
* Teams
* Players
* Injuries
* Odds
* Player props
* Historical data

### Phase 2 — Application

* Authentication
* Dashboard
* Games
* Player Props
* Saved Props
* Alerts
* User isolation

### Phase 3 — AI Assistant

The AI Assistant is the next major development phase.

The planned assistant will be able to:

* Answer general NFL questions
* Query application data
* Search Supabase tables
* Analyze player and game data
* Use application tools
* Analyze uploaded files
* Read CSV, TXT, JSON, XLS, XLSX and other supported formats
* Combine database information with uploaded files
* Generate structured outputs
* Generate lineup CSV files
* Maintain user-specific conversations
* Respect user-level data isolation

The goal is to make the assistant a **database-aware application agent**, rather than simply a basic chatbot.

---

## AI Assistant Architecture

The planned architecture will follow a tool-based approach:

```text
                    ┌──────────────────┐
                    │   AI Assistant   │
                    └────────┬─────────┘
                             │
             ┌───────────────┼───────────────┐
             ↓               ↓               ↓
       Database Tools    File Tools      NFL Tools
             │               │               │
             ↓               ↓               ↓
        Supabase DB      File Storage    Sports APIs
             │               │               │
             └───────────────┼───────────────┘
                             ↓
                     Structured Answer
```

The assistant will only access private resources belonging to the authenticated user.

---

## User Data Model

NFL EDGE separates shared sports data from private user data.

### Shared

```text
games
teams
players
injuries
odds
player statistics
props
bookmakers
```

### User-specific

```text
saved_props
alerts
uploaded_files
ai_conversations
ai_messages
generated_lineups
user_settings
```

This separation allows the platform to provide common NFL information while maintaining account-level privacy.

---

## Future Development

Planned improvements include:

* AI-powered database querying
* Natural-language data exploration
* File-aware AI analysis
* Automated lineup generation
* DraftKings salary-file processing
* Injury-aware lineup generation
* Prop hit-rate analysis
* Advanced historical analysis
* Line movement analysis
* AI-assisted research
* User-specific AI conversation history
* Automated reports and exports

---

## Project Status

### Completed

* Authentication
* Signup/login flow
* Password reset
* Protected routes
* User authentication dependency
* User-scoped backend operations
* Games page
* Player Props page
* Saved props
* Alerts
* Lineup CSV upload
* Supabase integration
* User data isolation
* Root login redirect

### In Development

* AI Assistant
* Database tool calling
* File analysis pipeline
* AI conversation storage
* Automated lineup generation
* Advanced analytics workflows

---

## Security Principles

NFL EDGE follows these principles:

* Never trust client-provided user IDs
* Authenticate users on protected backend endpoints
* Scope private queries to the authenticated user
* Keep shared and private data separate
* Use Supabase RLS for defense in depth
* Keep secrets in environment variables
* Validate uploaded files
* Restrict access to user-owned files and generated resources

---

## License

This project is currently maintained as a private application project.

License and distribution terms can be added when the project is prepared for public release.
