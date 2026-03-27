# ⚡ LuminPrompt

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![WebSockets](https://img.shields.io/badge/WebSockets-0082C9?style=for-the-badge&logo=websocket&logoColor=white)

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
