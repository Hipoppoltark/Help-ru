web: flask db upgrade; python main.py
worker: celery -A main.client worker -l INFO -P gevent
