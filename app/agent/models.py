from django.db import models

# Basic Models
class ChatInformation(models.Model):
    chat_date = models.DateTimeField(auto_now_add=True, verbose_name="Chat Date", help_text="The date and time when the chat was created.")
    message = models.TextField(verbose_name="Message", help_text="The message sent.")
    is_user = models.BooleanField(default=True, verbose_name="Is User", help_text="Indicates if the message was sent by the user.")
    metadata = models.JSONField(blank=True, null=True, verbose_name="Metadata", help_text="Additional metadata related to the chat.")
    critical = models.BooleanField(default=False, verbose_name="Critical", help_text="Indicates if the chat is marked as critical.")
    critical_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Critical Type", help_text="The type, if applicable.")

class ChatSummary(models.Model):
    summary_date = models.DateTimeField(auto_now_add=True, verbose_name="Summary Date", help_text="The date and time when the summary was created.")
    summary_text = models.TextField(verbose_name="Summary Text", help_text="The summarized text of the chat.")
    related_chats = models.ManyToManyField(
        ChatInformation,
        blank=True,
        verbose_name="Related Chats",
        help_text="The chat information entries related to this summary.",
        related_name="summaries"
    )

class AgentConfiguration(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Agent Name", help_text="The name of the agent configuration.")
    parameters = models.JSONField(verbose_name="Parameters", help_text="Configuration parameters for the agent.")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At", help_text="The date and time when the configuration was created.")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At", help_text="The date and time when the configuration was last updated.")
    timings = models.JSONField(blank=True, null=True, verbose_name="Timings", help_text="Timing information related to the agent's operations.")


# ChatSession

class ChatSession(models.Model):
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
