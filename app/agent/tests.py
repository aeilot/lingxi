from django.test import TestCase, Client
from django.urls import reverse
from agent.models import ChatSession, ChatInformation, AgentConfiguration
from agent.core import generate_session_summary, DecisionModule
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
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


class DecisionModuleTestCase(TestCase):
    """Test cases for the DecisionModule feature"""
    
    def setUp(self):
        """Set up test data"""
        self.agent_config = AgentConfiguration.objects.create(
            name="test",
            parameters={"model": "gpt-3.5-turbo", "personality_prompt": ""},
            timings={"inactivity_check_minutes": 5}
        )
        self.session = ChatSession.objects.create(
            agent_configuration=self.agent_config
        )
    
    def test_decision_module_wait_when_not_inactive(self):
        """Test that DecisionModule returns 'wait' when session is not inactive enough"""
        # Set last activity to just 2 minutes ago
        past_time = timezone.now() - timedelta(minutes=2)
        self.session.last_activity_at = past_time
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        decision = DecisionModule(self.session, self.agent_config)
        
        self.assertEqual(decision['action'], 'wait')
        self.assertIn('threshold', decision['reason'].lower())
    
    def test_decision_module_wait_when_no_activity(self):
        """Test that DecisionModule returns 'wait' when no activity recorded"""
        self.session.last_activity_at = None
        self.session.save()
        
        decision = DecisionModule(self.session, self.agent_config)
        
        self.assertEqual(decision['action'], 'wait')
        self.assertIn('no activity', decision['reason'].lower())
    
    def test_decision_module_without_api_key_short_conversation(self):
        """Test DecisionModule fallback behavior with short conversation"""
        # Set last activity to 10 minutes ago
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 3
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        decision = DecisionModule(self.session, self.agent_config, api_key=None)
        
        self.assertEqual(decision['action'], 'wait')
        self.assertIn('too short', decision['reason'].lower())
    
    def test_decision_module_without_api_key_long_conversation(self):
        """Test DecisionModule fallback behavior with longer conversation"""
        # Set last activity to 10 minutes ago
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 10
        self.session.summary = "Discussion about Python programming"
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        decision = DecisionModule(self.session, self.agent_config, api_key=None)
        
        self.assertEqual(decision['action'], 'continue')
        self.assertIsNotNone(decision['suggested_message'])
    
    def test_decision_module_with_mocked_api(self):
        """Test DecisionModule with mocked OpenAI API"""
        # Set last activity to 10 minutes ago
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 8
        self.session.summary = "Discussion about machine learning"
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        # Add some chat messages
        for i in range(4):
            user_msg = ChatInformation.objects.create(
                message=f"User question {i}",
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
        
        # Mock the OpenAI API call
        with patch('agent.core.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock the API response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"action": "continue", "reason": "Natural follow-up opportunity", "suggested_message": "Would you like to explore this topic further?"}'
            mock_client.chat.completions.create.return_value = mock_response
            
            decision = DecisionModule(
                self.session, 
                self.agent_config, 
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            self.assertEqual(decision['action'], 'continue')
            self.assertEqual(decision['reason'], 'Natural follow-up opportunity')
            self.assertIsNotNone(decision['suggested_message'])
    
    def test_check_session_inactivity_endpoint(self):
        """Test the check_session_inactivity API endpoint"""
        # Set last activity to 10 minutes ago (save first, then update with raw SQL to bypass auto_now)
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 10
        self.session.save()
        
        # Update directly using QuerySet update to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        
        response = self.client.get(f'/api/sessions/{self.session.id}/inactivity')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('action', data)
        self.assertIn('reason', data)
        self.assertIn('minutes_inactive', data)
        # Should be around 10 minutes (allow some variance for test execution time)
        self.assertGreater(data['minutes_inactive'], 9)
    
    def test_get_session_summary_endpoint(self):
        """Test the get_session_summary API endpoint"""
        self.session.summary = "Test summary text"
        self.session.message_count = 15
        self.session.save()
        
        response = self.client.get(f'/api/sessions/{self.session.id}/summary')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['summary'], "Test summary text")
        self.assertEqual(data['message_count'], 15)
    
    def test_last_activity_at_field_exists(self):
        """Test that ChatSession has last_activity_at field"""
        # Initially None for a new session
        self.assertIsNone(self.session.last_activity_at)
        
        # Test that it can be set manually
        now = timezone.now()
        self.session.last_activity_at = now
        self.session.save()
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.last_activity_at, now)
    
    def test_summary_update_response_includes_flag(self):
        """Test that handle_user_input response includes summary_updated flag"""
        # Add messages to get to 8 first
        for i in range(8):
            msg = ChatInformation.objects.create(
                message=f"Message {i}",
                is_user=(i % 2 == 0),
                is_agent=(i % 2 == 1)
            )
            self.session.chat_infos.add(msg)
        
        self.session.message_count = 8
        self.session.save()
        
        # Mock the summary generation
        with patch('agent.views.generate_session_summary') as mock_summary:
            mock_summary.return_value = "Generated summary"
            
            # This should trigger a summary update (message count 8 + 2 = 10)
            response = self.client.post('/handle_user_input', {
                'message': 'Test message',
                'session_id': self.session.id
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Check that summary_updated flag is present
            self.assertIn('summary_updated', data)
            self.assertTrue(data['summary_updated'])
            self.assertIn('summary', data)
            self.assertEqual(data['summary'], "Generated summary")


class SchedulerTestCase(TestCase):
    """Test cases for the scheduler module"""
    
    def setUp(self):
        """Set up test data"""
        self.agent_config = AgentConfiguration.objects.create(
            name="test",
            parameters={"model": "gpt-3.5-turbo", "personality_prompt": ""}
        )
        self.session = ChatSession.objects.create(
            agent_configuration=self.agent_config
        )
    
    def test_scheduler_module_imports(self):
        """Test that scheduler module can be imported"""
        from agent.scheduler import start_scheduler, stop_scheduler, check_all_sessions_inactivity
        self.assertIsNotNone(start_scheduler)
        self.assertIsNotNone(stop_scheduler)
        self.assertIsNotNone(check_all_sessions_inactivity)
    
    @patch('agent.core.DecisionModule')
    def test_check_all_sessions_inactivity(self, mock_decision):
        """Test that check_all_sessions_inactivity processes sessions correctly"""
        from agent.scheduler import check_all_sessions_inactivity
        
        # Set up a session with activity 10 minutes ago
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.save()
        
        # Mock the DecisionModule to return a decision
        mock_decision.return_value = {
            'action': 'send_message',
            'reason': 'User has been inactive',
            'suggested_message': 'Are you still there?'
        }
        
        # Run the check
        check_all_sessions_inactivity()
        
        # Verify DecisionModule was called for the inactive session
        self.assertTrue(mock_decision.called)
    
    def test_scheduler_start_stop(self):
        """Test that scheduler can be started and stopped"""
        from agent.scheduler import start_scheduler, stop_scheduler, scheduler
        
        # Start the scheduler
        start_scheduler()
        
        # Verify scheduler is running
        from agent import scheduler as scheduler_module
        self.assertIsNotNone(scheduler_module.scheduler)
        
        # Stop the scheduler
        stop_scheduler()
        
        # Verify scheduler is stopped
        self.assertIsNone(scheduler_module.scheduler)

