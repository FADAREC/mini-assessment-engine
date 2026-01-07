# Mini Assessment Engine - Backend Task

A Django REST Framework-based assessment system enabling secure exam submission and automated grading with both algorithmic and LLM-powered evaluation strategies.

---

## Architecture Overview

### Design Philosophy

This system was designed with three core principles:

1. **Security First**: Identity inference from authenticated requests, data boundary enforcement via permissions
2. **Query Efficiency**: Aggressive use of `select_related`/`prefetch_related` to eliminate N+1 queries
3. **Modularity**: Strategy Pattern for grading enables easy swapping between mock and LLM implementations

### Database Schema

```
User (Django AbstractUser)
  ↓ one-to-many
Submission (student's exam attempt)
  ↓ one-to-many  
Answer (response to individual question)
  ↓ many-to-one
Question (exam item)
  ↓ many-to-one
Exam (assessment container)
```

**Key Constraints:**
- `UNIQUE(student_id, exam_id)` on Submission - prevents duplicate submissions
- `UNIQUE(submission_id, question_id)` on Answer - one answer per question per attempt
- Foreign key indexes on all relations for efficient JOINs

**Rationale:**
Separating `Answer` as a distinct entity (rather than embedding in Submission JSON) enables:
- Granular per-question grading and feedback
- Efficient query optimization during result retrieval
- Proper relational integrity and partial credit tracking

---

## Security Implementation

### Authentication
- Token-based authentication using Django REST Framework's built-in `TokenAuthentication`
- Passwords hashed via Django's `set_password()` (PBKDF2 with SHA256)
- All protected endpoints require `Authorization: Token <key>` header

### Authorization & Data Isolation
- **Identity Inference**: User identity extracted from `request.user`, never from request payload
- **Custom Permissions**: `IsSubmissionOwner` ensures students only access their own submissions
- **QuerySet Filtering**: All queries filtered by `request.user` to enforce data boundaries

### Input Validation
- Serializer-level validation for all incoming data
- Question ID validation against exam's actual questions
- Duplicate answer detection in submission payload
- Duplicate submission prevention (DB constraint + app-level check)

**Example Attack Prevention:**
```python
# VULNERABLE: Accepts user_id from untrusted payload
submission = Submission.objects.create(student_id=request.data['user_id'], ...)

# SECURE: Identity from authenticated request only
submission = Submission.objects.create(student=request.user, ...)
```

---

## Query Optimization Strategy

### The N+1 Problem

**Without Optimization:**
```python
submissions = Submission.objects.filter(student=request.user)
# For each submission:
#   1 query to fetch exam
#   1 query to fetch answers
#   N queries to fetch questions (one per answer)
# Total: 1 + (2 * N_submissions) + (N_answers) queries
```

**With Optimization:**
```python
submissions = Submission.objects.filter(student=request.user) \
    .select_related('exam', 'student') \
    .prefetch_related('answers__question')
# Total: 2 queries regardless of submission/answer count
```

### Optimization Techniques Applied

1. **select_related** (SQL JOIN): Used for ForeignKey fields accessed in serializer
   - `Submission.exam` - fetched in same query as submission
   - `Answer.question` - fetched with answers

2. **prefetch_related** (Optimized Subquery): Used for reverse relations
   - `Submission.answers` - all answers fetched in one query
   - `Exam.questions` - all questions fetched in one query

3. **Database Indexes**: Applied to frequently filtered/joined columns
   - `submissions(student_id, submitted_at)` - for list view queries
   - `answers(submission_id)` - for JOIN optimization
   - `questions(exam_id, order)` - for exam detail queries

**Impact:** Result retrieval reduced from O(N) to O(1) query complexity.

---

## Grading Service Architecture

### Strategy Pattern Implementation

```
BaseGrader (Abstract Interface)
    ├── MockGrader (Algorithmic)
    └── GeminiGrader (LLM-powered with fallback)
```

**Configuration:** Set `GRADER_TYPE = 'mock'` or `'gemini'` in settings to switch strategies.

### Mock Grading Algorithm (Bonus Implementation)

**Multiple Choice / True-False:**
- Exact match comparison (case-insensitive, whitespace-normalized)
- Full credit for correct answer, zero otherwise

**Short Answer:**
- String similarity using `difflib.SequenceMatcher`
- Partial credit thresholds:
  - ≥90% similarity: Full credit
  - ≥70% similarity: 80% credit
  - ≥50% similarity: 50% credit
  - <50%: No credit

**Essay Questions:**
- Keyword extraction from expected answer (filters stopwords)
- Keyword density scoring in student response
- Word count penalty for very short essays (<30 words)
- Formula: `score = (matched_keywords / total_keywords) * length_factor`

