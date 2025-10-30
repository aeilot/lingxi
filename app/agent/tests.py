from django.test import TestCase, Client
from django.urls import reverse
from agent.models import ChatSession, ChatInformation, AgentConfiguration
from agent.core import generate_session_summary
from unittest.mock import patch, MagicMock
import json


class ChatSessionSummaryTestCase(TestCase):
    """Test cases for the session summary feature"""
    
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
    
    def test_session_model_has_summary_field(self):
        """Test that ChatSession model has summary field"""
        self.assertIsNone(self.session.summary)
        self.session.summary = "Test summary"
        self.session.save()
        self.assertEqual(self.session.summary, "Test summary")
    
    def test_session_model_has_message_count_field(self):
        """Test that ChatSession model has message_count field"""
        self.assertEqual(self.session.message_count, 0)
        self.session.message_count = 5
        self.session.save()
        self.assertEqual(self.session.message_count, 5)
    
    def test_message_count_updates_on_new_message(self):
        """Test that message_count is updated when messages are added via API"""
        # Add a message through the handle_user_input endpoint
        response = self.client.post('/handle_user_input', {
            'message': 'Test message',
            'session_id': self.session.id
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh session from database
        self.session.refresh_from_db()
        
        # Should have 2 messages (user + AI response)
        self.assertEqual(self.session.message_count, 2)
    
    def test_summary_generated_at_10_messages(self):
        """Test that summary is generated when message count reaches 10"""
        # Add 9 messages first
        for i in range(1, 5):
            user_msg = ChatInformation.objects.create(
                message=f"User message {i}",
                is_user=True,
                is_agent=False
            )
            self.session.chat_infos.add(user_msg)
            
            ai_msg = ChatInformation.objects.create(
                message=f"AI response {i}",
                is_user=False,
                is_agent=True
            )
            self.session.chat_infos.add(ai_msg)
        
        self.session.message_count = 8
        self.session.save()
        
        # Summary should be None before 10 messages
        self.assertIsNone(self.session.summary)
        
        # Add 10th message through API
        with patch('agent.views.generate_session_summary') as mock_summary:
            mock_summary.return_value = "Generated summary"
            
            response = self.client.post('/handle_user_input', {
                'message': 'Test message 10',
                'session_id': self.session.id
            })
            
            self.assertEqual(response.status_code, 200)
            
            # Refresh session
            self.session.refresh_from_db()
            
            # Summary should be generated at 10 messages
            self.assertEqual(self.session.message_count, 10)
            self.assertIsNotNone(self.session.summary)
    
    def test_generate_session_summary_without_api_key(self):
        """Test summary generation fallback when no API key is provided"""
        # Add some messages
        user_msg = ChatInformation.objects.create(
            message="Hello, I want to learn Python programming",
            is_user=True,
            is_agent=False
        )
        self.session.chat_infos.add(user_msg)
        
        ai_msg = ChatInformation.objects.create(
            message="Sure! Python is great.",
            is_user=False,
            is_agent=True
        )
        self.session.chat_infos.add(ai_msg)
        
        # Generate summary without API key
        summary = generate_session_summary(
            self.session,
            self.agent_config,
            api_key=None
        )
        
        # Should return a truncated version of first user message
        self.assertIsNotNone(summary)
        self.assertIn("Python", summary)
    
    def test_list_sessions_returns_summary(self):
        """Test that list_sessions API returns summary instead of last_message"""
        # Set a summary
        self.session.summary = "Test session summary"
        self.session.message_count = 5
        self.session.save()
        
        # Add a message
        msg = ChatInformation.objects.create(
            message="This is the last message in the session",
            is_user=True,
            is_agent=False
        )
        self.session.chat_infos.add(msg)
        
        # Call list_sessions API
        response = self.client.get('/api/sessions/list')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        sessions = data['sessions']
        
        self.assertEqual(len(sessions), 1)
        # Should return summary, not last_message
        self.assertEqual(sessions[0]['summary'], "Test session summary")
        self.assertNotIn('last_message', sessions[0])
    
    def test_list_sessions_fallback_to_last_message(self):
        """Test that list_sessions falls back to last message if no summary"""
        # Don't set a summary
        msg = ChatInformation.objects.create(
            message="This is the only message",
            is_user=True,
            is_agent=False
        )
        self.session.chat_infos.add(msg)
        
        # Call list_sessions API
        response = self.client.get('/api/sessions/list')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        sessions = data['sessions']
        
        self.assertEqual(len(sessions), 1)
        # Should fall back to last message when no summary
        self.assertEqual(sessions[0]['summary'], "This is the only message")
    
    def test_summary_updates_every_10_messages(self):
        """Test that summary is updated at 10, 20, 30 messages etc."""
        with patch('agent.views.generate_session_summary') as mock_summary:
            mock_summary.return_value = "Updated summary"
            
            # Add messages to reach 8 manually
            for i in range(8):
                msg = ChatInformation.objects.create(
                    message=f"Message {i}",
                    is_user=(i % 2 == 0),
                    is_agent=(i % 2 == 1)
                )
                self.session.chat_infos.add(msg)
            
            self.session.message_count = 8
            self.session.save()
            
            # Add 9th message via API - should not trigger summary
            # (API adds 2 messages: user + AI response, so count becomes 10)
            response = self.client.post('/handle_user_input', {
                'message': 'Message 9',
                'session_id': self.session.id
            })
            
            self.session.refresh_from_db()
            # Should have 10 messages now and summary should be generated
            self.assertEqual(self.session.message_count, 10)
            self.assertIsNotNone(self.session.summary)
            self.assertEqual(self.session.summary, "Updated summary")
