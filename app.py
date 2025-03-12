import os
from dotenv import load_dotenv  # load environment variables from .env
load_dotenv()

from flask import Flask, request, jsonify, render_template
from datetime import datetime
from celery import Celery
import logging

from extensions import db  # import shared db instance

logging.basicConfig(level=logging.DEBUG)

# Expose celery_app at module level
celery_app = None

def create_app():
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False  # preserve insertion order in JSON responses

    # Configure Flask app
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

    # Use the DATABASE_URL provided by .env
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Initialize database with current app context
    db.init_app(app)

    # Configure Celery with Redis running locally and expose it as `celery_app`
    global celery_app
    celery_app = Celery(
        app.name,
        broker='redis://127.0.0.1:6379/0',
        backend='redis://127.0.0.1:6379/0'
    )
    celery_app.conf.update(app.config)

    # Import models and create Celery task context
    from models import HealthMetric

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery_app.Task = ContextTask

    @app.route('/')
    def index():
        """Render API documentation page"""
        return render_template('index.html')

    @app.route('/ingest', methods=['POST'])
    def ingest_data():
        """Endpoint to receive health metrics data"""
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = ['user_id', 'timestamp', 'heart_rate', 'steps', 'calories']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            # Process data asynchronously if possible
            try:
                from tasks import process_health_data
                process_health_data.delay(data)
                return jsonify({'message': 'Data received and queued for processing'}), 202
            except Exception as e:
                logging.warning(f"Celery task queueing failed, processing directly: {str(e)}")
                metric = HealthMetric.create_from_dict(data)
                db.session.add(metric)
                db.session.commit()
                return jsonify({'message': 'Data processed successfully'}), 201

        except Exception as e:
            logging.error(f"Error processing request: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/metrics', methods=['GET'])
    def get_metrics():
        """Endpoint to retrieve aggregated metrics"""
        try:
            user_id = request.args.get('user_id')
            start_time = request.args.get('start')
            end_time = request.args.get('end')

            missing_params = []
            if not user_id:
                missing_params.append('user_id')
            if not start_time:
                missing_params.append('start')
            if not end_time:
                missing_params.append('end')
            if missing_params:
                return jsonify({
                    'error': f"Missing required parameters: {', '.join(missing_params)}",
                    'example_usage': '/metrics?user_id=123&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z'
                }), 400

            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400

            metrics = HealthMetric.query.filter(
                HealthMetric.user_id == user_id,
                HealthMetric.timestamp.between(start_dt, end_dt)
            ).all()

            if not metrics:
                response = {
                    "user_id": user_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "metrics": {
                        "average_heart_rate": 0,
                        "total_steps": 0,
                        "total_calories": 0
                    }
                }
            else:
                total_heart_rate = sum(m.heart_rate for m in metrics)
                total_steps = sum(m.steps for m in metrics)
                total_calories = sum(m.calories for m in metrics)
                avg_heart_rate = total_heart_rate / len(metrics)
                response = {
                    "user_id": user_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "metrics": {
                        "average_heart_rate": avg_heart_rate,
                        "total_steps": total_steps,
                        "total_calories": total_calories
                    }
                }

            return jsonify(response)

        except Exception as e:
            logging.error(f"Error retrieving metrics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/data', methods=['GET'])
    def get_data():
        """Return all health metric records from PostgreSQL using the remote DB_URL"""
        from models import HealthMetric
        records = HealthMetric.query.all()
        app.logger.info(f"Retrieved {len(records)} records from the database")
        data = []
        for record in records:
            data.append({
                "id": record.id,
                "user_id": record.user_id,
                "timestamp": record.timestamp.isoformat(),
                "heart_rate": record.heart_rate,
                "steps": record.steps,
                "calories": record.calories
            })
        return jsonify(data)

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001)

if __name__ != "__main__":
    # For gunicorn or Celery worker: create and initialize the app
    app = create_app()
    with app.app_context():
        db.create_all()