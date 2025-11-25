# SmartFileTools (Minimal Scaffold)
This archive contains a minimal Django scaffold for the **SmartFileTools** project.
It includes:
- basic Django project settings
- `accounts` and `tools` apps with minimal models and URLs
- Celery configuration file
- a sample PDF -> DOCX utility using `pdf2docx` (stub)

Important:
- This is a scaffold to get started. You must create a virtualenv and install dependencies from `requirements.txt`.
- Update `smartfiletools/settings.py` SECRET_KEY and other settings before running.

To run locally:
1. python -m venv venv
2. source venv/bin/activate  (or venv\Scripts\activate on Windows)
3. pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py createsuperuser
6. python manage.py runserver

Celery (example):
celery -A smartfiletools worker -l info

Downloaded zip path: /mnt/data/smartfiletools.zip
