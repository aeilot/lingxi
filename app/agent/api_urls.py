from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from agent import api_views

router = DefaultRouter()
router.register(r'agents', api_views.AgentConfigurationViewSet, basename='agent')
router.register(r'sessions', api_views.ChatSessionViewSet, basename='session')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Chat endpoints
    path('chat/', api_views.chat, name='api_chat'),
    path('chat/history/', api_views.chat_history, name='api_chat_history'),
    
    # Include router URLs
    path('', include(router.urls)),
]
