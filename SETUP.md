# Quick Setup Guide

This guide will get you up and running in less than 5 minutes.

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- **Optional:** PostgreSQL (recommended for production)

---

## Setup Options

### Option 1: Quick Start (SQLite - Development)

**Best for:** Local testing, development, quick evaluation

```bash
# 1. Clone the repository
git clone <repository-url>
cd mini-assessment-engine

# 2. Create virtual environment
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# Edit .env and set:
# DEBUG=True
# DB_ENGINE=django.db.backends.sqlite3
# GRADER_TYPE=mock

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create sample data
python manage.py create_sample_data

# 7. Run the server
python manage.py runserver
```

**Access:**
- API: http://localhost:8000/api/
- Swagger Docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

**Test Credentials:**
- Username: `student1`
- Password: `testpass123`

---

### Option 2: Production Setup (PostgreSQL)

**Best for:** Production deployment, team environments

```bash
# 1-3. Same as Option 1

# 4. Install PostgreSQL
# Download from: https://www.postgresql.org/download/

# 5. Create database
# Open PostgreSQL shell (psql):
createdb assessment_db

# Or via pgAdmin UI

# 6. Configure environment
cp .env.example .env

# Edit .env:
DEBUG=False
DB_ENGINE=django.db.backends.postgresql
DB_NAME=assessment_db
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
GRADER_TYPE=mock  # or 'gemini' if you have API key

# 7. Run migrations
python manage.py makemigrations
python manage.py migrate

# 8. Create admin user
python manage.py createsuperuser

# 9. Create sample data (optional)
python manage.py create_sample_data

# 10. Collect static files
python manage.py collectstatic --noinput

# 11. Run server
python manage.py runserver
```

---

### Option 3: With Gemini AI Grading

**Best for:** Advanced grading with AI feedback

```bash
# 1. Get Gemini API Key
# Visit: https://makersuite.google.com/app/apikey
# Click "Get API Key" → Create new key
# Copy the key

# 2. Configure .env
GRADER_TYPE=gemini
GEMINI_API_KEY=your_api_key_here

# 3. Restart server
# The system will now use AI for grading
# Falls back to mock grader if API fails
```

**Gemini Free Tier:**
- 60 requests per minute
- Perfect for moderate usage
- Automatic fallback to algorithmic grading

---

## Testing the Setup

### 1. Check API is running
```bash
curl http://localhost:8000/api/exams/
# Should return 401 (needs authentication) ✓
```

### 2. Register a test user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 3. Run automated tests
```bash
python manage.py test
```

Expected output:
```
Found 7 test(s).
...
Ran 7 tests in X.XXXs

OK
```

---

## Accessing Swagger Documentation

Once the server is running, visit:

**http://localhost:8000/api/docs/**

You'll see:
- ✅ Interactive API documentation
- ✅ All endpoints with examples
- ✅ Try-it-out functionality
- ✅ Schema downloads

---

## Common Issues & Solutions

### Issue: `SECRET_KEY not found`
**Solution:** Make sure you copied `.env.example` to `.env`

### Issue: `psycopg2` installation fails
**Solution:** 
```bash
# Use binary version instead:
pip install psycopg2-binary
```

### Issue: PostgreSQL connection refused
**Solution:**
1. Check PostgreSQL is running: `pg_ctl status`
2. Verify credentials in `.env`
3. Check firewall isn't blocking port 5432

### Issue: Migrations fail
**Solution:**
```bash
# Delete migrations and start fresh:
rm -rf apps/assessments/migrations
python manage.py makemigrations assessments
python manage.py migrate
```

### Issue: Tests fail with UUID errors
**Solution:**
```bash
# Recreate the database:
python manage.py flush --noinput
python manage.py migrate
python manage.py create_sample_data
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ Yes | - | Django secret key |
| `DEBUG` | No | `False` | Enable debug mode |
| `DB_ENGINE` | No | `sqlite3` | Database backend |
| `DB_NAME` | No | `db.sqlite3` | Database name |
| `DB_USER` | No | `postgres` | Database user |
| `DB_PASSWORD` | No | - | Database password |
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |
| `GRADER_TYPE` | No | `mock` | Grading strategy |
| `GEMINI_API_KEY` | No | - | Google Gemini API key |

---

## Next Steps

1. **Explore the API:** Visit http://localhost:8000/api/docs/
2. **Test endpoints:** Use Swagger UI or Postman
3. **Review code:** Check out the models, views, and grading service
4. **Run tests:** `python manage.py test`
5. **Check query optimization:** Enable SQL logging in `.env`

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate new `SECRET_KEY`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set up proper `ALLOWED_HOSTS`
- [ ] Configure HTTPS/SSL
- [ ] Set up proper logging
- [ ] Run `collectstatic`
- [ ] Set up backup strategy
- [ ] Configure monitoring

---

## Support

If you encounter any issues:

1. Check the logs: `logs/django.log`
2. Enable debug mode: `DEBUG=True`
3. Run tests: `python manage.py test`
4. Check database connection
5. Verify environment variables

---

**What's next after you're done with the above steps??**

Click the link => http://localhost:8000/api/docs/ to checkout the Swagger docs so you can explore the API more interactively.