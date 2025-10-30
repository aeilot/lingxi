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
                is_agent=True,
                is_read=True  # Mark as read so DecisionModule can proceed
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


class PersonalityUpdateTestCase(TestCase):
    """Test cases for the personality update feature"""
    
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
    
    def test_decide_personality_update_insufficient_messages(self):
        """Test that personality update is not suggested with insufficient messages"""
        from agent.core import decide_personality_update
        
        self.session.message_count = 10
        self.session.save()
        
        decision = decide_personality_update(self.session, self.agent_config)
        
        self.assertFalse(decision['should_update'])
        self.assertIn('not enough', decision['reason'].lower())
        self.assertEqual(decision['confidence'], 0.0)
    
    def test_decide_personality_update_sufficient_messages_no_api(self):
        """Test personality update decision with sufficient messages but no API"""
        from agent.core import decide_personality_update
        
        self.session.message_count = 50
        self.session.save()
        
        decision = decide_personality_update(self.session, self.agent_config, api_key=None)
        
        # Should suggest update at 50 messages with empty personality
        self.assertTrue(decision['should_update'])
        self.assertIsNotNone(decision['suggested_personality'])
    
    def test_decide_personality_update_with_mocked_api(self):
        """Test personality update decision with mocked OpenAI API"""
        from agent.core import decide_personality_update
        from unittest.mock import patch, MagicMock
        
        self.session.message_count = 30
        self.session.summary = "Discussion about Python programming"
        self.session.save()
        
        # Add some chat messages
        for i in range(15):
            user_msg = ChatInformation.objects.create(
                message=f"User question about Python {i}",
                is_user=True,
                is_agent=False
            )
            self.session.chat_infos.add(user_msg)
            
            ai_msg = ChatInformation.objects.create(
                message=f"AI response about Python {i}",
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
            mock_response.choices[0].message.content = '''{"should_update": true, "reason": "User prefers detailed technical explanations", "suggested_personality": "You are a knowledgeable Python programming assistant who provides detailed technical explanations with code examples.", "confidence": 0.85}'''
            mock_client.chat.completions.create.return_value = mock_response
            
            decision = decide_personality_update(
                self.session,
                self.agent_config,
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            self.assertTrue(decision['should_update'])
            self.assertIn('Python', decision['suggested_personality'])
            self.assertEqual(decision['confidence'], 0.85)
    
    def test_check_personality_suggestion_endpoint_no_suggestion(self):
        """Test the check_personality_update_suggestion endpoint with no suggestion"""
        response = self.client.get(f'/api/sessions/{self.session.id}/personality-suggestion')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['has_suggestion'])
        self.assertIsNone(data['suggestion'])
    
    def test_check_personality_suggestion_endpoint_with_suggestion(self):
        """Test the check_personality_update_suggestion endpoint with a suggestion"""
        # Add a suggestion to the session state
        self.session.current_state = {
            'personality_update_suggestion': {
                'should_update': True,
                'reason': 'Test reason',
                'suggested_personality': 'Test personality',
                'confidence': 0.8
            }
        }
        self.session.save()
        
        response = self.client.get(f'/api/sessions/{self.session.id}/personality-suggestion')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['has_suggestion'])
        self.assertIsNotNone(data['suggestion'])
        self.assertEqual(data['suggestion']['suggested_personality'], 'Test personality')
    
    def test_apply_personality_update_endpoint(self):
        """Test applying a personality update"""
        # Add a suggestion to the session state
        self.session.current_state = {
            'personality_update_suggestion': {
                'should_update': True,
                'reason': 'Test reason',
                'suggested_personality': 'New test personality',
                'confidence': 0.8
            }
        }
        self.session.save()
        
        # Apply the update
        response = self.client.post(f'/api/sessions/{self.session.id}/personality-update')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['personality_prompt'], 'New test personality')
        
        # Verify the agent config was updated
        self.agent_config.refresh_from_db()
        self.assertEqual(self.agent_config.parameters['personality_prompt'], 'New test personality')
        
        # Verify the suggestion was cleared
        self.session.refresh_from_db()
        self.assertNotIn('personality_update_suggestion', self.session.current_state)
    
    def test_dismiss_personality_suggestion_endpoint(self):
        """Test dismissing a personality suggestion"""
        # Add a suggestion to the session state
        self.session.current_state = {
            'personality_update_suggestion': {
                'should_update': True,
                'reason': 'Test reason',
                'suggested_personality': 'Test personality',
                'confidence': 0.8
            }
        }
        self.session.save()
        
        # Dismiss the suggestion
        response = self.client.post(f'/api/sessions/{self.session.id}/personality-dismiss')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify the suggestion was cleared
        self.session.refresh_from_db()
        self.assertNotIn('personality_update_suggestion', self.session.current_state)
    
    def test_celery_tasks_can_be_imported(self):
        """Test that Celery tasks can be imported"""
        from agent.tasks import check_all_sessions_inactivity_task, check_personality_updates_task
        self.assertIsNotNone(check_all_sessions_inactivity_task)
        self.assertIsNotNone(check_personality_updates_task)
    
    def test_personality_update_every_20_messages(self):
        """Test that personality update is checked every 20 messages"""
        from unittest.mock import patch, MagicMock
        
        # Use "default" agent config since that's what the view uses
        agent_config = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": "gpt-3.5-turbo", "personality_prompt": ""}}
        )[0]
        
        session = ChatSession.objects.create(agent_configuration=agent_config)
        
        # Add messages to reach 18
        for i in range(18):
            msg = ChatInformation.objects.create(
                message=f"Message {i}",
                is_user=(i % 2 == 0),
                is_agent=(i % 2 == 1)
            )
            session.chat_infos.add(msg)
        
        session.message_count = 18
        session.save()
        
        # Mock the decide_personality_update to return a suggestion with high confidence
        with patch('agent.views.decide_personality_update') as mock_decide:
            mock_decide.return_value = {
                'should_update': True,
                'reason': 'Test reason',
                'suggested_personality': 'Auto-applied personality',
                'confidence': 0.85
            }
            
            # Add 20th message via API (will add 2 messages: user + AI = 20 total)
            response = self.client.post('/handle_user_input', {
                'message': 'Test message at 20',
                'session_id': session.id
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Verify personality was auto-updated due to high confidence
            self.assertTrue(data.get('personality_updated'))
            
            # Verify the agent config was updated
            agent_config.refresh_from_db()
            self.assertEqual(agent_config.parameters['personality_prompt'], 'Auto-applied personality')
    
    def test_personality_suggestion_low_confidence(self):
        """Test that personality update is suggested (not auto-applied) for low confidence"""
        from unittest.mock import patch, MagicMock
        
        # Use "default" agent config since that's what the view uses
        agent_config = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": "gpt-3.5-turbo", "personality_prompt": ""}}
        )[0]
        
        session = ChatSession.objects.create(agent_configuration=agent_config)
        
        # Add messages to reach 18
        for i in range(18):
            msg = ChatInformation.objects.create(
                message=f"Message {i}",
                is_user=(i % 2 == 0),
                is_agent=(i % 2 == 1)
            )
            session.chat_infos.add(msg)
        
        session.message_count = 18
        session.save()
        
        # Mock the decide_personality_update to return a suggestion with low confidence
        with patch('agent.views.decide_personality_update') as mock_decide:
            mock_decide.return_value = {
                'should_update': True,
                'reason': 'Test reason',
                'suggested_personality': 'Suggested personality',
                'confidence': 0.65  # Below threshold
            }
            
            # Add 20th message via API
            response = self.client.post('/handle_user_input', {
                'message': 'Test message at 20',
                'session_id': session.id
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Verify personality was not auto-updated
            self.assertFalse(data.get('personality_updated', False))
            # But suggestion is available
            self.assertTrue(data.get('personality_suggestion_available'))
            
            # Verify suggestion is stored in session state
            session.refresh_from_db()
            self.assertIn('personality_update_suggestion', session.current_state)


class ProactiveMessagingTestCase(TestCase):
    """Test cases for proactive messaging feature"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.agent_config = AgentConfiguration.objects.create(
            name="test",
            parameters={"model": "gpt-3.5-turbo", "personality_prompt": ""},
            timings={"inactivity_check_minutes": 5}
        )
        self.session = ChatSession.objects.create(
            agent_configuration=self.agent_config
        )
    
    def test_check_new_messages_endpoint_no_messages(self):
        """Test check_new_messages endpoint with no new messages"""
        response = self.client.get(f'/api/sessions/{self.session.id}/new-messages')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['has_new_messages'])
        self.assertEqual(len(data['new_messages']), 0)
    
    def test_check_new_messages_endpoint_with_messages(self):
        """Test check_new_messages endpoint with new messages"""
        # Add a proactive message to session state
        proactive_msg = ChatInformation.objects.create(
            message="Proactive message",
            is_user=False,
            is_agent=True,
            is_agent_growth=True
        )
        self.session.chat_infos.add(proactive_msg)
        
        self.session.current_state = {
            'proactive_messages': [{
                'message_id': proactive_msg.id,
                'timestamp': timezone.now().isoformat(),
                'action': 'continue',
                'reason': 'Test reason'
            }]
        }
        self.session.save()
        
        response = self.client.get(f'/api/sessions/{self.session.id}/new-messages')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['has_new_messages'])
        self.assertEqual(len(data['new_messages']), 1)
        self.assertEqual(data['new_messages'][0]['message'], "Proactive message")
    
    def test_acknowledge_messages_endpoint(self):
        """Test acknowledge_new_messages endpoint"""
        # Add proactive messages to session state
        self.session.current_state = {
            'proactive_messages': [{
                'message_id': 1,
                'timestamp': timezone.now().isoformat(),
                'action': 'continue',
                'reason': 'Test'
            }]
        }
        self.session.save()
        
        response = self.client.post(f'/api/sessions/{self.session.id}/acknowledge-messages')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify messages were cleared
        self.session.refresh_from_db()
        self.assertNotIn('proactive_messages', self.session.current_state)
    
    def test_inactivity_task_sends_message(self):
        """Test that check_all_sessions_inactivity_task actually sends messages"""
        from agent.tasks import check_all_sessions_inactivity_task
        from unittest.mock import patch, MagicMock
        
        # Set session as inactive for 10 minutes
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 10
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        # Mock the DecisionModule in agent.core
        with patch('agent.core.DecisionModule') as mock_decision:
            mock_decision.return_value = {
                'action': 'continue',
                'reason': 'Test reason',
                'suggested_message': 'Would you like to continue?'
            }
            
            # Run the task
            check_all_sessions_inactivity_task()
            
            # Verify a proactive message was created
            self.session.refresh_from_db()
            proactive_messages = self.session.chat_infos.filter(is_agent_growth=True)
            self.assertEqual(proactive_messages.count(), 1)
            self.assertEqual(proactive_messages.first().message, 'Would you like to continue?')
            
            # Verify session state was updated
            self.assertIn('proactive_messages', self.session.current_state)
            self.assertEqual(len(self.session.current_state['proactive_messages']), 1)


class SplitMessageTestCase(TestCase):
    """Test cases for the split message feature"""
    
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
    
    def test_generate_response_returns_dict_for_json_response(self):
        """Test that generate_response returns a dict when LLM returns JSON"""
        from agent.core import generate_response
        from unittest.mock import patch, MagicMock
        
        # Mock the OpenAI API call
        with patch('agent.core.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock the API response with JSON
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"messages": ["Hello!", "How can I help you today?", "Let me know what you need."]}'
            mock_client.chat.completions.create.return_value = mock_response
            
            result = generate_response(
                "Hi there",
                self.agent_config,
                self.session,
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            # Should return a dict
            self.assertIsInstance(result, dict)
            self.assertIn('messages', result)
            self.assertEqual(len(result['messages']), 3)
            self.assertEqual(result['messages'][0], "Hello!")
            self.assertEqual(result['messages'][1], "How can I help you today?")
    
    def test_generate_response_returns_string_for_plain_text(self):
        """Test that generate_response returns a string for plain text response"""
        from agent.core import generate_response
        from unittest.mock import patch, MagicMock
        
        # Mock the OpenAI API call
        with patch('agent.core.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock the API response with plain text
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "This is a regular response without JSON formatting."
            mock_client.chat.completions.create.return_value = mock_response
            
            result = generate_response(
                "What is Python?",
                self.agent_config,
                self.session,
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            # Should return a string
            self.assertIsInstance(result, str)
            self.assertIn("regular response", result)
    
    def test_generate_response_handles_invalid_json(self):
        """Test that generate_response falls back to string for invalid JSON"""
        from agent.core import generate_response
        from unittest.mock import patch, MagicMock
        
        # Mock the OpenAI API call
        with patch('agent.core.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock the API response with invalid JSON
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"messages": ["Missing closing bracket"'
            mock_client.chat.completions.create.return_value = mock_response
            
            result = generate_response(
                "Test",
                self.agent_config,
                self.session,
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            # Should return the raw string when JSON parsing fails
            self.assertIsInstance(result, str)
    
    def test_generate_response_strips_code_blocks(self):
        """Test that generate_response handles JSON wrapped in code blocks"""
        from agent.core import generate_response
        from unittest.mock import patch, MagicMock
        
        # Mock the OpenAI API call
        with patch('agent.core.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock the API response with JSON in code blocks
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '```json\n{"messages": ["First", "Second"]}\n```'
            mock_client.chat.completions.create.return_value = mock_response
            
            result = generate_response(
                "Test",
                self.agent_config,
                self.session,
                api_key="test-key",
                base_url="https://api.test.com"
            )
            
            # Should successfully parse the JSON despite code blocks
            self.assertIsInstance(result, dict)
            self.assertIn('messages', result)
            self.assertEqual(len(result['messages']), 2)
    
    def test_handle_user_input_with_split_messages(self):
        """Test that handle_user_input creates multiple ChatInformation objects for split messages"""
        from unittest.mock import patch
        
        # Mock generate_response to return split messages
        with patch('agent.views.generate_response') as mock_generate:
            mock_generate.return_value = {
                "messages": ["Message 1", "Message 2", "Message 3"]
            }
            
            response = self.client.post('/handle_user_input', {
                'message': 'Test split message',
                'session_id': self.session.id
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Check response contains messages array
            self.assertIn('messages', data)
            self.assertEqual(len(data['messages']), 3)
            self.assertEqual(data['messages'][0]['message'], "Message 1")
            self.assertEqual(data['messages'][1]['message'], "Message 2")
            self.assertEqual(data['messages'][2]['message'], "Message 3")
            
            # Verify all message IDs are present
            for msg in data['messages']:
                self.assertIn('id', msg)
                self.assertIsNotNone(msg['id'])
            
            # Refresh session and check message count
            self.session.refresh_from_db()
            # 1 user message + 3 AI messages = 4 total
            self.assertEqual(self.session.message_count, 4)
    
    def test_handle_user_input_with_single_message_backward_compatibility(self):
        """Test that handle_user_input maintains backward compatibility with single messages"""
        from unittest.mock import patch
        
        # Mock generate_response to return a plain string
        with patch('agent.views.generate_response') as mock_generate:
            mock_generate.return_value = "Single message response"
            
            response = self.client.post('/handle_user_input', {
                'message': 'Test single message',
                'session_id': self.session.id
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Check legacy format is maintained
            self.assertIn('response', data)
            self.assertEqual(data['response'], "Single message response")
            self.assertIn('ai_message_id', data)
            
            # messages array should not be present for single messages
            self.assertNotIn('messages', data)
    
    def test_split_messages_stored_separately_in_database(self):
        """Test that split messages are stored as separate ChatInformation objects"""
        from unittest.mock import patch
        
        # Mock generate_response to return split messages
        with patch('agent.views.generate_response') as mock_generate:
            mock_generate.return_value = {
                "messages": ["Part 1", "Part 2"]
            }
            
            # Count messages before
            messages_before = ChatInformation.objects.filter(is_agent=True).count()
            
            response = self.client.post('/handle_user_input', {
                'message': 'Test',
                'session_id': self.session.id
            })
            
            self.assertEqual(response.status_code, 200)
            
            # Count messages after
            messages_after = ChatInformation.objects.filter(is_agent=True).count()
            
            # Should have created 2 new AI messages
            self.assertEqual(messages_after - messages_before, 2)
            
            # Verify the messages are linked to the session
            ai_messages = self.session.chat_infos.filter(is_agent=True).order_by('chat_date')
            self.assertEqual(ai_messages.count(), 2)
            self.assertEqual(ai_messages[0].message, "Part 1")
            self.assertEqual(ai_messages[1].message, "Part 2")




class ReadIndicatorTestCase(TestCase):
    """Test cases for the read indicator (已读回执) feature"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.agent_config = AgentConfiguration.objects.create(
            name="test",
            parameters={"model": "gpt-3.5-turbo", "personality_prompt": ""},
            timings={"inactivity_check_minutes": 5}
        )
        self.session = ChatSession.objects.create(
            agent_configuration=self.agent_config
        )
    
    def test_chat_information_has_is_read_field(self):
        """Test that ChatInformation model has is_read field"""
        msg = ChatInformation.objects.create(
            message="Test message",
            is_user=False,
            is_agent=True
        )
        self.assertFalse(msg.is_read)  # Default should be False
        
        msg.is_read = True
        msg.save()
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
    
    def test_decision_module_waits_when_unread_messages_exist(self):
        """Test that DecisionModule returns 'wait' when there are unread AI messages"""
        from agent.core import DecisionModule
        
        # Set session as inactive for 10 minutes
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 10
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        # Add an unread AI message
        unread_msg = ChatInformation.objects.create(
            message="Unread AI message",
            is_user=False,
            is_agent=True,
            is_read=False
        )
        self.session.chat_infos.add(unread_msg)
        
        # DecisionModule should return 'wait' because of unread messages
        decision = DecisionModule(self.session, self.agent_config, api_key=None)
        
        self.assertEqual(decision['action'], 'wait')
        self.assertIn('unread', decision['reason'].lower())
        self.assertEqual(decision.get('unread_count'), 1)
    
    def test_decision_module_proceeds_when_all_messages_read(self):
        """Test that DecisionModule proceeds normally when all messages are read"""
        from agent.core import DecisionModule
        
        # Set session as inactive for 10 minutes
        past_time = timezone.now() - timedelta(minutes=10)
        self.session.last_activity_at = past_time
        self.session.message_count = 10
        self.session.save()
        
        # Update directly to avoid auto_now
        ChatSession.objects.filter(id=self.session.id).update(last_activity_at=past_time)
        self.session.refresh_from_db()
        
        # Add a read AI message
        read_msg = ChatInformation.objects.create(
            message="Read AI message",
            is_user=False,
            is_agent=True,
            is_read=True
        )
        self.session.chat_infos.add(read_msg)
        
        # DecisionModule should not wait due to unread messages
        decision = DecisionModule(self.session, self.agent_config, api_key=None)
        
        # Should return 'continue' based on fallback logic (not 'wait' due to unread)
        self.assertEqual(decision['action'], 'continue')
    
    def test_messages_marked_read_on_user_input(self):
        """Test that AI messages are marked as read when user sends a message"""
        # Add unread AI messages (these represent old messages)
        old_message_ids = []
        for i in range(3):
            msg = ChatInformation.objects.create(
                message=f"AI message {i}",
                is_user=False,
                is_agent=True,
                is_read=False
            )
            self.session.chat_infos.add(msg)
            old_message_ids.append(msg.id)
        
        # User sends a message (this will create a new AI response)
        response = self.client.post('/handle_user_input', {
            'message': 'User reply',
            'session_id': self.session.id
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Previous AI messages should be marked as read
        for msg_id in old_message_ids:
            msg = ChatInformation.objects.get(id=msg_id)
            self.assertTrue(msg.is_read, f"Old message {msg_id} should be marked as read")
        
        # The NEW AI response should be unread (it just arrived)
        new_ai_messages = self.session.chat_infos.filter(
            is_agent=True
        ).exclude(id__in=old_message_ids)
        self.assertTrue(new_ai_messages.exists(), "Should have a new AI response")
        for new_msg in new_ai_messages:
            self.assertFalse(new_msg.is_read, "New AI response should be unread")
    
    def test_messages_marked_read_on_session_history_load(self):
        """Test that AI messages are marked as read when session history is loaded"""
        # Add unread AI messages
        for i in range(3):
            msg = ChatInformation.objects.create(
                message=f"AI message {i}",
                is_user=False,
                is_agent=True,
                is_read=False
            )
            self.session.chat_infos.add(msg)
        
        # Load session history
        response = self.client.get(f'/api/sessions/{self.session.id}/history')
        self.assertEqual(response.status_code, 200)
        
        # All AI messages should be marked as read
        self.session.refresh_from_db()
        unread_count = self.session.chat_infos.filter(is_agent=True, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_messages_marked_read_on_acknowledge(self):
        """Test that AI messages are marked as read when acknowledged"""
        # Add unread AI messages
        for i in range(3):
            msg = ChatInformation.objects.create(
                message=f"AI message {i}",
                is_user=False,
                is_agent=True,
                is_read=False
            )
            self.session.chat_infos.add(msg)
        
        # Acknowledge messages
        response = self.client.post(f'/api/sessions/{self.session.id}/acknowledge-messages')
        self.assertEqual(response.status_code, 200)
        
        # All AI messages should be marked as read
        self.session.refresh_from_db()
        unread_count = self.session.chat_infos.filter(is_agent=True, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_check_new_messages_includes_read_status(self):
        """Test that check_new_messages endpoint returns read status"""
        # Create a proactive message
        proactive_msg = ChatInformation.objects.create(
            message="Proactive message",
            is_user=False,
            is_agent=True,
            is_agent_growth=True,
            is_read=False
        )
        self.session.chat_infos.add(proactive_msg)
        
        self.session.current_state = {
            'proactive_messages': [{
                'message_id': proactive_msg.id,
                'timestamp': timezone.now().isoformat(),
                'action': 'continue',
                'reason': 'Test'
            }]
        }
        self.session.save()
        
        # Check for new messages
        response = self.client.get(f'/api/sessions/{self.session.id}/new-messages')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['has_new_messages'])
        self.assertEqual(len(data['new_messages']), 1)
        self.assertIn('is_read', data['new_messages'][0])
        self.assertFalse(data['new_messages'][0]['is_read'])
