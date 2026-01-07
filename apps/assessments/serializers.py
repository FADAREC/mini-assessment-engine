from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Exam, Question, Submission, Answer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
    
    def create(self, validated_data):
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
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'points', 'order']


class QuestionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class ExamListSerializer(serializers.ModelSerializer):
    """
    Lightweight exam listing for browse view.
    Would use annotation from the view to avoid N+1 queries on question_count.
    """
    question_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Exam
        fields = ['id', 'title', 'course', 'duration_minutes', 'question_count', 'created_at']


class ExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exam
        fields = ['id', 'title', 'course', 'duration_minutes', 
                  'instructions', 'questions', 'created_at']


class AnswerSubmissionSerializer(serializers.Serializer):
    """
    Validate incoming answer data during submission.
    """
    question_id = serializers.UUIDField()
    student_answer = serializers.CharField(allow_blank=False)


class SubmissionCreateSerializer(serializers.Serializer):
    """
    Handle exam submission payload seperately.
    """
    exam_id = serializers.UUIDField()
    answers = AnswerSubmissionSerializer(many=True)
    
    def validate_answers(self, value):
        """I'm ensuring no duplicate question_ids in submission."""
        question_ids = [a['question_id'] for a in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError(
                "Duplicate answers for the same question are not allowed."
            )
        return value


class AnswerDetailSerializer(serializers.ModelSerializer):
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
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    course = serializers.CharField(source='exam.course', read_only=True)
    answers = AnswerDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'exam_title', 'course', 'submitted_at', 'graded_at',
                  'score', 'max_possible_score', 'status', 'answers']