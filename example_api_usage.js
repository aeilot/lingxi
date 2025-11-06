/**
 * Example JavaScript/Node.js script demonstrating how to use the Lingxi API.
 * 
 * This script shows:
 * 1. User authentication with JWT tokens
 * 2. Creating and managing AI agents
 * 3. Sending chat messages
 * 4. Retrieving chat history
 * 5. Updating agent personality
 * 
 * Usage:
 *   node example_api_usage.js
 */

const baseURL = 'http://localhost:8000';

class LingxiClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.accessToken = null;
    this.refreshToken = null;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status}`);
    }

    const data = await response.json();
    this.accessToken = data.access;
    this.refreshToken = data.refresh;

    console.log(`✓ Logged in as ${username}`);
    return data;
  }

  getHeaders() {
    if (!this.accessToken) {
      throw new Error('Not authenticated. Please login first.');
    }

    return {
      'Authorization': `Bearer ${this.accessToken}`,
      'Content-Type': 'application/json'
    };
  }

  async createAgent(name, model = 'gpt-3.5-turbo', personalityPrompt = '') {
    const response = await fetch(`${this.baseURL}/api/agents/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        name,
        parameters: {
          model,
          personality_prompt: personalityPrompt
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Create agent failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Created agent '${name}' (ID: ${data.id})`);
    return data;
  }

  async listAgents() {
    const response = await fetch(`${this.baseURL}/api/agents/`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`List agents failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Found ${data.results.length} agent(s)`);
    return data.results;
  }

  async updateAgentPersonality(agentId, personalityPrompt) {
    const response = await fetch(`${this.baseURL}/api/agents/${agentId}/personality/`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify({ personality_prompt: personalityPrompt })
    });

    if (!response.ok) {
      throw new Error(`Update personality failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Updated agent ${agentId} personality`);
    return data;
  }

  async chat(message, sessionId = null, agentId = null) {
    const payload = { message };
    if (sessionId) payload.session_id = sessionId;
    if (agentId) payload.agent_id = agentId;

    const response = await fetch(`${this.baseURL}/api/chat/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Chat failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Message sent (Session ID: ${data.session_id})`);
    return data;
  }

  async getChatHistory(sessionId = null, limit = 100) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (sessionId) params.append('session_id', sessionId.toString());

    const response = await fetch(`${this.baseURL}/api/chat/history/?${params}`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`Get history failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Retrieved ${data.sessions.length} session(s)`);
    return data;
  }

  async listSessions() {
    const response = await fetch(`${this.baseURL}/api/sessions/`, {
      headers: this.getHeaders()
    });

    if (!response.ok) {
      throw new Error(`List sessions failed: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✓ Found ${data.results.length} session(s)`);
    return data.results;
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('Lingxi API Example (JavaScript)');
  console.log('='.repeat(60));

  const client = new LingxiClient('http://localhost:8000');

  try {
    // 1. Login
    console.log('\n1. User Authentication');
    console.log('-'.repeat(60));
    await client.login('testuser', 'testpass123');

    // 2. Create an agent
    console.log('\n2. Create an AI Agent');
    console.log('-'.repeat(60));
    const agent = await client.createAgent(
      'javascript-mentor',
      'gpt-3.5-turbo',
      'You are a helpful JavaScript programming mentor who explains concepts clearly with modern ES6+ examples.'
    );
    const agentId = agent.id;

    // 3. List agents
    console.log('\n3. List All Agents');
    console.log('-'.repeat(60));
    const agents = await client.listAgents();
    agents.forEach(agent => {
      console.log(`  - ${agent.name} (ID: ${agent.id}, Model: ${agent.parameters.model})`);
    });

    // 4. Send chat messages
    console.log('\n4. Chat with the Agent');
    console.log('-'.repeat(60));

    // First message (creates a new session)
    const response1 = await client.chat(
      'What are JavaScript closures?',
      null,
      agentId
    );
    const sessionId = response1.session_id;
    console.log(`  User: What are JavaScript closures?`);
    console.log(`  AI: ${response1.response.substring(0, 100)}...`);

    // Second message (continues the session)
    const response2 = await client.chat(
      'Can you show me a practical example?',
      sessionId
    );
    console.log(`  User: Can you show me a practical example?`);
    console.log(`  AI: ${response2.response.substring(0, 100)}...`);

    // 5. Get chat history
    console.log('\n5. Retrieve Chat History');
    console.log('-'.repeat(60));
    const history = await client.getChatHistory(sessionId);
    const session = history.sessions[0];
    console.log(`  Session ID: ${session.id}`);
    console.log(`  Started: ${session.started_at}`);
    console.log(`  Messages: ${session.message_count}`);
    console.log(`  Summary: ${session.summary || 'Not yet generated'}`);

    // 6. Update agent personality
    console.log('\n6. Update Agent Personality');
    console.log('-'.repeat(60));
    await client.updateAgentPersonality(
      agentId,
      'You are an expert JavaScript developer who provides concise, production-ready code examples with TypeScript types.'
    );

    // 7. List all sessions
    console.log('\n7. List All Sessions');
    console.log('-'.repeat(60));
    const sessions = await client.listSessions();
    sessions.slice(0, 5).forEach(session => {
      console.log(`  - Session ${session.id}: ${session.message_count} messages`);
    });

    console.log('\n' + '='.repeat(60));
    console.log('Example completed successfully!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error(`\n✗ Error: ${error.message}`);
    if (error.message.includes('Login failed')) {
      console.log('\nNote: You need to create a user first:');
      console.log('  python manage.py createsuperuser');
      console.log('  Or use Django shell to create a user');
    }
  }
}

// Run the example
main().catch(console.error);
