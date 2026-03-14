# ⚡ LuminPrompt

> Real-time AI-powered voice collaboration rooms.

## What is this?
LuminPrompt lets teams join voice rooms, speak naturally,
and have an AI assistant listen, understand who said what,
and generate streamed responses collaboratively.

## Tech Stack
- **Backend**: Django, Django REST Framework, Django Channels
- **Real-time**: WebSockets, WebRTC
- **AI**: Ollama (local LLM)
- **Queue**: Celery + Redis
- **Database**: PostgreSQL
- **Frontend**: Django Templates + TailwindCSS

## Setup

### Prerequisites
- Python 3.12+
- Docker + Docker Compose

### Installation
```bash
git clone <repo-url>
cd luminprompt
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env      # fill in your values
docker compose up -d
python manage.py migrate
python manage.py runserver
```

## Environment Variables
See `.env.example` for required variables.