from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Exam, Question, Submission, Answer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Registration with password hashing via set_password."""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
    
    def create(self, validated_data):
        # would use set_password to ensure proper hashing
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class QuestionSerializer(serializers.ModelSerializer):
    """
    Public question view - excludes expected_answer for security.
    Students must never see answers before submission.
    """
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'points', 'order']


class QuestionDetailSerializer(serializers.ModelSerializer):
    """
    Admin/grading view - includes expected_answer.
    Used internally by grading service.
    """
    class Meta:
        model = Question
        fields = '__all__'


class ExamListSerializer(serializers.ModelSerializer):
    """Lightweight exam listing for browse view."""
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = ['id', 'title', 'course', 'duration_minutes', 'question_count', 'created_at']
    
    def get_question_count(self, obj):
        return obj.questions.count()


class ExamDetailSerializer(serializers.ModelSerializer):
    """
    Full exam with questions for take-exam view.
    need to use nested serializer for efficient single-query fetch.
    """
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exam
        fields = ['id', 'title', 'course', 'duration_minutes', 
                  'instructions', 'questions', 'created_at']


class AnswerSubmissionSerializer(serializers.Serializer):
    """
    Validates incoming answer data during submission.
    Not tied to model - pure validation logic.
    """
    question_id = serializers.IntegerField()
    student_answer = serializers.CharField(allow_blank=False)


class SubmissionCreateSerializer(serializers.Serializer):
    """
    Handles exam submission payload.
    Separated from model serializer for custom validation logic.
    """
    exam_id = serializers.IntegerField()
    answers = AnswerSubmissionSerializer(many=True)
    
    def validate_answers(self, value):
        """Ensure no duplicate question_ids in submission."""
        question_ids = [a['question_id'] for a in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError(
                "Block double answers for the same question."
            )
        return value


class AnswerDetailSerializer(serializers.ModelSerializer):
    """
    Answer view for graded results.
    Includes question context for student review.
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    points_possible = serializers.IntegerField(source='question.points', read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question_text', 'question_type', 'student_answer', 
                  'is_correct', 'points_earned', 'points_possible', 'feedback']


class SubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight submission listing."""
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    course = serializers.CharField(source='exam.course', read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'exam_title', 'course', 'submitted_at', 
                  'score', 'max_possible_score', 'status']


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """
    Full submission with answers for result view.
    Optimized with select_related/prefetch_related in view.
    """
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    course = serializers.CharField(source='exam.course', read_only=True)
    answers = AnswerDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'exam_title', 'course', 'submitted_at', 'graded_at',
                  'score', 'max_possible_score', 'status', 'answers']