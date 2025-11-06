from rest_framework import serializers
from django.contrib.auth.models import User
from .models import AgentConfiguration, ChatSession, ChatInformation


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']


class AgentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConfiguration
        fields = ['id', 'name', 'parameters', 'created_at', 'updated_at', 'timings']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set the user from the request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatInformation
        fields = ['id', 'chat_date', 'message', 'is_user', 'is_agent', 'is_agent_growth', 'is_read', 'metadata', 'critical', 'critical_type']
        read_only_fields = ['id', 'chat_date']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatInformationSerializer(source='chat_infos', many=True, read_only=True)
    agent_name = serializers.CharField(source='agent_configuration.name', read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'agent_configuration', 'agent_name', 'started_at', 'summary', 'message_count', 'last_activity_at', 'messages', 'current_state']
        read_only_fields = ['id', 'started_at', 'message_count', 'last_activity_at']

    def create(self, validated_data):
        # Set the user from the request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for sending a chat message"""
    message = serializers.CharField()
    session_id = serializers.IntegerField(required=False, allow_null=True)
    agent_id = serializers.IntegerField(required=False, allow_null=True)
