# Create celery tasks in this file
from django_orm_sample.models import Patient
from mt_site import celery_app


@celery_app.task
def create_patient(user_details):
    Patient.objects.create(**user_details)
