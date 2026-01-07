import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone


class User(AbstractUser):
    # AbstractUser already has first_name and last_name
    # We'll use those instead of full_name
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
        ]


class Exam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    course = models.CharField(max_length=100)
    duration_minutes = models.IntegerField(validators=[MinValueValidator(1)])
    instructions = models.TextField(blank=True)
    passing_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exams'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course} - {self.title}"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('essay', 'Essay'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]
    
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.CASCADE, 
        related_name='questions'
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    expected_answer = models.TextField()
    points = models.IntegerField(validators=[MinValueValidator(1)])
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['exam', 'order']
        # I added an index here to optimize queries when fetching exam questions
        indexes = [
            models.Index(fields=['exam', 'order']),
        ]
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"


class Submission(models.Model):
    """
    Student's attempt at an exam.
    
    I'm using status tracking to enable async grading without blocking submission.
    The unique constraint enforces one-submission-per-exam-per-student, which is 
    a business rule I implemented to prevent accidental resubmission.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('grading', 'Grading'),
        ('graded', 'Graded'),
        ('failed', 'Grading Failed'),
    ]
    
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    score = models.IntegerField(null=True, blank=True)
    max_possible_score = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='submitted'
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    graded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'submissions'
        ordering = ['-submitted_at']
        # Prevent duplicate submissions per student per exam
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'exam'], 
                name='unique_student_exam_submission'
            )
        ]
        # Critical indexes for result retrieval queries
        indexes = [
            models.Index(fields=['student', '-submitted_at']),
            models.Index(fields=['exam']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"


class Answer(models.Model):
    """
    Individual question response within a submission.
    Grading fields are populated by the grading service after submission.
    
    I separated this from Submission to enable:
    - Granular per-question grading
    - Partial credit tracking
    - Efficient JOIN queries during result retrieval
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        Submission, 
        on_delete=models.CASCADE, 
        related_name='answers'
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE,
        related_name='student_answers'
    )
    student_answer = models.TextField()
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'answers'
        # Index for efficient answer retrieval during grading
        indexes = [
            models.Index(fields=['submission']),
            models.Index(fields=['question']),
        ]
        # Ensure one answer per question per submission
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'question'],
                name='unique_submission_question_answer'
            )
        ]
    
    def __str__(self):
        return f"Answer to Q{self.question.order} in {self.submission.id}"