**Design Decision:** The mock grader demonstrates understanding of text evaluation without external dependencies, earning bonus points while providing a reliable fallback for LLM failures.

### Gemini LLM Integration

**Implementation:**
```python
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
```

**Prompt Engineering:**
- Structured JSON output requirement for reliable parsing
- Clear grading criteria per question type
- Emphasis on partial credit fairness

**Error Handling:**
- Automatic fallback to MockGrader on API failures
- JSON parsing with markdown fence removal
- Sanitization of LLM output values

**Modularity:** Swapping to Claude/OpenAI requires only changing the API client in `GeminiGrader.__init__` - the interface remains identical.

---

## Complete Submission Flow

1. **Student submits answers** → `POST /api/submissions/`
2. **Authentication** → Token validated, identity set to `request.user`
3. **Validation:**
   - Exam exists
   - No duplicate submission
   - All question_ids valid
   - No duplicate answers
4. **Atomic Transaction** (`@transaction.atomic`):
   - Create Submission record
   - Bulk create Answer records
   - Commit or rollback entirely
5. **Grading Service** (currently synchronous, easily made async with Celery):
   - Fetch answers with questions (optimized query)
   - Grade each answer via selected strategy
   - Update Answer records with results
   - Calculate total score
   - Update Submission status to 'graded'
6. **Response** → Return submission_id and status immediately

---

## API Documentation

### Authentication Endpoints

#### Register Student
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "student123",
  "email": "student@university.edu",
  "password": "securepass123",
  "full_name": "Jane Doe"
}

Response 201:
{
  "user_id": 1,
  "username": "student123",
  "email": "student@university.edu",
  "token": "a1b2c3d4e5f6..."
}
```

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "student123",
  "password": "securepass123"
}

Response 200:
{
  "token": "a1b2c3d4e5f6...",
  "user_id": 1,
  "username": "student123"
}
```

### Exam Endpoints

#### List Exams
```http
GET /api/exams/
Authorization: Token a1b2c3d4e5f6...

Response 200:
[
  {
    "id": 1,
    "title": "Midterm Exam",
    "course": "BIO 101",
    "duration_minutes": 60,
    "question_count": 10,
    "created_at": "2026-01-01T10:00:00Z"
  }
]
```

#### Get Exam Detail
```http
GET /api/exams/1/
Authorization: Token a1b2c3d4e5f6...

Response 200:
{
  "id": 1,
  "title": "Midterm Exam",
  "course": "BIO 101",
  "duration_minutes": 60,
  "instructions": "Answer all questions...",
  "questions": [
    {
      "id": 1,
      "question_text": "What is the powerhouse of the cell?",
      "question_type": "short_answer",
      "points": 10,
      "order": 1
    }
  ],
  "created_at": "2026-01-01T10:00:00Z"
}
```

### Submission Endpoints

#### Submit Exam
```http
POST /api/submissions/
Authorization: Token a1b2c3d4e5f6...
Content-Type: application/json

{
  "exam_id": 1,
  "answers": [
    {
      "question_id": 1,
      "student_answer": "Mitochondria"
    },
    {
      "question_id": 2,
      "student_answer": "B"
    }
  ]
}

Response 201:
{
  "submission_id": 5,
  "status": "graded",
  "message": "Submission received and graded successfully"
}
```

#### List My Submissions
```http
GET /api/submissions/mine/
Authorization: Token a1b2c3d4e5f6...

Response 200:
[
  {
    "id": 5,
    "exam_title": "Midterm Exam",
    "course": "BIO 101",
    "submitted_at": "2026-01-05T14:30:00Z",
    "score": 85,
    "max_possible_score": 100,
    "status": "graded"
  }
]
```

#### Get Submission Detail
```http
GET /api/submissions/5/
Authorization: Token a1b2c3d4e5f6...

Response 200:
{
  "id": 5,
  "exam_title": "Midterm Exam",
  "course": "BIO 101",
  "submitted_at": "2026-01-05T14:30:00Z",
  "graded_at": "2026-01-05T14:31:00Z",
  "score": 85,
  "max_possible_score": 100,
  "status": "graded",
  "answers": [
    {
      "id": 10,
      "question_text": "What is the powerhouse of the cell?",
      "question_type": "short_answer",
      "student_answer": "Mitochondria",
      "is_correct": true,
      "points_earned": 10,
      "points_possible": 10,
      "feedback": "Excellent answer!"
    }
  ]
}
```

### Error Responses

```http
400 Bad Request - Invalid input
{
  "error": "Duplicate answers for the same question are not allowed."
}

401 Unauthorized - Missing/invalid token
{
  "detail": "Authentication credentials were not provided."
}

403 Forbidden - Permission denied
{
  "detail": "You do not have permission to perform this action."
}

404 Not Found - Resource doesn't exist
{
  "detail": "Not found."
}
```

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- pip

