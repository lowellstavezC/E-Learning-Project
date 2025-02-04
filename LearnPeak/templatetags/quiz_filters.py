from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def get_quiz_result(results, quiz):
    """Get a specific quiz result from a queryset of results"""
    return results.filter(quiz=quiz).first()

@register.filter
def average_quiz_score(results):
    """Calculate average score for a set of quiz results"""
    if not results.exists():
        return 0
    return results.aggregate(Avg('score'))['score__avg'] or 0 