
import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from django.urls import resolve

# Try to find the view for the token endpoint
try:
    match = resolve('/api/auth/token/')
    print(f"DEBUG: Endpoint resolves to: {match.func.view_class}")
    
    # Create a request
    factory = APIRequestFactory()
    data = {'username': 'ibrahim', 'password': '123456'} # Using known credentials
    request = factory.post('/api/auth/token/', data, format='json')
    
    # Execute view
    view = match.func
    response = view(request)
    
    print(f"DEBUG: Status Code: {response.status_code}")
    if response.status_code == 500:
        print("DEBUG: Hit 500 Error. Unfortunately, this manual invocation might catch it differently.")
        # But normally the view handles exceptions.
        # Let's try invoke the serializer manually if it's TokenObtainPairView
        from rest_framework_simplejwt.views import TokenObtainPairView
        if issubclass(match.func.view_class, TokenObtainPairView):
             print("DEBUG: Inspecting Serializer...")
             serializer_class = match.func.view_class.serializer_class
             print(f"DEBUG: Serializer Class: {serializer_class}")
             serializer = serializer_class(data=data)
             try:
                 serializer.is_valid(raise_exception=True)
                 print("DEBUG: Serializer Valid. Token:", serializer.validated_data)
             except Exception as e:
                 import traceback
                 traceback.print_exc()

except Exception as e:
    print("DEBUG: Crash during diagnosis:")
    import traceback
    traceback.print_exc()
