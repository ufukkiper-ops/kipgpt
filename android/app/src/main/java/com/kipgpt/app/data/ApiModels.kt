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

data class ChatMessage(val role: String, val content: String)

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
    val id: String,
    val subject: String,
    val sender: String,
    val sender_display: String,
    val date: String,
    val content: String,
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

data class ApiError(val error: String)
