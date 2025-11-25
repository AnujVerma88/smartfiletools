@echo off
cd E:\globalwhiteboard\smartfiletools
call .\myenv\Scripts\activate

start "Celery Worker" cmd /k "celery -A smartfiletools worker --loglevel=info -P solo"
start "Celery Beat" cmd /k "celery -A smartfiletools beat --loglevel=info"
start "Django Server" cmd /k "python manage.py runserver 6051"

echo All services started.
pause
