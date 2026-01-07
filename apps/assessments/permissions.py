from rest_framework import permissions


class IsSubmissionOwner(permissions.BasePermission):
    """
    Only allow students to access their own submissions.
    
    This enforces data isolation at the permission layer,
    preventing horizontal privilege escalation attacks.
    """
    
    def has_object_permission(self, request, view, obj):
        # Assume 'obj' has a 'student' attribute that references the user who owns the submission
        return obj.student == request.user