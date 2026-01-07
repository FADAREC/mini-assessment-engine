from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Exam, Question, Submission, Answer
from .serializers import (
    UserRegistrationSerializer,
    ExamListSerializer,
    ExamDetailSerializer,
    SubmissionCreateSerializer,
    SubmissionListSerializer,
    SubmissionDetailSerializer,
)
from .grading_service import GradingService
from .permissions import IsSubmissionOwner


@extend_schema(
    tags=['Authentication'],
    summary='Register a new student account',
    description='''
    Creates a new student account and returns an authentication token.
    
    **Security Note:** User IDs are not exposed in the response to prevent ID enumeration attacks.
    
    **Password Requirements:**
    - Minimum 8 characters
    - Will be hashed using Django's PBKDF2 algorithm
    ''',
    request=UserRegistrationSerializer,
    responses={
        201: {
            'description': 'Account created successfully',
            'content': {
                'application/json': {
                    'example': {
                        'username': 'student123',
                        'email': 'student@university.edu',
                        'token': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
                    }
                }
            }
        },
        400: {
            'description': 'Validation error',
            'content': {
                'application/json': {
                    'examples': {
                        'missing_field': {
                            'summary': 'Missing required field',
                            'value': {
                                'password': ['This field is required.']
                            }
                        },
                        'weak_password': {
                            'summary': 'Password too short',
                            'value': {
                                'password': ['Ensure this field has at least 8 characters.']
                            }
                        },
                        'duplicate_username': {
                            'summary': 'Username already exists',
                            'value': {
                                'username': ['A user with that username already exists.']
                            }
                        }
                    }
                }
            }
        }
    }
)
class RegisterView(APIView):
    """
    Student registration endpoint.
    Return a token for immediate authentication post-signup and prevent user_id from beign exposed to prevent ID enumeration.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'username': user.username,
                'email': user.email,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Login to get authentication token',
    description='''
    Authenticates a student and returns a token for subsequent API calls.
    
    **How to use the token:**
    Include it in the Authorization header of all subsequent requests:
    ```
    Authorization: Token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    ```
    ''',
    request={
        'application/json': {
            'example': {
                'username': 'student123',
                'password': 'securepass123'
            }
        }
    },
    responses={
        200: {
            'description': 'Login successful',
            'content': {
                'application/json': {
                    'example': {
                        'token': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6',
                        'username': 'student123'
                    }
                }
            }
        },
        400: {
            'description': 'Missing credentials',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Username and password required'
                    }
                }
            }
        },
        401: {
            'description': 'Invalid credentials',
            'content': {
                'application/json': {
                    'example': {
                        'error': 'Invalid credentials'
                    }
                }
            }
        }
    }
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'username': user.username
            })
        
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


@extend_schema(
    tags=['Exams'],
    summary='List all available exams',
    description='''
    Returns a paginated list of all exams available to take.
    
    **Query Optimization:**
    This endpoint uses database-level aggregation (COUNT) to calculate question counts,
    preventing N+1 query problems even with hundreds of exams.
    
    **Pagination:**
    - Default page size: 20 items
    - Use `?page=2` to get subsequent pages
    ''',
    responses={
        200: {
            'description': 'List of exams',
            'content': {
                'application/json': {
                    'example': {
                        'count': 2,
                        'next': None,
                        'previous': None,
                        'results': [
                            {
                                'id': '550e8400-e29b-41d4-a716-446655440000',
                                'title': 'Biology Midterm',
                                'course': 'BIO 101',
                                'duration_minutes': 90,
                                'question_count': 10,
                                'created_at': '2026-01-01T10:00:00Z'
                            },
                            {
                                'id': '650e8400-e29b-41d4-a716-446655440000',
                                'title': 'Introduction to Algorithms',
                                'course': 'CS 201',
                                'duration_minutes': 60,
                                'question_count': 8,
                                'created_at': '2026-01-02T14:00:00Z'
                            }
                        ]
                    }
                }
            }
        },
        401: {
            'description': 'Not authenticated',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Authentication credentials were not provided.'
                    }
                }
            }
        }
    }
)
class ExamListView(generics.ListAPIView):
    """
    List all available exams.
    Ensure the calculation of question_count is done at database level to prevent N+1 queries.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExamListSerializer
    
    def get_queryset(self):
        from django.db.models import Count
        return Exam.objects.annotate(
            question_count=Count('questions')
        ).all()


