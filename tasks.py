from app import celery_app as celery, db
from models import HealthMetric
import logging

@celery.task(bind=True)
def process_health_data(self, data):
    """Celery task to process and store health metrics data"""
    try:
        # Create new health metric record
        metric = HealthMetric.create_from_dict(data)

        # Add and commit to database
        db.session.add(metric)
        db.session.commit()

        logging.info(f"Successfully processed health data for user {data['user_id']}")
        return True
    except Exception as e:
        logging.error(f"Error processing health data: {str(e)}")
        db.session.rollback()  # Rollback on error
        raise self.retry(exc=e, max_retries=3)  # Retry up to 3 times