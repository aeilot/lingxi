SPLIT_MESSAGE_SYSTEM_PROMPT = """You can optionally split your response into multiple messages for better readability.
If you want to split your response, return ONLY a JSON object in this exact format:
{"messages": ["first message", "second message", "third message"]}

If you prefer to send a single message, just reply with plain text as normal.

Important:
- If using JSON format, the response MUST be valid JSON and nothing else
- Each message in the array should be a complete thought or idea
- Use this feature when the response naturally breaks into multiple parts (e.g., greeting + answer, or multiple steps)
- Don't overuse it - only split when it improves clarity
- Reply in the sender's language""".strip()

SUMMARIZE_PROMPT_WITH_EXISTING = """
你是一个主题生成助手，负责根据最近的对话生成一个当前对话的主题。

最近的对话记录：
"{existing_summary}"

请提供一个更新后的主题，包含新消息。主题应该简洁（1-2句话，最多100个字符），捕捉对话的主要内容。只返回主题文本，不要包含其他内容。

输出格式：直接输出主题字符串。""".strip()

SUMMARIZE_PROMPT_NO_EXISTING = """You are summarizing a chat conversation. Here are the messages:
{conversation_text}

Please provide a brief summary (1-2 sentences, max 100 characters) that captures the main topic of the conversation. Return only the summary text, nothing else.""".strip()

PERSONALITY_ANALYSIS_PROMPT = """You are analyzing a chat conversation to determine if the AI agent's personality should be updated.

Current personality prompt: "{current_personality_text}"
Message count: {message_count}
Session summary: {session_summary}

Recent conversation:
{conversation_text}

Based on this conversation, analyze:
1. Is the current personality appropriate for the user's needs?
2. What communication style does the user prefer? (formal/casual, detailed/concise, etc.)
3. Are there any patterns in the conversation that suggest a different personality would work better?
4. Would updating the personality improve the user experience?

Consider:
- User's language style and formality
- Topics being discussed
- Level of detail the user prefers
- Whether the user seems satisfied with current responses
- Consistency of conversation topics

Respond ONLY with a JSON object in this exact format:
{{"should_update": true/false, "reason": "explanation", "suggested_personality": "new personality prompt or null", "confidence": 0.0-1.0}}

The suggested_personality should be a clear, concise prompt that describes how the AI should behave.""".strip()

PROACTIVE_DECISION_PROMPT = """You are analyzing a chat conversation to decide whether the AI should proactively continue the conversation.

Current summary: {summary}
Message count: {message_count}
Minutes inactive: {minutes_inactive:.1f}
User preference for proactivity: {user_preferences}{unread_info}

Recent conversation:
{conversation_text}

Based on this information, decide whether the AI should:
1. 'continue' - proactively continue the current topic with a relevant follow-up
2. 'new_topic' - suggest starting a new related topic
3. 'wait' - wait for the user to respond

Consider:
- Is the conversation at a natural stopping point?
- Are there unanswered questions or incomplete thoughts?
- Would a follow-up add value or feel pushy?
- What is the user's preference level for proactive behavior?

Respond ONLY with a JSON object in this exact format:
{{"action": "continue|new_topic|wait", "reason": "brief explanation", "suggested_message": "message to send or null"}}""".strip()
