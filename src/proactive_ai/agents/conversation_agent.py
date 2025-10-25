"""
Conversation Agent - Uses Haystack RAG Pipeline for responses
"""

from typing import List, Optional, Dict, Any
from haystack import Pipeline, Document
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.document_stores.in_memory import InMemoryDocumentStore

from ..models import PersonalityProfile, Message


class ConversationAgent:
    """
    Conversation Agent that uses a Haystack RAG Pipeline for responses.
    Integrates factual knowledge and personality context.
    """
    
    def __init__(
        self,
        api_key: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize the Conversation Agent.
        
        Args:
            api_key: OpenAI API key
            embedding_model: Model for embeddings
            llm_model: LLM model name
        """
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.personality_profile = PersonalityProfile()
        
        # Initialize document store for RAG
        self.document_store = InMemoryDocumentStore()
        
        # Build the RAG pipeline
        self._build_pipeline()
    
    def _build_pipeline(self):
        """Build the Haystack RAG pipeline"""
        # Create the RAG pipeline
        self.pipeline = Pipeline()
        
        # Add components
        self.pipeline.add_component("retriever", InMemoryBM25Retriever(document_store=self.document_store))
        
        # Prompt builder with personality and context
        prompt_template = """
{{ personality_context }}

Context from knowledge base:
{% for doc in documents %}
- {{ doc.content }}
{% endfor %}

Conversation history:
{% for message in history %}
{{ message.role }}: {{ message.content }}
{% endfor %}

User: {{ query }}
Assistant: """
        
        self.pipeline.add_component("prompt_builder", PromptBuilder(template=prompt_template))
        self.pipeline.add_component("llm", OpenAIGenerator(api_key=self.api_key, model=self.llm_model))
        
        # Connect components
        self.pipeline.connect("retriever", "prompt_builder.documents")
        self.pipeline.connect("prompt_builder", "llm")
    
    def add_knowledge(self, documents: List[str]):
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of document strings
        """
        docs = [Document(content=doc) for doc in documents]
        self.document_store.write_documents(docs)
    
    def update_personality(self, personality_profile: PersonalityProfile):
        """
        Update the personality profile (P_params).
        
        Args:
            personality_profile: New personality profile
        """
        self.personality_profile = personality_profile
    
    def generate_response(
        self,
        query: str,
        history: List[Message],
        kb_context: str = "",
        max_history: int = 5
    ) -> Dict[str, str]:
        """
        Generate a response using the RAG pipeline with transparent parts.
        
        Args:
            query: User query
            history: Conversation history
            kb_context: Additional knowledge base context
            max_history: Maximum number of history messages to include
            
        Returns:
            Dictionary with 'factual', 'personality', and 'full' response parts
        """
        # Get personality context
        personality_context = self.personality_profile.to_prompt()
        
        # Format history
        recent_history = history[-max_history:] if len(history) > max_history else history
        history_dict = [{"role": msg.role, "content": msg.content} for msg in recent_history]
        
        # Run the pipeline to get factual response
        result = self.pipeline.run({
            "retriever": {"query": query},
            "prompt_builder": {
                "personality_context": personality_context,
                "history": history_dict,
                "query": query
            }
        })
        
        # Extract full response
        full_response = result["llm"]["replies"][0]
        
        # Get retrieved documents for factual part
        retrieved_docs = result.get("retriever", {}).get("documents", [])
        factual_info = "\n".join([doc.content for doc in retrieved_docs[:2]]) if retrieved_docs else "No specific factual information retrieved."
        
        return {
            "factual": factual_info,
            "personality": personality_context,
            "full": full_response
        }
    
    def chat(self, query: str, history: List[Message]) -> Dict[str, str]:
        """
        Simplified chat interface.
        
        Args:
            query: User query
            history: Conversation history
            
        Returns:
            Dictionary with response parts
        """
        return self.generate_response(query, history)
