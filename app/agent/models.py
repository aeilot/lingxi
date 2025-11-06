from django.db import models
from django.contrib.auth.models import User

# Basic Models
class ChatInformation(models.Model):
    chat_date = models.DateTimeField(auto_now_add=True, verbose_name="Chat Date", help_text="The date and time when the chat was created.")
    message = models.TextField(verbose_name="Message", help_text="The message sent.")
    is_agent_growth = models.BooleanField(default=False, verbose_name="Is Agent Growth", help_text="Indicates if the message was sent by the agent growth system.")
    is_user = models.BooleanField(default=True, verbose_name="Is User", help_text="Indicates if the message was sent by the user.")
    is_agent = models.BooleanField(default=False, verbose_name="Is Agent", help_text="Indicates if the message was sent by the agent.")
    is_read = models.BooleanField(default=False, verbose_name="Is Read", help_text="Indicates if the message has been read by the user (已读回执).")
    metadata = models.JSONField(blank=True, null=True, verbose_name="Metadata", help_text="Additional metadata related to the chat.")
    critical = models.BooleanField(default=False, verbose_name="Critical", help_text="Indicates if the chat is marked as critical.")
    critical_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Critical Type", help_text="The type, if applicable.")

class ChatSummary(models.Model):
    summary_start_time = models.DateTimeField(verbose_name="Summary Start Time", help_text="The start time of the summarized chat.")
    summary_end_time = models.DateTimeField(verbose_name="Summary End Time", help_text="The end time of the summarized chat.")
    summary_text = models.TextField(verbose_name="Summary Text", help_text="The summarized text of the chat.")
    related_chats = models.ManyToManyField(
        ChatInformation,
        blank=True,
        verbose_name="Related Chats",
        help_text="The chat information entries related to this summary.",
        related_name="summaries"
    )

class AgentConfiguration(models.Model):
    name = models.CharField(max_length=100, verbose_name="Agent Name", help_text="The name of the agent configuration.")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User", help_text="The user who owns this agent.", null=True, blank=True)
    parameters = models.JSONField(verbose_name="Parameters", help_text="Configuration parameters for the agent.")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At", help_text="The date and time when the configuration was created.")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At", help_text="The date and time when the configuration was last updated.")
    timings = models.JSONField(blank=True, null=True, verbose_name="Timings", help_text="Timing information related to the agent's operations.")

    class Meta:
        unique_together = [['name', 'user']]
    
# ChatSession

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User", help_text="The user who owns this session.", null=True, blank=True)
    agent_configuration = models.ForeignKey(
        'AgentConfiguration',
        on_delete=models.CASCADE,
        verbose_name="Agent Configuration",
        help_text="The agent configuration associated with this chat session."
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Started At", help_text="The date and time when the chat session started.")
    chat_infos = models.ManyToManyField(
        ChatInformation,
        blank=True,
        verbose_name="Chat Informations",
        help_text="The chat information entries in this session.",
        related_name="sessions"
    )
    summaries = models.ManyToManyField(
        ChatSummary,
        blank=True,
        verbose_name="Chat Summaries",
        help_text="The chat summaries associated with this session.",
        related_name="sessions"
    )
    current_state = models.JSONField(blank=True, null=True, verbose_name="Current State", help_text="The current state of the chat session.")
    summary = models.TextField(blank=True, null=True, verbose_name="Session Summary", help_text="The current summary of the chat session.")
    message_count = models.IntegerField(default=0, verbose_name="Message Count", help_text="The number of messages in this session.")
    last_activity_at = models.DateTimeField(blank=True, null=True, verbose_name="Last Activity At", help_text="The date and time of the last activity in this session.")
