from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView

# users/views.py
class RegisterView(APIView): # POST /api/users/register/ 
    def post(self, request):
        pass

class LoginView(APIView):           # POST /api/users/login/
    def post(self, request):
        pass

class ProfileView(RetrieveUpdateAPIView):  # GET/PUT /api/users/profile/
    pass

