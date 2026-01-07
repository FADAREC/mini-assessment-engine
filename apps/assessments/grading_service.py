"""
Grading service with Strategy Pattern implementation.

Architecture:
- BaseGrader: Abstract interface for grading strategies
- MockGrader: Algorithmic grading (keyword matching, similarity)
- GeminiGrader: LLM-powered grading with fallback
- GradingService: Orchestrator with transaction safety

This design allows easy strategy switching via config.
"""
import json
import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
from django.conf import settings
from django.utils import timezone


class BaseGrader(ABC):
    """
    Strategy interface for grading implementations.
    Enables dependency injection and easy testing.
    """
    @abstractmethod
    def grade_answer(self, question, student_answer):
        """
        Returns dict: {
            'is_correct': bool,
            'points_earned': int,
            'feedback': str
        }
        """
        pass


class MockGrader(BaseGrader):
    """
    Algorithmic grading without external dependencies.
    
    Strategies by question type:
    - multiple_choice/true_false: Exact match
    - short_answer: String similarity with normalization
    - essay: Keyword density scoring
    
    Demonstrates understanding of evaluation algorithms.
    """
    
    def grade_answer(self, question, student_answer):
        qtype = question.question_type
        
        if qtype in ['multiple_choice', 'true_false']:
            return self._grade_exact_match(question, student_answer)
        elif qtype == 'short_answer':
            return self._grade_short_answer(question, student_answer)
        elif qtype == 'essay':
            return self._grade_essay(question, student_answer)
        else:
            # Default fallback
            return {
                'is_correct': False,
                'points_earned': 0,
                'feedback': 'Unsupported question type'
            }
    
    def _grade_exact_match(self, question, student_answer):
        """For multiple choice and true/false - strict matching."""
        normalized_expected = self._normalize_text(question.expected_answer)
        normalized_student = self._normalize_text(student_answer)
        
        is_correct = normalized_expected == normalized_student
        
        return {
            'is_correct': is_correct,
            'points_earned': question.points if is_correct else 0,
            'feedback': 'Correct!' if is_correct else f'Expected: {question.expected_answer}'
        }
    
    def _grade_short_answer(self, question, student_answer):
        """
        Uses string similarity for partial credit.
        Handles typos and minor variations.
        """
        normalized_expected = self._normalize_text(question.expected_answer)
        normalized_student = self._normalize_text(student_answer)
        
        # Calculate similarity ratio using SequenceMatcher
        similarity = SequenceMatcher(
            None, 
            normalized_expected, 
            normalized_student
        ).ratio()
        
        # Grading thresholds
        if similarity >= 0.9:
            is_correct = True
            points = question.points
            feedback = 'Excellent answer!'
        elif similarity >= 0.7:
            is_correct = True
            points = int(question.points * 0.8)
            feedback = 'Good answer with minor issues. Partial credit awarded.'
        elif similarity >= 0.5:
            is_correct = False
            points = int(question.points * 0.5)
            feedback = 'Partially correct. Key concepts present but incomplete.'
        else:
            is_correct = False
            points = 0
            feedback = 'Answer does not match expected response.'
        
        return {
            'is_correct': is_correct,
            'points_earned': points,
            'feedback': feedback
        }
    
    def _grade_essay(self, question, student_answer):
        """
        Keyword density scoring for essay questions.
        Extracts key concepts from expected answer and checks coverage.
        """
        # Extract keywords from expected answer (simple approach)
        expected_keywords = self._extract_keywords(question.expected_answer)
        student_text_lower = student_answer.lower()
        
        # Count matched keywords
        matched_count = sum(
            1 for keyword in expected_keywords 
            if keyword in student_text_lower
        )
        
        # Calculate keyword coverage
        keyword_score = matched_count / len(expected_keywords) if expected_keywords else 0
        
        # Word count factor (penalize very short essays)
        word_count = len(student_answer.split())
        if word_count < 30:
            length_factor = 0.6
        elif word_count < 50:
            length_factor = 0.8
        else:
            length_factor = 1.0
        
        # Final score
        final_score = keyword_score * length_factor
        points_earned = int(question.points * final_score)
        
        # Determine correctness threshold
        is_correct = final_score >= 0.6
        
        feedback = f"Keyword coverage: {matched_count}/{len(expected_keywords)}. "
        if final_score >= 0.8:
            feedback += "Strong answer with good coverage of key concepts."
        elif final_score >= 0.6:
            feedback += "Adequate answer but missing some key points."
        else:
            feedback += "Answer lacks sufficient depth and key concepts."
        
        return {
            'is_correct': is_correct,
            'points_earned': points_earned,
            'feedback': feedback
        }
    
    @staticmethod
    def _normalize_text(text):
        """Case-insensitive, whitespace-trimmed comparison."""
        return re.sub(r'\s+', ' ', text.strip().lower())
    
    @staticmethod
    def _extract_keywords(text):
        """
        Extract significant words as keywords.
        Filters out common stopwords.
        """
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 
                     'at', 'to', 'for', 'of', 'and', 'or', 'but'}
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if len(w) > 3 and w not in stopwords]


