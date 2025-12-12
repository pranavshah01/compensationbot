# Compensation Recommendation Assistant - Frontend

Next.js frontend for the Compensation Recommendation Conversational Assistant.

## Features

- 🔐 Authentication with login page
- 💬 Real-time chat interface with SSE streaming
- 👍 Feedback system (thumbs down / report error)
- 📋 Context management panel
- 🎨 Modern UI with Tailwind CSS
- 📱 Responsive design

## Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment** (optional):
   Create `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Login page
│   ├── chat/              # Chat page
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── LoginPage.tsx      # Login component
│   ├── ChatInterface.tsx  # Main chat interface
│   └── ContextPanel.tsx   # Context management
├── lib/                   # Utilities
│   ├── store.ts          # Zustand auth store
│   └── api.ts            # API client
└── package.json          # Dependencies
```

## Features Details

### Authentication
- Login page with email/password
- JWT token stored in localStorage
- Protected routes
- Auto-redirect based on auth status

### Chat Interface
- Real-time streaming responses via SSE
- Message history
- Loading states
- Error handling
- Candidate ID management

### Feedback System
- Thumbs down button for quick feedback
- Report error with optional comment
- Feedback linked to response IDs

### Context Management
- View candidate context
- Reset context (Comp Team only)
- Audit log viewing
- Candidate ID input

## API Integration

The frontend communicates with the FastAPI backend at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

Endpoints used:
- `POST /api/login` - Authentication
- `POST /api/chat/stream` - SSE chat streaming
- `GET /api/context/{candidate_id}` - Get context
- `POST /api/context/reset` - Reset context
- `GET /api/audit/{candidate_id}` - Get audit log
- `POST /api/feedback` - Submit feedback

## Build

```bash
npm run build
npm start
```

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - HTTP client




