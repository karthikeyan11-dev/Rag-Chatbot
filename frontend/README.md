# RAG Chatbot — Frontend

React + Vite frontend for the company policy chatbot.

## Tech Stack

- **React 18** — UI library
- **Vite** — fast development server and bundler
- **TailwindCSS** — utility-first styling
- **Livvic** — Google Font for clean, modern typography

## Setup & Run

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

The Vite dev server proxies all `/api` requests to `http://localhost:8000`, so make sure the backend is running.

## Features

- Clean white/blue chat UI
- Welcome screen with quick-start suggestions
- Auto-scrolling conversation thread
- Source document badges shown per assistant answer
- Typing/loading indicator with animated dots
- Enter key to submit, Shift+Enter for newline
- Send button disabled while loading
- Error banner with dismiss
- Clear chat button
- Fully responsive layout
