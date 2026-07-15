package com.kipgpt.app.data

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
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

    @DELETE("chats/{id}")
    suspend fun clearChat(@Path("id") id: String): Map<String, Boolean>

    @GET("mail/folders")
    suspend fun folders(): FoldersResponse

    @GET("mail")
    suspend fun mails(
        @Query("folder") folder: String,
        @Query("search") search: String? = null,
    ): MailListResponse

    @POST("mail/translate")
    suspend fun translate(@Body body: TranslateRequest): TranslateResponse
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
