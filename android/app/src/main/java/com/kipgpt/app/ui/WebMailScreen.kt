package com.kipgpt.app.ui

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.kipgpt.app.data.SessionManager
import java.net.URLEncoder

/**
 * Giriş sonrası web mail arayüzünü (masaüstü ile aynı UI) gösterir.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun WebMailScreen(
    apiBaseUrl: String,
    token: String,
    onLogout: () -> Unit,
) {
    val webOrigin = remember(apiBaseUrl) {
        SessionManager.webOriginFromApiBase(apiBaseUrl)
    }
    val startUrl = remember(webOrigin, token) {
        val encoded = URLEncoder.encode(token, "UTF-8")
        "$webOrigin/auth/mobile-handoff?token=$encoded&next=/mail"
    }
    val loading = remember { mutableStateOf(true) }
    val webViewRef = remember { mutableStateOf<WebView?>(null) }
    val loggedOut = remember { mutableStateOf(false) }

    fun maybeHandleLogout(url: String?) {
        if (url.isNullOrBlank() || loggedOut.value) return
        val path = url.substringAfter(webOrigin, missingDelimiterValue = "")
        val onLogin = path.startsWith("/login") ||
            url.contains("/login?") ||
            url.endsWith("/login")
        val handoff = url.contains("/auth/mobile-handoff")
        if (onLogin && !handoff) {
            loggedOut.value = true
            onLogout()
        }
    }

    BackHandler(enabled = true) {
        val wv = webViewRef.value
        if (wv != null && wv.canGoBack()) {
            wv.goBack()
        }
    }

    LaunchedEffect(startUrl) {
        loggedOut.value = false
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { context ->
                WebView(context).apply {
                    layoutParams = ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT,
                    )
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.loadsImagesAutomatically = true
                    settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                    settings.userAgentString = settings.userAgentString + " KipGPTAndroid/1.8.8"
                    CookieManager.getInstance().setAcceptCookie(true)
                    CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                    webChromeClient = WebChromeClient()
                    webViewClient = object : WebViewClient() {
                        override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                            loading.value = true
                            maybeHandleLogout(url)
                        }

                        override fun onPageFinished(view: WebView?, url: String?) {
                            loading.value = false
                            CookieManager.getInstance().flush()
                            maybeHandleLogout(url)
                        }

                        override fun shouldOverrideUrlLoading(
                            view: WebView?,
                            request: WebResourceRequest?,
                        ): Boolean {
                            val url = request?.url?.toString()
                            maybeHandleLogout(url)
                            return false
                        }
                    }
                    webViewRef.value = this
                    loadUrl(startUrl)
                }
            },
            update = { view ->
                webViewRef.value = view
            },
        )

        if (loading.value) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            webViewRef.value?.stopLoading()
            webViewRef.value = null
        }
    }
}
