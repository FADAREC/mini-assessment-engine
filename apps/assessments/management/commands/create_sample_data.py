from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.assessments.models import Exam, Question

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates sample exam data for testing the API'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')
        
        # Create sample users
        if not User.objects.filter(username='student1').exists():
            user1 = User.objects.create_user(
                username='student1',
                email='student1@test.com',
                password='testpass123',
                first_name='Alice',
                last_name='Johnson'
            )
            self.stdout.write(self.style.SUCCESS(f'Created user: student1'))
        
        if not User.objects.filter(username='student2').exists():
            user2 = User.objects.create_user(
                username='student2',
                email='student2@test.com',
                password='testpass123',
                first_name='Bob',
                last_name='Smith'
            )
            self.stdout.write(self.style.SUCCESS(f'Created user: student2'))
        
        # Create Biology Exam
        bio_exam = Exam.objects.create(
            title='Biology Midterm',
            course='BIO 101',
            duration_minutes=90,
            instructions='Answer all questions to the best of your ability. Partial credit may be awarded.',
            passing_score=70
        )
        
        # Biology Questions
        Question.objects.create(
            exam=bio_exam,
            question_text='What is the powerhouse of the cell?',
            question_type='short_answer',
            expected_answer='Mitochondria',
            points=10,
            order=1
        )
        
        Question.objects.create(
            exam=bio_exam,
            question_text='Photosynthesis occurs in which organelle?',
            question_type='multiple_choice',
            expected_answer='B',
            points=5,
            order=2
        )
        
        Question.objects.create(
            exam=bio_exam,
            question_text='DNA replication is semi-conservative.',
            question_type='true_false',
            expected_answer='True',
            points=5,
            order=3
        )
        
        Question.objects.create(
            exam=bio_exam,
            question_text='Explain the process of photosynthesis and its importance to life on Earth.',
            question_type='essay',
            expected_answer='Photosynthesis is the process by which plants, algae, and some bacteria convert light energy into chemical energy stored in glucose. It occurs in chloroplasts using sunlight, water, and carbon dioxide to produce glucose and oxygen. This process is critical as it forms the base of most food chains and produces the oxygen that aerobic organisms need to survive.',
            points=20,
            order=4
        )
        
        self.stdout.write(self.style.SUCCESS(f'Created Biology Exam with 4 questions'))
        
        # Create Computer Science Exam
        cs_exam = Exam.objects.create(
            title='Introduction to Algorithms',
            course='CS 201',
            duration_minutes=60,
            instructions='Show your work where applicable.',
            passing_score=60
        )
        
        # CS Questions
        Question.objects.create(
            exam=cs_exam,
            question_text='What is the time complexity of binary search?',
            question_type='short_answer',
            expected_answer='O(log n)',
            points=10,
            order=1
        )
        
        Question.objects.create(
            exam=cs_exam,
            question_text='Which data structure uses LIFO (Last In First Out)?',
            question_type='multiple_choice',
            expected_answer='C',
            points=5,
            order=2
        )
        
        Question.objects.create(
            exam=cs_exam,
            question_text='Quicksort is a stable sorting algorithm.',
            question_type='true_false',
            expected_answer='False',
            points=5,
            order=3
        )
        
        Question.objects.create(
            exam=cs_exam,
            question_text='Explain the difference between depth-first search (DFS) and breadth-first search (BFS) in graph traversal.',
            question_type='essay',
            expected_answer='DFS explores as far as possible along each branch before backtracking, using a stack (or recursion). BFS explores all neighbors at the current depth before moving to the next level, using a queue. DFS is better for finding paths and detecting cycles, while BFS is optimal for finding shortest paths in unweighted graphs.',
            points=15,
            order=4
        )
        
        self.stdout.write(self.style.SUCCESS(f'Created CS Exam with 4 questions'))
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('Test credentials: username=student1, password=testpass123')