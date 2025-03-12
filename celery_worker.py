from app import celery, app
import logging

logging.basicConfig(level=logging.DEBUG)

# This ensures the task runs in the application context
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    pass

if __name__ == '__main__':
    with app.app_context():
        celery.worker_main(['worker', '--loglevel=info'])