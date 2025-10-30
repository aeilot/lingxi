"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from agent import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.chat_ui, name='chat_ui'),
    path('handle_user_input', views.handle_user_input, name='handle_user_input'),
    path('api/sessions/create', views.create_session, name='create_session'),
    path('api/sessions/list', views.list_sessions, name='list_sessions'),
    path('api/sessions/<int:session_id>/history', views.get_session_history, name='get_session_history'),
    path('api/sessions/<int:session_id>/delete', views.delete_session, name='delete_session'),
    path('api/sessions/<int:session_id>/inactivity', views.check_session_inactivity, name='check_session_inactivity'),
    path('api/sessions/<int:session_id>/summary', views.get_session_summary, name='get_session_summary'),
    path('api/sessions/<int:session_id>/personality-suggestion', views.check_personality_update_suggestion, name='check_personality_update_suggestion'),
    path('api/sessions/<int:session_id>/personality-update', views.apply_personality_update, name='apply_personality_update'),
    path('api/sessions/<int:session_id>/personality-dismiss', views.dismiss_personality_suggestion, name='dismiss_personality_suggestion'),
    path('api/sessions/<int:session_id>/new-messages', views.check_new_messages, name='check_new_messages'),
    path('api/sessions/<int:session_id>/acknowledge-messages', views.acknowledge_new_messages, name='acknowledge_new_messages'),
    path('api/personality/update', views.update_personality_prompt, name='update_personality_prompt'),
    path('api/personality/get', views.get_personality_prompt, name='get_personality_prompt'),
]