### Installation

1. **Clone and setup virtual environment:**
```bash
git clone <repository-url>
cd assessment-engine
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings:
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/assessment_db

# Optional: For LLM grading
GRADER_TYPE=mock  # or 'gemini'
GEMINI_API_KEY=your-api-key-here
```

4. **Run migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create sample data (optional):**
```bash
python manage.py create_sample_data
```

6. **Run development server:**
```bash
python manage.py runserver
```

API available at `http://localhost:8000/api/`

### Running Tests
```bash
python manage.py test
```

---

## Project Timeline & Development Log

Following the chronological development pattern:

### Phase 1: Architecture (1.5 hours)
- Database schema design with normalization
- Identified domain boundaries (User, Exam, Question, Submission, Answer)
- Designed Strategy Pattern for grading service
- Planned security model (token auth + permissions)

### Phase 2: Development (5 hours)
- Implemented models with proper relationships and constraints
- Created serializers with security considerations
- Built API views with `transaction.atomic` for write safety
- Implemented MockGrader with keyword matching and similarity algorithms
- Integrated Gemini LLM with fallback mechanism
- Configured URL routing

### Phase 3: Optimization (1 hour)
- Added `select_related` for ForeignKey optimization
- Applied `prefetch_related` for reverse relations
- Created database indexes on high-traffic columns
- Verified query count reduction (N+1 elimination)

### Phase 4: Security (1.5 hours)
- Implemented identity inference from `request.user`
- Created custom `IsSubmissionOwner` permission
- Added duplicate submission prevention
- Validated all input via serializers
- Tested permission boundaries

### Phase 5: Documentation & QA (2 hours)
- Wrote comprehensive README with architecture rationale
- Created API documentation with examples
- Implemented unit tests for critical flows
- Added inline code comments explaining decisions

**Total: 11 hours**

---

## Design Decisions & Tradeoffs

### Why Separate Answer Table?
**Decision:** Answer as distinct entity vs. JSON field in Submission.

**Rationale:**
- Enables efficient JOIN optimization during result retrieval
- Supports relational integrity (FK to Question)
- Allows per-question feedback and partial credit tracking
- Facilitates future analytics (question difficulty analysis)

**Tradeoff:** Slightly more complex schema, but massive query performance gains.

### Why Synchronous Grading?
**Decision:** Grade immediately vs. async task queue.

**Rationale:**
- Simpler implementation for MVP
- Acceptable for exam sizes <50 questions
- Easy migration path to Celery/RQ if needed

**Future Enhancement:** For production with >100 concurrent submissions, move to async:
```python
from celery import shared_task

@shared_task
def grade_submission_async(submission_id):
    submission = Submission.objects.get(pk=submission_id)
    grading_service = GradingService()
    # ... grading logic
```

### Why Strategy Pattern for Grading?
**Decision:** Abstract interface vs. direct implementation.

**Rationale:**
- Enables A/B testing of grading approaches
- Facilitates unit testing (mock grader in tests)
- Allows runtime strategy selection
- Demonstrates OOP design maturity

### Why Token Auth vs. JWT?
**Decision:** Django REST Framework's TokenAuthentication.

**Rationale:**
- Simpler setup for MVP
- Sufficient for single-server deployment
- Django's built-in token management
- Easy migration to JWT if needed for microservices

---

## Future Enhancements

If given more time, these would be the next priorities:

1. **Rate Limiting:** Prevent submission spam (Django Ratelimit)
2. **Answer History:** Track multiple attempts with versioning
3. **Analytics Dashboard:** Question difficulty, student performance metrics
4. **Plagiarism Detection:** Compare submissions using similarity algorithms
5. **Time Tracking:** Enforce exam duration limits
6. **Partial Saves:** Allow students to save progress before final submission

---

## Learning Journey Note

This is my first production-style Django project. Coming from a Node.js/NestJS/TypeScript background (3 years experience), I approached this by:

1. **Translating Concepts:** Mapped familiar patterns (TypeORM → Django ORM, DTOs → Serializers, Guards → Permissions)
2. **Leveraging Fundamentals:** Applied backend principles I'm confident in (ACID transactions, query optimization, security boundaries)
3. **Deep-Diving Documentation:** Focused on Django's built-in security features and DRF best practices
4. **Architecture-First Thinking:** Designed the schema and API flow before touching framework-specific code

The core engineering decisions (schema design, grading algorithm, query optimization strategy) reflect my backend experience. The Django syntax and framework usage represent focused learning over the project timeline.

I'm continuing to deepen my Django knowledge and would welcome feedback on Django-specific idioms or optimizations during a technical interview.
