# Health Metrics API

This API ingests health metrics data, stores them in a PostgreSQL database, and provides endpoints for querying aggregated results.

## Prerequisites

- Python (3.8+)
- PostgreSQL database
- Redis (used as the Celery broker/worker)
- [jq](https://stedolan.github.io/jq/) (for command-line JSON processing)
- Virtual Environment (recommended)

## Setup

1. **Install Dependencies:**

   Activate your virtual environment and install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables:**

   Create a `.env` file in the project root with the following content (adjust as needed):

   ```properties
   DATABASE_URL="postgres://avnadmin:AVNS_DZjYXtCx2IeiLWZw7b7@postgresql-preffect.g.aivencloud.com:10366/defaultdb?sslmode=require"
   SESSION_SECRET="dev_secret_key"
   ```

3. **Database Setup:**

   The linked PostgreSQL database should already be running via Aiven.

## Redis Installation and Startup

Redis is required for Celery. You can install and start Redis using Homebrew:

```bash
brew update && brew install redis
brew services start redis
```

If you prefer to run Redis manually:

```bash
redis-server --daemonize yes
```

## Running the Application

### Development Server

Start the application using Flask's development server:

```bash
python main.py
```

### Production Server

You can also run the application with Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5001 --reload main:app
```

## Celery Worker

To process data asynchronously, run the Celery worker with the tasks module. In a separate terminal, execute:

```bash
celery -A tasks worker --loglevel=info
```

Make sure that your Redis broker is running before starting the worker.

## Submitting Data
## Viewing Data and Sending Metrics Requests

After starting the application, open your browser and navigate to [http://127.0.0.1:5001/](http://127.0.0.1:5001/). On this page you will:

- Scroll to see a dynamically generated table displaying all the current health metrics data stored in PostgreSQL (should be empty at first). Follow the steps below and refresh to see changes.
- Below is an example output of a metrics querie. Enter the user ID and the desired start and end timestamps, then submit the request to view aggregated metrics results (pressing the button executes the following).

```bash
curl "http://0.0.0.0:5001/metrics?user_id=123&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z"
```

This UI provides an interactive way to test both data viewing and metric querying.
### Individual Data Submission

You can test data ingestion using `curl`. For example:

```bash
curl -X POST http://0.0.0.0:5001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 101,
    "timestamp": "2025-01-01T09:30:00Z",
    "heart_rate": 78,
    "steps": 150,
    "calories": 6.5
}'
```

### Batch Data Submission via Command Line

A sample file `sample_posts.json` is provided in the project root. You can submit all entries from that file using your shell:

#### **Using Bash:**

```bash
for sample in $(jq -c '.[]' sample_posts.json); do
  curl -X POST http://0.0.0.0:5001/ingest \
    -H "Content-Type: application/json" \
    -d "$sample"
  echo
done
```

#### **Using Fish Shell:**

```fish
for sample in (jq -c '.[]' sample_posts.json)
    curl -X POST http://0.0.0.0:5001/ingest \
      -H "Content-Type: application/json" \
      -d $sample
end
```

## Endpoints

- **GET /**  
  Renders the API documentation page.

- **POST /ingest**  
  Ingests health metrics data.  
  *Example Request Body:*
  ```json
  {
    "user_id": 101,
    "timestamp": "2025-01-01T09:30:00Z",
    "heart_rate": 78,
    "steps": 150,
    "calories": 6.5
  }
  ```

- **GET /metrics**  
  Returns aggregated metrics for a specified user between provided timestamps.  
  *Query Parameters:*  
  - `user_id`  
  - `start` (ISO timestamp)  
  - `end` (ISO timestamp)  

  *Example Query:*  
  ```
  /metrics?user_id=123&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z
  ```

- **GET /data**  
  Returns all health metric records stored in PostgreSQL.

## Frontend Testing

The `index.html` file (located in `/templates`) provides a UI to:
- Submit individual and batch data.
- Display the resulting PostgreSQL data in a table.
- Send sample metrics queries.

## Troubleshooting

- **Ensure the JSON file is accessible:**  
  If `sample_posts.json` isn’t served from the root, consider moving it to the `/static` folder and update the fetch URL in the frontend accordingly.

- **Check shell compatibility:**  
  Use the appropriate shell commands for Bash or Fish when running batch submission scripts.

- **Celery Task Issue:**  
  If you see errors related to importing `celery` in `tasks.py`, ensure that you're importing `celery_app` as shown in the file:
  ```python
  from app import celery_app as celery, db
  ```

## Design Explanation

This solution leverages a Flask backend for a lightweight API that ingests health metrics through an `/ingest` endpoint, processes data asynchronously using Celery (with Redis as the message broker), and stores the data in a PostgreSQL database. The database schema is defined using SQLAlchemy, with a `health_metrics` table structured to capture user ID, timestamp, heart rate, steps, and calories. Indexes are optionally created on the `user_id` and `timestamp` fields to optimize query performance.

The design emphasizes scalability and asynchronous processing, allowing data ingestion to be decoupled from the API response. This means incoming data is quickly queued for background processing, enhancing responsiveness. Additionally, the UI provided via `index.html` offers a simple way for users to view real-time data and perform metric aggregation queries, illustrating the end-to-end flow from data ingestion to analytical output.
