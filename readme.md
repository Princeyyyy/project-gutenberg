# Project Gutenberg Bookmarked

Project Gutenberg Bookmarked is a high-performance, self-hosted web API for serving ebook catalog metadata and cached content files (EPUB, text, etc.) from [Project Gutenberg](https://www.gutenberg.org). It includes a resilient Gutenberg mirror integration, an asynchronous S3 caching layer to bypass router timeouts, and a sleek developer playground.

---

## Local Setup & Quickstart

Follow these steps to run the application locally on your machine.

### 1. Prerequisites
Ensure you have **Python 3.11+** and **PostgreSQL** running locally.

### 2. Activate Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Create a file named `gutendex/.env` using the template below:
```env
DEBUG=true
SECRET_KEY=generate_a_random_string_here
DATABASE_NAME=gutendex
DATABASE_USER=gutendex_user
DATABASE_PASSWORD=change_me
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 4. Create Database & Run Migrations
Create your database inside PostgreSQL, then run migrations:
```bash
# In PostgreSQL terminal:
# CREATE DATABASE gutendex;
# CREATE USER gutendex_user WITH PASSWORD 'change_me';
# GRANT ALL PRIVILEGES ON DATABASE gutendex TO gutendex_user;

python manage.py migrate
```

### 5. Collect Static Files
Generate the static assets for the developer portal page:
```bash
python manage.py collectstatic --noinput
```

### 6. Start the Server
Start the local Django development server:
```bash
python manage.py runserver
```

Now navigate to `http://localhost:8000/` in your browser to view the interactive developer portal and API playground!

---

## Gutenberg Catalog Import

To populate your database with Project Gutenberg ebook metadata:
```bash
python manage.py updatecatalog
```
*Note: This downloads a ~700 MB catalog dump and inserts tens of thousands of books. It can take hours depending on network/system speeds.*

---

## Heroku Production Deployment

This project is built specifically to deploy onto Heroku while satisfying strict hosting limitations (30s request timeouts and ephemeral dyno filesystems).

### 1. Initialize & Provision
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:essential-1 -a your-app-name
heroku addons:create scheduler:standard -a your-app-name
```

### 2. Set Config Vars
Set the required environment keys on Heroku:
```bash
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))") -a your-app-name
heroku config:set DEBUG=False -a your-app-name
heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com -a your-app-name

# S3 Configuration for dynamic content caching:
heroku config:set S3_BUCKET_NAME=your-bucket-name -a your-app-name
heroku config:set S3_ACCESS_KEY_ID=your-s3-key -a your-app-name
heroku config:set S3_SECRET_ACCESS_KEY=your-s3-secret -a your-app-name
```

### 3. Deploy Code
Deploy the codebase to your Heroku app:
```bash
heroku ps:type basic -a your-app-name
git push heroku main
```

### 4. Database Setup & Remote Catalog Import
Run database migrations and trigger the catalog updater inside a detached dyno:
```bash
heroku run python manage.py migrate -a your-app-name
heroku run:detached --size=standard-2x python manage.py updatecatalog -a your-app-name
```
*Tip: Track the detached import using `heroku logs --tail -a your-app-name`.*

---

## Caching Architecture (Phase 4)

Gutenberg mirrors can be slow, which triggers a `30-second router timeout (H12 error)` on Heroku web requests. Project Gutenberg Bookmarked sidesteps this using an **Asynchronous Content Caching Loop**:

1. **Client Request:** The client calls `GET /content/{gutenberg_id}/?format=epub`.
2. **Cache Hit:** If the EPUB file is cached in your S3 bucket, the server immediately issues a `302 redirect` to the S3 file download URL (taking <50ms).
3. **Cache Miss:** If not cached, the server registers a `Pending` cache job and instantly returns a `202 Accepted` response status code to the client.
4. **Worker Processing:** The background worker dyno detects the job, downloads the file from a randomized Gutenberg mirror, uploads the file to S3, and marks the status as `Ready`.
5. **Polling:** The client polls `GET /content/{gutenberg_id}/status/?format=epub` every 3-5 seconds until it receives a status of `Ready` with the S3 URL.
