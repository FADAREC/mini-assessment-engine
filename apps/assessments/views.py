from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

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


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate token for auto-login
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                'user_id': user.id,
                'username': user.username
            })
        
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


class ExamListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExamListSerializer
    queryset = Exam.objects.prefetch_related('questions').all()


class ExamDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExamDetailSerializer
    queryset = Exam.objects.prefetch_related('questions').all()
    lookup_field = 'pk'


class SubmissionCreateView(APIView):
    """
    Submit exam answers securely.
    
    Security measures to set in place:
    - Identity inferred from request.user (no user_id in payload)
    - Validates all questions before creating submission
    - Unique constraint prevents duplicate submissions
    - transaction.atomic ensures all-or-nothing writes
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = SubmissionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        exam_id = serializer.validated_data['exam_id']
        answers_data = serializer.validated_data['answers']
        
        # Validate exam exists
        exam = get_object_or_404(Exam, pk=exam_id)
        
        # Fetch all questions for this exam (single query)
        exam_questions = {q.id: q for q in exam.questions.all()}
        
        # Validate all answers reference valid questions
        for answer_data in answers_data:
            qid = answer_data['question_id']
            if qid not in exam_questions:
                return Response(
                    {'error': f'Invalid question_id: {qid} for exam {exam_id}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check for duplicate submission (belt-and-suspenders with DB constraint)
        if Submission.objects.filter(student=request.user, exam=exam).exists():
            return Response(
                {'error': 'You have already submitted this exam'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate max possible score
        max_score = sum(q.points for q in exam_questions.values())
        
        # Create submission (identity from request.user, not payload)
        submission = Submission.objects.create(
            student=request.user,
            exam=exam,
            status='submitted',
            submitted_at=timezone.now(),
            max_possible_score=max_score
        )
        
        # Bulk create answers
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
        Internal grading logic.
        In production, this should be async (Celery task).
        """
        submission.status = 'grading'
        submission.save()
        
        grading_service = GradingService()
        total_score, max_possible = grading_service.grade_submission(submission)
        
        # Update submission with results
        submission.score = total_score
        submission.status = 'graded'
        submission.graded_at = timezone.now()
        submission.save()


class SubmissionListView(generics.ListAPIView):
    """
    List student's own submissions.
    
    Security: Filters by request.user automatically (no user_id param).
    Optimization: select_related('exam') prevents N+1 on exam lookups.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubmissionListSerializer
    
    def get_queryset(self):
        return Submission.objects.filter(
            student=self.request.user
        ).select_related('exam').order_by('-submitted_at')


class SubmissionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsSubmissionOwner]
    serializer_class = SubmissionDetailSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        base_queryset = Submission.objects.all()
        
        # Apply aggressive query optimization
        return base_queryset.select_related(
            'exam',
            'student'
        ).prefetch_related(
            'answers__question'
        )