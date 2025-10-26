from django.contrib import admin
from .models import ChatInformation, ChatSummary, AgentConfiguration, ChatSession

# Register your models here.

@admin.register(ChatInformation)
class ChatInformationAdmin(admin.ModelAdmin):
    list_display = ('chat_date', 'message', 'is_user', 'is_agent', 'critical')
    list_filter = ('is_user', 'is_agent', 'is_agent_growth', 'critical', 'chat_date')
    search_fields = ('message',)
    readonly_fields = ('chat_date',)

@admin.register(ChatSummary)
class ChatSummaryAdmin(admin.ModelAdmin):
    list_display = ('summary_start_time', 'summary_end_time', 'summary_text')
    list_filter = ('summary_start_time', 'summary_end_time')
    search_fields = ('summary_text',)
    filter_horizontal = ('related_chats',)

@admin.register(AgentConfiguration)
class AgentConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'agent_configuration', 'started_at')
    list_filter = ('started_at', 'agent_configuration')
    readonly_fields = ('started_at',)
    filter_horizontal = ('chat_infos', 'summaries')
