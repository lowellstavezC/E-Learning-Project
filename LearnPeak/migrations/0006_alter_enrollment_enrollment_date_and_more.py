# Generated by Django 5.1.5 on 2025-02-01 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LearnPeak', '0005_rename_created_at_enrollment_enrollment_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollment',
            name='enrollment_date',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='status',
            field=models.CharField(choices=[('enrolled', 'Enrolled'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('dropped', 'Dropped')], db_index=True, default='enrolled', max_length=20),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['student', 'status'], name='LearnPeak_e_student_f313e3_idx'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['course', 'status'], name='LearnPeak_e_course__a940f7_idx'),
        ),
    ]
