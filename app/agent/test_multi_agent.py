from django.test import TestCase, Client
from django.urls import reverse
from agent.models import ChatSession, ChatInformation, AgentConfiguration, Agent
from agent.core import generate_multi_agent_responses
from unittest.mock import patch, MagicMock
from django.utils import timezone
import json


class MultiAgentTestCase(TestCase):
    """Test cases for multi-agent functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.agent_config = AgentConfiguration.objects.create(
            name="test",
            parameters={"model": "gpt-3.5-turbo", "personality_prompt": ""}
        )
        self.session = ChatSession.objects.create(
            agent_configuration=self.agent_config
        )
        
        # Create test agents
        self.alice = Agent.objects.create(
            name="Alice",
            personality_prompt="You are Alice, friendly and helpful.",
            avatar_emoji="😊",
            color="#FF6B9D",
            is_active=True
        )
        
        self.bob = Agent.objects.create(
            name="Bob",
            personality_prompt="You are Bob, professional and knowledgeable.",
            avatar_emoji="🧠",
            color="#4A90E2",
            is_active=True
        )
        
        # Add agents to session
        self.session.agents.add(self.alice, self.bob)
    
    def test_agent_model_creation(self):
        """Test that Agent model can be created with all fields"""
        agent = Agent.objects.create(
            name="Test Agent",
            personality_prompt="Test personality",
            avatar_emoji="🤖",
            color="#FF0000",
            is_active=True
        )
        self.assertEqual(agent.name, "Test Agent")
        self.assertEqual(agent.avatar_emoji, "🤖")
        self.assertEqual(agent.color, "#FF0000")
        self.assertTrue(agent.is_active)
    
    def test_chat_information_has_agent_field(self):
        """Test that ChatInformation has agent field"""
        msg = ChatInformation.objects.create(
            message="Test message",
            is_user=False,
            is_agent=True,
            agent=self.alice
        )
        self.assertEqual(msg.agent, self.alice)
        self.assertEqual(msg.agent.name, "Alice")
    
    def test_session_has_agents_field(self):
        """Test that ChatSession has agents many-to-many field"""
        self.assertEqual(self.session.agents.count(), 2)
        self.assertIn(self.alice, self.session.agents.all())
        self.assertIn(self.bob, self.session.agents.all())
    
    def test_generate_multi_agent_responses_returns_list(self):
        """Test that generate_multi_agent_responses returns a list of responses"""
        responses = generate_multi_agent_responses(
            "Hello",
            self.agent_config,
            self.session,
            api_key=None  # Will use simulated responses
        )
        
        self.assertIsInstance(responses, list)
        self.assertGreater(len(responses), 0)
        
        # Check structure of responses
        for response in responses:
            self.assertIn("agent", response)
            self.assertIn("response", response)
            self.assertIsInstance(response["agent"], Agent)
    
    def test_multi_agent_response_includes_agent_info(self):
        """Test that multi-agent responses include agent information"""
        response = self.client.post('/handle_user_input', {
            'message': 'Hello agents!',
            'session_id': self.session.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Check that messages array is present
        self.assertIn('messages', data)
        self.assertIsInstance(data['messages'], list)
        
        # Check that each message has agent info
        for msg in data['messages']:
            self.assertIn('agent_id', msg)
            self.assertIn('agent_name', msg)
            self.assertIn('agent_emoji', msg)
            self.assertIn('agent_color', msg)
            self.assertIn('message', msg)
    
    def test_session_auto_assigns_agents_on_creation(self):
        """Test that new sessions automatically get agents assigned"""
        # Create a new session without explicitly setting agents
        response = self.client.post('/handle_user_input', {
            'message': 'First message'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Get the session
        session = ChatSession.objects.get(id=data['session_id'])
        
        # Should have agents assigned
        self.assertGreater(session.agents.count(), 0)
    
    def test_get_session_history_includes_agent_info(self):
        """Test that session history includes agent information"""
        # Create a message with agent
        msg = ChatInformation.objects.create(
            message="Test from Alice",
            is_user=False,
            is_agent=True,
            agent=self.alice
        )
        self.session.chat_infos.add(msg)
        
        # Get session history
        response = self.client.get(f'/api/sessions/{self.session.id}/history')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('messages', data)
        
        # Find our message
        our_msg = next((m for m in data['messages'] if m['id'] == msg.id), None)
        self.assertIsNotNone(our_msg)
        
        # Check agent info is present
        self.assertEqual(our_msg['agent_name'], 'Alice')
        self.assertEqual(our_msg['agent_emoji'], '😊')
        self.assertEqual(our_msg['agent_color'], '#FF6B9D')
    
    def test_list_agents_endpoint(self):
        """Test the list_agents API endpoint"""
        response = self.client.get('/api/agents/list')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('agents', data)
        self.assertIsInstance(data['agents'], list)
        
        # Should have at least our test agents
        agent_names = [a['name'] for a in data['agents']]
        self.assertIn('Alice', agent_names)
        self.assertIn('Bob', agent_names)
    
    def test_get_agent_endpoint(self):
        """Test the get_agent API endpoint"""
        response = self.client.get(f'/api/agents/{self.alice.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'Alice')
        self.assertEqual(data['avatar_emoji'], '😊')
        self.assertEqual(data['color'], '#FF6B9D')
    
    def test_update_agent_endpoint(self):
        """Test the update_agent API endpoint"""
        response = self.client.post(f'/api/agents/{self.alice.id}/update', {
            'personality_prompt': 'Updated personality'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify the agent was updated
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.personality_prompt, 'Updated personality')
    
    def test_update_session_agents_endpoint(self):
        """Test the update_session_agents API endpoint"""
        # Create a third agent
        charlie = Agent.objects.create(
            name="Charlie",
            personality_prompt="Creative agent",
            avatar_emoji="🎨",
            color="#FFA500",
            is_active=True
        )
        
        # Update session to only have Charlie
        response = self.client.post(f'/api/sessions/{self.session.id}/agents', {
            'agent_ids': str(charlie.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify session agents were updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.agents.count(), 1)
        self.assertEqual(self.session.agents.first(), charlie)
    
    def test_inactive_agents_not_used(self):
        """Test that inactive agents are not used in responses"""
        # Deactivate all agents
        Agent.objects.filter(id__in=[self.alice.id, self.bob.id]).update(is_active=False)
        
        # Try to generate responses
        responses = generate_multi_agent_responses(
            "Test",
            self.agent_config,
            self.session,
            api_key=None
        )
        
        # Should return empty list since no active agents
        self.assertEqual(len(responses), 0)
    
    def test_default_agents_created(self):
        """Test that default agents were created by migration"""
        alice = Agent.objects.filter(name="Alice").first()
        bob = Agent.objects.filter(name="Bob").first()
        charlie = Agent.objects.filter(name="Charlie").first()
        
        self.assertIsNotNone(alice)
        self.assertIsNotNone(bob)
        self.assertIsNotNone(charlie)
        
        self.assertEqual(alice.avatar_emoji, "😊")
        self.assertEqual(bob.avatar_emoji, "🧠")
        self.assertEqual(charlie.avatar_emoji, "🎨")
