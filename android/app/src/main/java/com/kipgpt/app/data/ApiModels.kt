package com.kipgpt.app.data

data class LoginRequest(val email: String, val password: String)

data class RegisterRequest(val email: String, val password: String)

data class LoginResponse(val token: String, val user: UserInfo)

data class UserInfo(val email: String, val auth_provider: String)

data class MeResponse(
    val email: String,
    val auth_provider: String,
    val mail_accounts: List<MailAccount> = emptyList(),
)

data class MailAccount(
    val id: String = "",
    val email: String = "",
    val label: String = "",
)

data class ChatSummary(
    val id: String,
    val title: String,
    val preview: String,
    val message_count: Int,
    val active: Boolean,
)

data class ChatsResponse(val active_chat: String, val chats: List<ChatSummary>)

data class ChatFileMeta(
    val name: String = "",
    val type: String = "other",
    val icon: String = "",
)

data class ChatMessage(
    val role: String,
    val content: String,
    val file: ChatFileMeta? = null,
)

data class MessagesResponse(
    val chat_id: String,
    val title: String,
    val messages: List<ChatMessage>,
)

data class SendRequest(val text: String)

data class SendResponse(
    val answer: String,
    val chat_title: String,
    val messages: List<ChatMessage>,
    val file: ChatFileMeta? = null,
)

data class MailFolder(val id: String, val label: String, val icon: String)

data class FoldersResponse(val folders: List<MailFolder>)

data class MailAttachment(
    val index: Int,
    val filename: String,
    val mime: String,
    val size: Int,
    val is_image: Boolean,
)

data class MailItem(
    val id: String = "",
    val subject: String = "",
    val sender: String = "",
    val sender_display: String = "",
    val date: String = "",
    val content: String = "",
    val attachments: List<MailAttachment> = emptyList(),
    val thread_count: Int = 1,
    val starred: Boolean = false,
)

data class MailListResponse(
    val folder: String,
    val account: String,
    val mails: List<MailItem>,
    val meta: Map<String, Any> = emptyMap(),
)

data class TranslateRequest(val text: String, val target_lang: String)

data class TranslateResponse(val translated: String, val target_lang: String)

data class MailLanguageOption(val code: String, val label: String)

data class MailLanguagesResponse(val languages: List<MailLanguageOption> = emptyList())

data class LibraryAttachmentRef(
    val id: String = "",
    val filename: String = "",
    val mimetype: String = "",
    val size: Int = 0,
    val score: Int = 0,
    val query: String = "",
)

data class MailAiReplyRequest(
    val mail_id: String = "",
    val folder: String = "inbox",
    val sender: String = "",
    val subject: String = "",
    val content: String = "",
    val user_instruction: String = "",
    val current_draft: String = "",
    val revize_notu: String = "",
)

data class MailAiReplyResponse(
    val draft: String,
    val html_body: String = "",
    val library_attachments: List<LibraryAttachmentRef> = emptyList(),
    val library_file_ids: List<String> = emptyList(),
    val mail: MailItem,
)

data class OutgoingAttachmentPayload(
    val filename: String,
    val mimetype: String = "application/octet-stream",
    val data_base64: String,
)

data class MailSendReplyRequest(
    val sender: String,
    val subject: String,
    val final_reply: String,
    val cc_email: String = "",
    val bcc_email: String = "",
    val html_body: String = "",
    val library_file_ids: List<String> = emptyList(),
    val attachment: OutgoingAttachmentPayload? = null,
)

data class MailSendReplyResponse(
    val success: Boolean,
    val message: String,
)

data class MailAiComposeRequest(
    val to_email: String = "",
    val subject: String = "",
    val user_instruction: String = "",
    val current_draft: String = "",
    val revize_notu: String = "",
)

data class MailAiComposeResponse(
    val draft: String,
    val html_body: String = "",
    val library_attachments: List<LibraryAttachmentRef> = emptyList(),
    val library_file_ids: List<String> = emptyList(),
)

data class MailSendNewRequest(
    val to_email: String,
    val subject: String = "",
    val body: String,
    val cc_email: String = "",
    val bcc_email: String = "",
    val html_body: String = "",
    val library_file_ids: List<String> = emptyList(),
    val attachment: OutgoingAttachmentPayload? = null,
)

data class MailSendNewResponse(
    val success: Boolean,
    val message: String,
)

data class MailSummaryRequest(
    val mail_id: String = "",
    val folder: String = "inbox",
    val sender: String = "",
    val subject: String = "",
    val content: String = "",
    val create_reminders: Boolean = false,
)

data class MailSummaryData(
    val summary: String = "",
    val interpretation: String = "",
    val importance: String = "medium",
    val urgency: String = "medium",
    val action_items: List<String> = emptyList(),
    val suggested_reply: String = "",
)

data class CalendarEvent(
    val id: String = "",
    val title: String = "",
    val description: String = "",
    val start: String? = null,
    val end: String? = null,
    val reminder_at: String? = null,
    val all_day: Boolean = false,
    val done: Boolean = false,
    val source: String = "",
    val source_mail_id: String? = null,
    val created_at: String = "",
    val due_at: String? = null,
    val is_overdue: Boolean = false,
)

data class MailSummaryResponse(
    val summary: MailSummaryData,
    val reminders_created: List<CalendarEvent> = emptyList(),
)

data class CalendarEventsResponse(
    val events: List<CalendarEvent> = emptyList(),
    val reminders: List<CalendarEvent> = emptyList(),
)

data class CalendarCreateRequest(
    val title: String,
    val description: String = "",
    val start: String? = null,
    val end: String? = null,
    val reminder_at: String? = null,
    val all_day: Boolean = false,
)

data class CalendarUpdateRequest(
    val title: String? = null,
    val description: String? = null,
    val start: String? = null,
    val reminder_at: String? = null,
    val done: Boolean? = null,
)

data class CalendarEventResponse(val event: CalendarEvent)

data class LibraryFile(
    val id: String = "",
    val filename: String = "",
    val stored_name: String = "",
    val mimetype: String = "",
    val category: String = "",
    val size: Int = 0,
    val note: String = "",
    val created_at: String = "",
)

data class FilesResponse(val files: List<LibraryFile> = emptyList())

data class FileUploadResponse(val file: LibraryFile)

data class ApiError(val error: String)
