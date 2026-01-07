"""
Unit tests covering critical business logic and security.

Tests On:
- Authentication and authorization
- Duplicate submission prevention
- Query optimization (via Django debug toolbar in dev)
- Grading accuracy
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Exam, Question, Submission, Answer
from .grading_service import MockGrader

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    """Test authentication flows."""
    
    def test_user_registration(self):
        """Test student can register and receive token."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_user_login(self):
        """Test student can login with valid credentials."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        data = {'username': 'testuser', 'password': 'testpass123'}
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)


class SubmissionSecurityTestCase(APITestCase):
    """Test submission security and permissions."""
    
    def setUp(self):
        # Get the actual User model from Django
        User = get_user_model()
        
        self.user1 = User.objects.create_user(
            username='student1',
            email='s1@test.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='student2',
            email='s2@test.com',
            password='pass123'
        )
        
        self.exam = Exam.objects.create(
            title='Test Exam',
            course='CS101',
            duration_minutes=60
        )
        
        self.question = Question.objects.create(
            exam=self.exam,
            question_text='What is 2+2?',
            question_type='short_answer',
            expected_answer='4',
            points=10,
            order=1
        )
    
    def test_cannot_view_other_student_submission(self):
        """Students cannot access other students' submissions."""
        # User1 creates submission
        submission = Submission.objects.create(
            student=self.user1,
            exam=self.exam,
            status='graded',
            score=10,
            max_possible_score=10
        )
        
        # User2 tries to access it
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f'/api/submissions/{submission.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_duplicate_submission_prevented(self):
        """Students cannot submit same exam twice."""
        self.client.force_authenticate(user=self.user1)
        
        submission_data = {
            'exam_id': self.exam.id,
            'answers': [
                {'question_id': self.question.id, 'student_answer': '4'}
            ]
        }
        
        # Prevent  Duplicate submission
        # First submission succeeds
        response1 = self.client.post('/api/submissions/', submission_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second submission fails
        response2 = self.client.post('/api/submissions/', submission_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already submitted', str(response2.data).lower())


class GradingServiceTestCase(TestCase):
    """Test grading algorithms."""
    
    def setUp(self):
        self.grader = MockGrader()
        self.exam = Exam.objects.create(
            title='Test Exam',
            course='CS101',
            duration_minutes=60
        )
    
    def test_multiple_choice_grading(self):
        """Test exact match for multiple choice."""
        question = Question.objects.create(
            exam=self.exam,
            question_text='What is 2+2?',
            question_type='multiple_choice',
            expected_answer='B',
            points=10,
            order=1
        )
        
        # Correct answer
        result = self.grader.grade_answer(question, 'B')
        self.assertTrue(result['is_correct'])
        self.assertEqual(result['points_earned'], 10)
        
        # Incorrect answer
        result = self.grader.grade_answer(question, 'C')
        self.assertFalse(result['is_correct'])
        self.assertEqual(result['points_earned'], 0)
    
    def test_short_answer_partial_credit(self):
        """Test similarity-based grading for short answers."""
        question = Question.objects.create(
            exam=self.exam,
            question_text='What is the powerhouse of the cell?',
            question_type='short_answer',
            expected_answer='Mitochondria',
            points=10,
            order=1
        )
        
        # Exact match
        result = self.grader.grade_answer(question, 'Mitochondria')
        self.assertTrue(result['is_correct'])
        self.assertEqual(result['points_earned'], 10)
        
        # Close match (typo)
        result = self.grader.grade_answer(question, 'Mitochondrion')
        self.assertTrue(result['is_correct'])
        self.assertGreater(result['points_earned'], 5)
    
    def test_essay_keyword_grading(self):
        """Test keyword density for essay questions."""
        question = Question.objects.create(
            exam=self.exam,
            question_text='Explain photosynthesis',
            question_type='essay',
            expected_answer='Photosynthesis is a process where plants use sunlight, water, and carbon dioxide to produce glucose and oxygen in chloroplasts.',
            points=20,
            order=1
        )
        
        # Good answer with keywords
        good_answer = """
        Photosynthesis is the process by which plants convert light energy 
        into chemical energy. It occurs in chloroplasts and requires sunlight, 
        water, and carbon dioxide. The end products are glucose and oxygen.
        """
        result = self.grader.grade_answer(question, good_answer)
        self.assertGreater(result['points_earned'], 10)
        
        # Poor answer without keywords
        poor_answer = "Plants make food somehow."
        result = self.grader.grade_answer(question, poor_answer)
        self.assertLess(result['points_earned'], 5)