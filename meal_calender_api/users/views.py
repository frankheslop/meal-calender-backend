from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Import your serializers (we will define these in the next step)
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate an auth token automatically upon registration
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {"token": token.key, "user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]

            # Try direct username authentication first.
            user = authenticate(username=username, password=password)

            # If direct auth fails and input looks like an email, try email lookup.
            if user is None and "@" in username:
                candidate = User.objects.filter(email__iexact=username).only("username").first()
                if candidate:
                    user = authenticate(username=candidate.username, password=password)

            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response(
                    {"token": token.key, "user": UserSerializer(user).data},
                    status=status.HTTP_200_OK,
                )
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(RetrieveUpdateAPIView):
    # Requires a valid Auth token header
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    # Overridden to return the logged-in user instead of looking up a PK in the URL
    def get_object(self):
        return self.request.user
