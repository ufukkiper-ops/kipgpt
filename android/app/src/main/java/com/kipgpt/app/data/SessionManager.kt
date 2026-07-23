package com.kipgpt.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore("kipgpt_session")

class SessionManager(private val context: Context) {
    companion object {
        private val KEY_TOKEN = stringPreferencesKey("token")
        private val KEY_BASE_URL = stringPreferencesKey("base_url")
        private val KEY_USER_EMAIL = stringPreferencesKey("user_email")
        private val KEY_MAIL_ACCOUNT = stringPreferencesKey("active_mail_account_id")
        const val EMULATOR_BASE_URL = "http://10.0.2.2:5001/api/v1/"
        const val RENDER_BASE_URL = "https://kip-asistan.onrender.com/api/v1/"
        /** start.bat LAN örneği */
        const val LAN_IP_PLACEHOLDER = "192.168.10.153"
        /**
         * start_public.bat / Cloudflare Tunnel adresi.
         * Tunnel yeniden açılırsa bu URL değişebilir; tunnel/current_url.txt ile güncelle.
         */
        const val PUBLIC_TUNNEL_BASE_URL =
            "https://affiliate-totally-brian-observations.trycloudflare.com/api/v1/"

        val DEFAULT_BASE_URL: String = PUBLIC_TUNNEL_BASE_URL

        fun lanBaseUrl(ip: String = LAN_IP_PLACEHOLDER): String {
            val clean = ip.trim().trimEnd('/')
            return "http://$clean:5001/api/v1/"
        }

        fun isPlaceholderLanUrl(url: String): Boolean {
            return url.contains(LAN_IP_PLACEHOLDER) && !url.contains("trycloudflare.com")
        }
    }

    val tokenFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_TOKEN]
    }

    val baseUrlFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_BASE_URL] ?: DEFAULT_BASE_URL
    }

    val userEmailFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_USER_EMAIL]
    }

    val activeMailAccountFlow: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_MAIL_ACCOUNT]
    }

    suspend fun getActiveMailAccount(): String? {
        return activeMailAccountFlow.first()
    }

    suspend fun saveToken(token: String, email: String? = null) {
        context.dataStore.edit { prefs ->
            prefs[KEY_TOKEN] = token
            if (!email.isNullOrBlank()) {
                prefs[KEY_USER_EMAIL] = email
            }
        }
    }

    suspend fun clearToken() {
        context.dataStore.edit { prefs ->
            prefs.remove(KEY_TOKEN)
            prefs.remove(KEY_USER_EMAIL)
            prefs.remove(KEY_MAIL_ACCOUNT)
        }
    }

    suspend fun saveActiveMailAccount(accountId: String?) {
        context.dataStore.edit { prefs ->
            if (accountId.isNullOrBlank()) {
                prefs.remove(KEY_MAIL_ACCOUNT)
            } else {
                prefs[KEY_MAIL_ACCOUNT] = accountId
            }
        }
    }

    suspend fun saveBaseUrl(url: String) {
        val normalized = if (url.endsWith("/")) url else "$url/"
        context.dataStore.edit { prefs ->
            prefs[KEY_BASE_URL] = normalized
        }
    }

    /** Uygulama içine gömülü tünel adresini her açılışta uygula (eski URL’leri sil). */
    suspend fun applyBundledServerUrl() {
        context.dataStore.edit { prefs ->
            prefs[KEY_BASE_URL] = PUBLIC_TUNNEL_BASE_URL
        }
    }

    @Deprecated("Use applyBundledServerUrl", ReplaceWith("applyBundledServerUrl()"))
    suspend fun applyLocalServerDefaultIfNeeded() = applyBundledServerUrl()
}