@extend_schema(
    tags=['Exams'],
    summary='Get exam details with questions',
    description='''
    Returns full exam information including all questions for taking the exam.
    
    **Security Note:**
    - Expected answers are NOT included in the response
    - Students can only see question text, type, and point values
    - Expected answers are only visible after submission in the results
    
    **Use this endpoint to:**
    1. Display the exam to students
    2. Build the exam-taking interface
    3. Get question IDs for submission
    ''',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description='Exam UUID'
        )
    ],
    responses={
        200: {
            'description': 'Exam details with questions',
            'content': {
                'application/json': {
                    'example': {
                        'id': '550e8400-e29b-41d4-a716-446655440000',
                        'title': 'Biology Midterm',
                        'course': 'BIO 101',
                        'duration_minutes': 90,
                        'instructions': 'Answer all questions to the best of your ability.',
                        'created_at': '2026-01-01T10:00:00Z',
                        'questions': [
                            {
                                'id': '750e8400-e29b-41d4-a716-446655440000',
                                'question_text': 'What is the powerhouse of the cell?',
                                'question_type': 'short_answer',
                                'points': 10,
                                'order': 1
                            },
                            {
                                'id': '850e8400-e29b-41d4-a716-446655440000',
                                'question_text': 'Photosynthesis occurs in which organelle?',
                                'question_type': 'multiple_choice',
                                'points': 5,
                                'order': 2
                            }
                        ]
                    }
                }
            }
        },
        404: {
            'description': 'Exam not found',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Not found.'
                    }
                }
            }
        }
    }
)
class ExamDetailView(generics.RetrieveAPIView):
    """
    Get exam with questions for take-exam view.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExamDetailSerializer
    queryset = Exam.objects.prefetch_related('questions').all()
    lookup_field = 'pk'


@extend_schema(
    tags=['Submissions'],
    summary='Submit exam answers for grading',
    description='''
    Submits student answers for an exam and triggers automated grading.
    
    **Security Features:**
    - Student identity inferred from auth token (cannot submit for others)
    - Duplicate submissions prevented (one attempt per exam)
    - All question IDs validated against the exam
    - Transaction-safe: either all answers save or none do
    
    **Grading Process:**
    1. Submission is saved immediately with status='submitted'
    2. Grading service evaluates each answer
    3. Status updated to 'graded' with total score
    4. If grading fails, status='failed' (submission is not lost)
    
    **Important:**
    - You must answer ALL questions in the exam
    - Each question_id must be from the specified exam
    - You cannot submit the same exam twice
    ''',
    request={
        'application/json': {
            'example': {
                'exam_id': '550e8400-e29b-41d4-a716-446655440000',
                'answers': [
                    {
                        'question_id': '750e8400-e29b-41d4-a716-446655440000',
                        'student_answer': 'Mitochondria'
                    },
                    {
                        'question_id': '850e8400-e29b-41d4-a716-446655440000',
                        'student_answer': 'B'
                    }
                ]
            }
        }
    },
    responses={
        201: {
            'description': 'Submission successful',
            'content': {
                'application/json': {
                    'example': {
                        'submission_id': '950e8400-e29b-41d4-a716-446655440000',
                        'status': 'graded',
                        'message': 'Submission received and graded successfully'
                    }
                }
            }
        },
        400: {
            'description': 'Validation error',
            'content': {
                'application/json': {
                    'examples': {
                        'duplicate_submission': {
                            'summary': 'Already submitted this exam',
                            'value': {
                                'error': 'You have already submitted this exam'
                            }
                        },
                        'invalid_question': {
                            'summary': 'Question not in exam',
                            'value': {
                                'error': 'Invalid question_id: 750e8400-e29b-41d4-a716-446655440000 for exam 550e8400-e29b-41d4-a716-446655440000'
                            }
                        },
                        'duplicate_answers': {
                            'summary': 'Answered same question twice',
                            'value': {
                                'answers': ['Duplicate answers for the same question are not allowed.']
                            }
                        },
                        'missing_answer': {
                            'summary': 'Empty answer',
                            'value': {
                                'answers': [{'student_answer': ['This field may not be blank.']}]
                            }
                        }
                    }
                }
            }
        },
        404: {
            'description': 'Exam not found',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Not found.'
                    }
                }
            }
        }
    }
)
class SubmissionCreateView(APIView):
    """
    Submit exam answers securely.
    
    Security measures to put in place:
    - Infer Identity from request.user (so no user_id would be exposed in payload)
    - Validate all questions before creating submission
    - Prevent duplicate submissions using unique constraint
    - Make everything transactional so it's either all-or-nothing writes
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = SubmissionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        exam_id = serializer.validated_data['exam_id']
        answers_data = serializer.validated_data['answers']
        
        exam = get_object_or_404(Exam, pk=exam_id)
        
        exam_questions = {q.id: q for q in exam.questions.all()}
        
        for answer_data in answers_data:
            qid = answer_data['question_id']
            if qid not in exam_questions:
                return Response(
                    {'error': f'Invalid question_id: {qid} for exam {exam_id}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if Submission.objects.filter(student=request.user, exam=exam).exists():
            return Response(
                {'error': 'You have already submitted this exam'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_score = sum(q.points for q in exam_questions.values())
        
        # Create submission (identity from request.user, not payload)
        submission = Submission.objects.create(
            student=request.user,
            exam=exam,
            status='submitted',
            submitted_at=timezone.now(),
            max_possible_score=max_score
        )
        
        answer_objects = [
            Answer(
                submission=submission,
                question=exam_questions[ans['question_id']],
                student_answer=ans['student_answer']
            )
            for ans in answers_data
        ]
        Answer.objects.bulk_create(answer_objects)
        
        # Trigger grading (synchronous for now - can be made async with Celery)
        self._grade_submission(submission)
        
        return Response({
            'submission_id': submission.id,
            'status': submission.status,
            'message': 'Submission received and graded successfully'
        }, status=status.HTTP_201_CREATED)
    
    def _grade_submission(self, submission):
        """
        If grading fails, I'm saving submission as 'failed' rather than crashing.
        In an actual production env, this should be an async Celery task.
        """
        try:
            submission.status = 'grading'
            submission.save()
            
            grading_service = GradingService()
            total_score, max_possible = grading_service.grade_submission(submission)
            
            # Update submission with results
            submission.score = total_score
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.save()
        except Exception as e:
            # If grading fails, mark as failed but don't crash
            submission.status = 'failed'
            submission.save()
            print(f"Grading failed for submission {submission.id}: {str(e)}")


@extend_schema(
    tags=['Submissions'],
    summary='List my submissions',
    description='''
    Returns all exam submissions for the authenticated student.
    
    **Security:**
    - Automatically filtered by authenticated user
    - Students can ONLY see their own submissions
    - No way to access other students' data
    
    **Ordered by:**
    Most recent submissions first (descending by submitted_at)
    ''',
    responses={
        200: {
            'description': 'List of submissions',
            'content': {
                'application/json': {
                    'example': {
                        'count': 2,
                        'next': None,
                        'previous': None,
                        'results': [
                            {
                                'id': '950e8400-e29b-41d4-a716-446655440000',
                                'exam_title': 'Biology Midterm',
                                'course': 'BIO 101',
                                'submitted_at': '2026-01-05T14:30:00Z',
                                'score': 85,
                                'max_possible_score': 100,
                                'status': 'graded'
                            },
                            {
                                'id': 'a50e8400-e29b-41d4-a716-446655440000',
                                'exam_title': 'Introduction to Algorithms',
                                'course': 'CS 201',
                                'submitted_at': '2026-01-04T10:15:00Z',
                                'score': 72,
                                'max_possible_score': 80,
                                'status': 'graded'
                            }
                        ]
                    }
                }
            }
        }
    }
)
class SubmissionListView(generics.ListAPIView):
    """
    List student's own submissions.
    
    Security: Filter request.user automatically (no user_id param should be collected).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubmissionListSerializer
    
    def get_queryset(self):
        return Submission.objects.filter(
            student=self.request.user
        ).select_related('exam').order_by('-submitted_at')


@extend_schema(
    tags=['Submissions'],
    summary='Get detailed submission results',
    description='''
    Returns full submission details including all answers, scores, and feedback.
    
    **Security:**
    - You can ONLY access your own submissions
    - Attempting to access another student's submission returns 403 Forbidden
    - UUIDs prevent ID enumeration attacks
    
    **Query Optimization:**
    This endpoint uses aggressive query optimization:
    - select_related() for exam data (single JOIN)
    - prefetch_related() for answers + questions (1 additional query)
    - Total: 2 queries regardless of number of answers
    
    **Use this to:**
    1. Show students their graded results
    2. Display detailed feedback per question
    3. Show correct answers after grading
    ''',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description='Submission UUID'
        )
    ],
    responses={
        200: {
            'description': 'Detailed submission with answers',
            'content': {
                'application/json': {
                    'example': {
                        'id': '950e8400-e29b-41d4-a716-446655440000',
                        'exam_title': 'Biology Midterm',
                        'course': 'BIO 101',
                        'submitted_at': '2026-01-05T14:30:00Z',
                        'graded_at': '2026-01-05T14:31:00Z',
                        'score': 85,
                        'max_possible_score': 100,
                        'status': 'graded',
                        'answers': [
                            {
                                'id': 'b50e8400-e29b-41d4-a716-446655440000',
                                'question_text': 'What is the powerhouse of the cell?',
                                'question_type': 'short_answer',
                                'student_answer': 'Mitochondria',
                                'is_correct': True,
                                'points_earned': 10,
                                'points_possible': 10,
                                'feedback': 'Excellent answer!'
                            },
                            {
                                'id': 'c50e8400-e29b-41d4-a716-446655440000',
                                'question_text': 'Photosynthesis occurs in which organelle?',
                                'question_type': 'multiple_choice',
                                'student_answer': 'B',
                                'is_correct': True,
                                'points_earned': 5,
                                'points_possible': 5,
                                'feedback': 'Correct!'
                            }
                        ]
                    }
                }
            }
        },
        403: {
            'description': 'Not your submission',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'You do not have permission to perform this action.'
                    }
                }
            }
        },
        404: {
            'description': 'Submission not found',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Not found.'
                    }
                }
            }
        }
    }
)
class SubmissionDetailView(generics.RetrieveAPIView):
    """
    Get detailed submission results with answers.
    
    Security: Ensure students only see their own work.
    """
    permission_classes = [IsAuthenticated, IsSubmissionOwner]
    serializer_class = SubmissionDetailSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        base_queryset = Submission.objects.all()
        
        return base_queryset.select_related(
            'exam',     
            'student'   
        ).prefetch_related(
            'answers__question' 
        )