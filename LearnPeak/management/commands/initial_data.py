from django.core.management.base import BaseCommand
from LearnPeak.models import Role, User, CourseCategory

class Command(BaseCommand):
    help = 'Populate initial data'

    def handle(self, *args, **kwargs):
        # Create roles
        roles = ['admin', 'teacher', 'student']
        for role_name in roles:
            Role.objects.get_or_create(role_name=role_name)
        self.stdout.write(self.style.SUCCESS('Created roles'))

        # Create course categories
        categories = [
            {
                'name': 'Programming',
                'description': 'Learn various programming languages and software development.'
            },
            {
                'name': 'Data Science',
                'description': 'Explore data analysis, machine learning, and statistics.'
            },
            {
                'name': 'Design',
                'description': 'Master graphic design, UI/UX, and digital art.'
            },
            {
                'name': 'Business',
                'description': 'Study business management, marketing, and entrepreneurship.'
            }
        ]
        
        for category in categories:
            CourseCategory.objects.get_or_create(
                name=category['name'],
                defaults={'description': category['description']}
            )
        self.stdout.write(self.style.SUCCESS('Created course categories')) 