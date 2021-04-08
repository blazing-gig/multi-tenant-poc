# Create your views here.
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

# Create your views here.
from .models import Hospital, Patient
from .serializers import HospitalSerializer, PatientSerializer
from .tasks import create_patient


class HospitalView(APIView):

    def get(self, request):
        print("within get...")
        data = HospitalSerializer(
            Hospital.objects.all(), many=True
        ).data

        return Response(data=data, status=status.HTTP_200_OK)


class PatientView(APIView):
    def get(self, request):
        data = PatientSerializer(
            Patient.objects.all(), many=True
        ).data
        return Response(
            data=data, status=status.HTTP_200_OK
        )

    def post(self, request):
        create_patient.delay(request.data)
        return Response(
            status=status.HTTP_201_CREATED
        )
