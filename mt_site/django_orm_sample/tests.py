# Create your tests here.
from django.test import TestCase

from django_orm_sample.models import Hospital


class HospitalModelTest(TestCase):
    databases = {'default', 'celery_beat_db'}

    def setUp(self):
        Hospital.objects.create(
            name="hello",
            address="hello.com",
        )

    def test_hospital_create(self):
        hello_obj = Hospital.objects.get(name="hello")
        self.assertEqual(hello_obj.name, 'hello')
        self.assertEqual(hello_obj.address, 'hello.com')

    def test_hospital_create_2(self):
        hello_obj = Hospital.objects.get(name="hello")
        self.assertEqual(hello_obj.name, 'hello')
        self.assertEqual(hello_obj.address, 'hello.com')


class HospitalModelTest_2(TestCase):

    def setUp(self):
        Hospital.objects.create(
            name="hello",
            address="hello.com",
        )

    def test_hospital_create(self):
        hello_obj = Hospital.objects.get(name="hello")
        self.assertEqual(hello_obj.name, 'hello')
        self.assertEqual(hello_obj.address, 'hello.com')

    def test_hospital_create_2(self):
        hello_obj = Hospital.objects.get(name="hello")
        self.assertEqual(hello_obj.name, 'hello')
        self.assertEqual(hello_obj.address, 'hello.com')



