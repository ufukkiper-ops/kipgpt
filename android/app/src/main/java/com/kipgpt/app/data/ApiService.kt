package com.kipgpt.app.data

import okhttp3.Interceptor
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming
import okhttp3.ResponseBody
import java.util.concurrent.TimeUnit

interface KipGptApi {
    @POST("login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @POST("register")
    suspend fun register(@Body body: RegisterRequest): LoginResponse

    @GET("me")
    suspend fun me(): MeResponse

    @GET("chats")
    suspend fun chats(): ChatsResponse

    @POST("chats")
    suspend fun newChat(): Map<String, String>

    @PUT("chats/{id}/activate")
    suspend fun activateChat(@Path("id") id: String): Map<String, String>

    @GET("chats/{id}/messages")
    suspend fun messages(@Path("id") id: String): MessagesResponse

    @POST("chats/{id}/messages")
    suspend fun sendMessage(@Path("id") id: String, @Body body: SendRequest): SendResponse

    @Multipart
    @POST("chats/{id}/messages")
    suspend fun sendMessageWithFile(
        @Path("id") id: String,
        @Part("text") text: RequestBody,
        @Part file: MultipartBody.Part,
    ): SendResponse

    @DELETE("chats/{id}")
    suspend fun clearChat(@Path("id") id: String): Map<String, Boolean>

    @GET("mail/folders")
    suspend fun folders(): FoldersResponse

    @GET("mail")
    suspend fun mails(
        @Query("folder") folder: String,
        @Query("search") search: String? = null,
    ): MailListResponse

    @GET("mail/detail")
    suspend fun mailDetail(
        @Query("mail_id") mailId: String,
        @Query("folder") folder: String,
    ): MailItem

    @GET("mail/attachment")
    @Streaming
    suspend fun downloadAttachment(
        @Query("mail_id") mailId: String,
        @Query("index") index: Int,
        @Query("folder") folder: String,
    ): ResponseBody

    @POST("mail/translate")
    suspend fun translate(@Body body: TranslateRequest): TranslateResponse

    @POST("mail/ai-reply")
    suspend fun generateMailAiReply(@Body body: MailAiReplyRequest): MailAiReplyResponse

    @POST("mail/send-reply")
    suspend fun sendMailReply(@Body body: MailSendReplyRequest): MailSendReplyResponse
}

class ApiClient(private var token: String?, baseUrl: String) {
    private var retrofit: Retrofit = buildRetrofit(baseUrl)

    fun updateToken(newToken: String?) {
        token = newToken
    }

    fun updateBaseUrl(baseUrl: String) {
        retrofit = buildRetrofit(baseUrl)
    }

    val api: KipGptApi get() = retrofit.create(KipGptApi::class.java)

    private fun buildRetrofit(baseUrl: String): Retrofit {
        val authInterceptor = Interceptor { chain ->
            val requestBuilder = chain.request().newBuilder()
            token?.let { requestBuilder.addHeader("Authorization", "Bearer $it") }
            chain.proceed(requestBuilder.build())
        }

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .writeTimeout(90, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
}
