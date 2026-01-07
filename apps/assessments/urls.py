from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    ExamListView,
    ExamDetailView,
    SubmissionCreateView,
    SubmissionListView,
    SubmissionDetailView,
)

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # Exams
    path('exams/', ExamListView.as_view(), name='exam-list'),
    path('exams/<int:pk>/', ExamDetailView.as_view(), name='exam-detail'),
    
    # Submissions
    path('submissions/', SubmissionCreateView.as_view(), name='submission-create'),
    path('submissions/mine/', SubmissionListView.as_view(), name='submission-list'),
    path('submissions/<int:pk>/', SubmissionDetailView.as_view(), name='submission-detail'),
]