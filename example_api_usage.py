#!/usr/bin/env python
"""
Example Python script demonstrating how to use the Lingxi API.

This script shows:
1. User authentication with JWT tokens
2. Creating and managing AI agents
3. Sending chat messages
4. Retrieving chat history
5. Updating agent personality
"""

import requests
import json
from typing import Dict, Any


class LingxiClient:
    """Simple client for the Lingxi API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get JWT tokens"""
        response = requests.post(
            f"{self.base_url}/api/auth/login/",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access']
        self.refresh_token = data['refresh']
        
        print(f"✓ Logged in as {username}")
        return data
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        if not self.access_token:
            raise Exception("Not authenticated. Please login first.")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_agent(self, name: str, model: str = "gpt-3.5-turbo", 
                     personality_prompt: str = "") -> Dict[str, Any]:
        """Create a new AI agent"""
        response = requests.post(
            f"{self.base_url}/api/agents/",
            headers=self._headers(),
            json={
                "name": name,
                "parameters": {
                    "model": model,
                    "personality_prompt": personality_prompt
                }
            }
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Created agent '{name}' (ID: {data['id']})")
        return data
    
    def list_agents(self) -> list:
        """List all agents"""
        response = requests.get(
            f"{self.base_url}/api/agents/",
            headers=self._headers()
        )
        response.raise_for_status()
        
        agents = response.json()['results']
        print(f"✓ Found {len(agents)} agent(s)")
        return agents
    
    def update_agent_personality(self, agent_id: int, personality_prompt: str) -> Dict[str, Any]:
        """Update an agent's personality"""
        response = requests.put(
            f"{self.base_url}/api/agents/{agent_id}/personality/",
            headers=self._headers(),
            json={"personality_prompt": personality_prompt}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Updated agent {agent_id} personality")
        return data
    
    def chat(self, message: str, session_id: int = None, agent_id: int = None) -> Dict[str, Any]:
        """Send a chat message"""
        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        if agent_id:
            payload["agent_id"] = agent_id
        
        response = requests.post(
            f"{self.base_url}/api/chat/",
            headers=self._headers(),
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Message sent (Session ID: {data['session_id']})")
        return data
    
    def get_chat_history(self, session_id: int = None, limit: int = 100) -> Dict[str, Any]:
        """Get chat history"""
        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        
        response = requests.get(
            f"{self.base_url}/api/chat/history/",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Retrieved {len(data['sessions'])} session(s)")
        return data
    
    def list_sessions(self) -> list:
        """List all chat sessions"""
        response = requests.get(
            f"{self.base_url}/api/sessions/",
            headers=self._headers()
        )
        response.raise_for_status()
        
        sessions = response.json()['results']
        print(f"✓ Found {len(sessions)} session(s)")
        return sessions


def main():
    """Example usage of the Lingxi API"""
    
    # Initialize client
    client = LingxiClient("http://localhost:8000")
    
    print("=" * 60)
    print("Lingxi API Example")
    print("=" * 60)
    
    # 1. Login
    print("\n1. User Authentication")
    print("-" * 60)
    try:
        client.login("testuser", "testpass123")
    except requests.exceptions.HTTPError as e:
        print(f"✗ Login failed: {e}")
        print("\nNote: You need to create a user first:")
        print("  python manage.py createsuperuser")
        print("  Or use Django shell to create a user")
        return
    
    # 2. Create an agent
    print("\n2. Create an AI Agent")
    print("-" * 60)
    agent = client.create_agent(
        name="python-tutor",
        model="gpt-3.5-turbo",
        personality_prompt="You are a friendly Python programming tutor who explains concepts clearly with examples."
    )
    agent_id = agent['id']
    
    # 3. List agents
    print("\n3. List All Agents")
    print("-" * 60)
    agents = client.list_agents()
    for agent in agents:
        print(f"  - {agent['name']} (ID: {agent['id']}, Model: {agent['parameters']['model']})")
    
    # 4. Send chat messages
    print("\n4. Chat with the Agent")
    print("-" * 60)
    
    # First message (creates a new session)
    response1 = client.chat(
        message="What are Python decorators?",
        agent_id=agent_id
    )
    session_id = response1['session_id']
    print(f"  User: What are Python decorators?")
    print(f"  AI: {response1['response'][:100]}...")
    
    # Second message (continues the session)
    response2 = client.chat(
        message="Can you show me an example?",
        session_id=session_id
    )
    print(f"  User: Can you show me an example?")
    print(f"  AI: {response2['response'][:100]}...")
    
    # 5. Get chat history
    print("\n5. Retrieve Chat History")
    print("-" * 60)
    history = client.get_chat_history(session_id=session_id)
    session = history['sessions'][0]
    print(f"  Session ID: {session['id']}")
    print(f"  Started: {session['started_at']}")
    print(f"  Messages: {session['message_count']}")
    print(f"  Summary: {session['summary'] or 'Not yet generated'}")
    
    # 6. Update agent personality
    print("\n6. Update Agent Personality")
    print("-" * 60)
    client.update_agent_personality(
        agent_id=agent_id,
        personality_prompt="You are an expert Python developer who provides concise, production-ready code examples."
    )
    
    # 7. List all sessions
    print("\n7. List All Sessions")
    print("-" * 60)
    sessions = client.list_sessions()
    for session in sessions[:5]:  # Show first 5
        print(f"  - Session {session['id']}: {session['message_count']} messages")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
