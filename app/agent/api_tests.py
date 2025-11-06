from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from agent.models import AgentConfiguration, ChatSession, ChatInformation
import json


class AuthenticationTestCase(TestCase):
    """Test cases for authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_login_success(self):
        """Test successful login returns JWT tokens"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials fails"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token(self):
        """Test token refresh endpoint"""
        # First login to get tokens
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        refresh_token = login_response.data['refresh']
        
        # Try to refresh
        response = self.client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class AgentAPITestCase(TestCase):
    """Test cases for agent management API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_agent(self):
        """Test creating a new agent"""
        response = self.client.post('/api/agents/', {
            'name': 'my-agent',
            'parameters': {
                'model': 'gpt-4',
                'personality_prompt': 'You are helpful'
            }
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'my-agent')
        self.assertEqual(response.data['parameters']['model'], 'gpt-4')
        
        # Verify agent is owned by the user
        agent = AgentConfiguration.objects.get(id=response.data['id'])
        self.assertEqual(agent.user, self.user)
    
    def test_list_agents(self):
        """Test listing agents for authenticated user"""
        # Create agents
        AgentConfiguration.objects.create(
            name='agent1',
            user=self.user,
            parameters={'model': 'gpt-3.5-turbo'}
        )
        AgentConfiguration.objects.create(
            name='agent2',
            user=self.user,
            parameters={'model': 'gpt-4'}
        )
        
        # Create agent for another user
        other_user = User.objects.create_user(username='other', password='pass')
        AgentConfiguration.objects.create(
            name='other-agent',
            user=other_user,
            parameters={'model': 'gpt-3.5-turbo'}
        )
        
        response = self.client.get('/api/agents/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_update_agent_personality(self):
        """Test updating agent personality"""
        agent = AgentConfiguration.objects.create(
            name='test-agent',
            user=self.user,
            parameters={'model': 'gpt-3.5-turbo', 'personality_prompt': 'old'}
        )
        
        response = self.client.put(f'/api/agents/{agent.id}/personality/', {
            'personality_prompt': 'New personality prompt'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify update
        agent.refresh_from_db()
        self.assertEqual(agent.parameters['personality_prompt'], 'New personality prompt')
    
    def test_cannot_access_other_user_agent(self):
        """Test that users cannot access other users' agents"""
        other_user = User.objects.create_user(username='other', password='pass')
        other_agent = AgentConfiguration.objects.create(
            name='other-agent',
            user=other_user,
            parameters={'model': 'gpt-3.5-turbo'}
        )
        
        response = self.client.get(f'/api/agents/{other_agent.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ChatAPITestCase(TestCase):
    """Test cases for chat API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.agent = AgentConfiguration.objects.create(
            name='test-agent',
            user=self.user,
            parameters={'model': 'gpt-3.5-turbo', 'personality_prompt': ''}
        )
    
    def test_chat_without_api_key(self):
        """Test chat endpoint creates session and uses fallback response"""
        response = self.client.post('/api/chat/', {
            'message': 'Hello',
            'agent_id': self.agent.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', response.data)
        self.assertIn('response', response.data)
        self.assertIn('Simulated response', response.data['response'])
        
        # Verify session was created
        session = ChatSession.objects.get(id=response.data['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.agent_configuration, self.agent)
    
    def test_chat_continues_existing_session(self):
        """Test chat endpoint can continue an existing session"""
        # Create a session
        session = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        
        response = self.client.post('/api/chat/', {
            'message': 'Hello again',
            'session_id': session.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_id'], session.id)
        
        # Verify messages were added
        session.refresh_from_db()
        self.assertEqual(session.message_count, 2)  # User + AI
    
    def test_chat_uses_default_agent_if_not_specified(self):
        """Test chat endpoint uses default agent if none specified"""
        response = self.client.post('/api/chat/', {
            'message': 'Hello'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', response.data)
        
        # Verify default agent was created
        default_agent = AgentConfiguration.objects.get(name='default', user=self.user)
        self.assertIsNotNone(default_agent)
    
    def test_chat_history(self):
        """Test chat history endpoint"""
        # Create sessions with messages
        session1 = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        msg1 = ChatInformation.objects.create(
            message='Message 1',
            is_user=True,
            is_agent=False
        )
        session1.chat_infos.add(msg1)
        
        session2 = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        msg2 = ChatInformation.objects.create(
            message='Message 2',
            is_user=True,
            is_agent=False
        )
        session2.chat_infos.add(msg2)
        
        response = self.client.get('/api/chat/history/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['sessions']), 2)
    
    def test_chat_history_filtered_by_session(self):
        """Test chat history filtered by session ID"""
        session = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        
        response = self.client.get(f'/api/chat/history/?session_id={session.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['sessions']), 1)
        self.assertEqual(response.data['sessions'][0]['id'], session.id)
    
    def test_cannot_access_other_user_session(self):
        """Test that users cannot access other users' sessions"""
        other_user = User.objects.create_user(username='other', password='pass')
        other_agent = AgentConfiguration.objects.create(
            name='agent',
            user=other_user,
            parameters={'model': 'gpt-3.5-turbo'}
        )
        other_session = ChatSession.objects.create(
            user=other_user,
            agent_configuration=other_agent
        )
        
        # Try to chat in other user's session
        response = self.client.post('/api/chat/', {
            'message': 'Hello',
            'session_id': other_session.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SessionAPITestCase(TestCase):
    """Test cases for session management API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.agent = AgentConfiguration.objects.create(
            name='test-agent',
            user=self.user,
            parameters={'model': 'gpt-3.5-turbo'}
        )
    
    def test_create_session(self):
        """Test creating a new session"""
        response = self.client.post('/api/sessions/', {
            'agent_configuration': self.agent.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['agent_name'], 'test-agent')
        
        # Verify session is owned by user
        session = ChatSession.objects.get(id=response.data['id'])
        self.assertEqual(session.user, self.user)
    
    def test_list_sessions(self):
        """Test listing sessions"""
        ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        
        response = self.client.get('/api/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_session_with_messages(self):
        """Test getting a session with full message history"""
        session = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        
        # Add messages
        for i in range(3):
            msg = ChatInformation.objects.create(
                message=f'Message {i}',
                is_user=(i % 2 == 0),
                is_agent=(i % 2 == 1)
            )
            session.chat_infos.add(msg)
        
        response = self.client.get(f'/api/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 3)
    
    def test_delete_session(self):
        """Test deleting a session"""
        session = ChatSession.objects.create(
            user=self.user,
            agent_configuration=self.agent
        )
        
        response = self.client.delete(f'/api/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatSession.objects.filter(id=session.id).exists())


class UnauthenticatedAccessTestCase(TestCase):
    """Test that API endpoints require authentication"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_agents_require_auth(self):
        """Test that agent endpoints require authentication"""
        response = self.client.get('/api/agents/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_sessions_require_auth(self):
        """Test that session endpoints require authentication"""
        response = self.client.get('/api/sessions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_chat_requires_auth(self):
        """Test that chat endpoint requires authentication"""
        response = self.client.post('/api/chat/', {'message': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_chat_history_requires_auth(self):
        """Test that chat history endpoint requires authentication"""
        response = self.client.get('/api/chat/history/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
