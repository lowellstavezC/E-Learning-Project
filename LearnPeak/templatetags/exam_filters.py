from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def get_exam_result(results, exam):
    """Get a specific exam result from a queryset of results"""
    for result in results:
        if result.exam == exam:
            return result
    return None

@register.filter
def average_exam_score(results):
    """Calculate the average score for exam results"""
    if not results:
        return None
    
    scores = [result.score for result in results if result.score is not None]
    if not scores:
        return None
    
    return sum(scores) / len(scores)