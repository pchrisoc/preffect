from extensions import db

class HealthMetric(db.Model):
    __tablename__ = 'health_metrics'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    heart_rate = db.Column(db.Integer, nullable=False)
    steps = db.Column(db.Integer, nullable=False)
    calories = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<HealthMetric user_id={self.user_id} timestamp={self.timestamp}>'

    @classmethod
    def create_from_dict(cls, data):
        from datetime import datetime
        return cls(
            user_id=data['user_id'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            heart_rate=data['heart_rate'],
            steps=data['steps'],
            calories=data['calories']
        )