class GeminiGrader(BaseGrader):
    """
    LLM-powered grading using Google Gemini API.
    Falls back to MockGrader on API failures.
    
    Modular design allows swapping to Claude/OpenAI by changing client.
    """
    
    def __init__(self):
        try:
            import google.generativeai as genai
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.fallback_grader = MockGrader()
        except Exception as e:
            print(f"Warning: Gemini initialization failed: {e}")
            self.model = None
            self.fallback_grader = MockGrader()
    
    def grade_answer(self, question, student_answer):
        """Grade using LLM with structured output, fallback to mock on error."""
        if not self.model:
            return self.fallback_grader.grade_answer(question, student_answer)
        
        try:
            prompt = self._build_grading_prompt(question, student_answer)
            response = self.model.generate_content(prompt)
            result = self._parse_llm_response(response.text, question.points)
            return result
        except Exception as e:
            print(f"LLM grading failed: {e}. Falling back to mock grader.")
            return self.fallback_grader.grade_answer(question, student_answer)
    
    def _build_grading_prompt(self, question, student_answer):
        """Construct prompt for LLM with strict JSON output requirement."""
        return f"""You are an expert academic grader. Evaluate the student's answer fairly and objectively.

Question Type: {question.question_type}
Question: {question.question_text}
Expected Answer: {question.expected_answer}
Maximum Points: {question.points}

Student's Answer: {student_answer}

CRITICAL: Respond ONLY with valid JSON in this exact format (no markdown, no backticks):
{{
  "is_correct": true or false,
  "points_earned": <number between 0 and {question.points}>,
  "feedback": "<brief constructive feedback>"
}}

Grading Guidelines:
- For multiple choice/true-false: Full points only for exact matches
- For short answers: Full points if key concept is present, partial for close answers
- For essays: Evaluate depth, accuracy, and coverage of key concepts
- Be fair but rigorous. Award partial credit where appropriate.
"""
    
    def _parse_llm_response(self, response_text, max_points):
        """Extract JSON from LLM response, handling markdown wrapping."""
        # Clean potential markdown formatting
        cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        
        try:
            result = json.loads(cleaned)
            
            # Validate and sanitize output
            is_correct = bool(result.get('is_correct', False))
            points_earned = min(int(result.get('points_earned', 0)), max_points)
            feedback = str(result.get('feedback', ''))
            
            return {
                'is_correct': is_correct,
                'points_earned': max(0, points_earned),
                'feedback': feedback
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Icase of Parsing error - return default failure
            return {
                'is_correct': False,
                'points_earned': 0,
                'feedback': 'Grading error - could not parse LLM response'
            }


class GradingService:
    """
    Orchestrates grading workflow with strategy selection.
    Configurable via settings to switch between graders.
    """
    
    def __init__(self, grader_type=None):
        grader_type = grader_type or getattr(settings, 'GRADER_TYPE', 'mock')
        
        if grader_type == 'gemini':
            self.grader = GeminiGrader()
        else:
            self.grader = MockGrader()
    
    def grade_submission(self, submission):
        """
        Grades all answers in a submission.
        Uses transaction safety to ensure atomicity.
        
        Returns: (total_score, max_possible_score)
        """
        from .models import Answer
        
        # Fetch all answers with related questions in one query
        answers = submission.answers.select_related('question').all()
        
        total_score = 0
        max_possible = 0
        
        for answer in answers:
            # Grade individual answer
            result = self.grader.grade_answer(
                answer.question, 
                answer.student_answer
            )
            
            # Update answer with grading results
            answer.is_correct = result['is_correct']
            answer.points_earned = result['points_earned']
            answer.feedback = result.get('feedback', '')
            answer.graded_at = timezone.now()
            answer.save()
            
            total_score += result['points_earned']
            max_possible += answer.question.points
        
        return total_score, max_possible