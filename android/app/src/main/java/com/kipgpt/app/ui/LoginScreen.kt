package com.kipgpt.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kipgpt.app.R
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.LoginRequest
import com.kipgpt.app.data.RegisterRequest
import com.kipgpt.app.data.SessionManager
import kotlinx.coroutines.launch
import retrofit2.HttpException

private val AuthBgTop = Color(0xFF0B0E14)
private val AuthBgMid = Color(0xFF121826)
private val AuthCard = Color(0xEB121622)
private val AuthBorder = Color(0x2E94A3B8)
private val AuthInputBg = Color(0xFF0F1420)
private val AuthText = Color(0xFFF3F4F6)
private val AuthMuted = Color(0xFF94A3B8)
private val AuthCyan = Color(0xFF67E8F9)
private val AuthBlue = Color(0xFF1A73E8)

@Composable
fun LoginScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    onLoggedIn: () -> Unit,
) {
    val email = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }
    val password2 = remember { mutableStateOf("") }
    val showPassword = remember { mutableStateOf(false) }
    val loading = remember { mutableStateOf(false) }
    val isRegister = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        sessionManager.applyBundledServerUrl()
        sessionManager.baseUrlFlow.collect { url ->
            apiClient.updateBaseUrl(url)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(AuthBgTop, AuthBgMid, AuthBgTop),
                ),
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(20.dp))
                    .background(AuthCard)
                    .border(1.dp, AuthBorder, RoundedCornerShape(20.dp))
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Image(
                    painter = painterResource(R.drawable.kipgpt_logo),
                    contentDescription = "KipGPT — Akıllı • Güvenilir • Yanında",
                    modifier = Modifier
                        .fillMaxWidth(0.85f)
                        .height(200.dp),
                    contentScale = ContentScale.Fit,
                )

                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = if (isRegister.value) "Kayıt Ol" else "Giriş Yap",
                    color = AuthText,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center,
                )
                Spacer(modifier = Modifier.height(16.dp))

                AuthField(
                    value = email.value,
                    onValueChange = { email.value = it },
                    placeholder = if (isRegister.value) {
                        "E-posta adresiniz"
                    } else {
                        "E-posta veya kullanıcı adı"
                    },
                    keyboardType = KeyboardType.Email,
                )
                Spacer(modifier = Modifier.height(10.dp))
                AuthField(
                    value = password.value,
                    onValueChange = { password.value = it },
                    placeholder = if (isRegister.value) "KipGPT giriş şifreniz" else "Şifre",
                    keyboardType = KeyboardType.Password,
                    isPassword = true,
                    showPassword = showPassword.value,
                    onTogglePassword = { showPassword.value = !showPassword.value },
                )
                if (isRegister.value) {
                    Spacer(modifier = Modifier.height(10.dp))
                    AuthField(
                        value = password2.value,
                        onValueChange = { password2.value = it },
                        placeholder = "Şifre tekrar",
                        keyboardType = KeyboardType.Password,
                        isPassword = true,
                        showPassword = showPassword.value,
                        onTogglePassword = { showPassword.value = !showPassword.value },
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "En az 6 karakter; büyük + küçük harf, sayı ve özel işaret",
                        color = AuthMuted,
                        fontSize = 12.sp,
                        textAlign = TextAlign.Start,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))
                Button(
                    onClick = {
                        scope.launch {
                            if (isRegister.value) {
                                val pwdError = validateRegisterPassword(password.value)
                                if (pwdError != null) {
                                    snackbar.showSnackbar(pwdError)
                                    return@launch
                                }
                                if (password.value != password2.value) {
                                    snackbar.showSnackbar("Şifreler eşleşmiyor.")
                                    return@launch
                                }
                            }
                            loading.value = true
                            try {
                                val response = if (isRegister.value) {
                                    apiClient.api.register(
                                        RegisterRequest(
                                            email = email.value.trim(),
                                            password = password.value,
                                            link_gmail = false,
                                        ),
                                    )
                                } else {
                                    apiClient.api.login(
                                        LoginRequest(email.value.trim(), password.value),
                                    )
                                }
                                sessionManager.saveToken(response.token, response.user.email)
                                apiClient.updateToken(response.token)
                                onLoggedIn()
                            } catch (e: HttpException) {
                                val msg = e.response()?.errorBody()?.string()?.let {
                                    it.substringAfter("\"error\":\"").substringBefore("\"")
                                } ?: "Giriş başarısız"
                                snackbar.showSnackbar(msg)
                            } catch (e: Exception) {
                                snackbar.showSnackbar("Bağlantı hatası: ${e.message}")
                            } finally {
                                loading.value = false
                            }
                        }
                    },
                    enabled = !loading.value &&
                        email.value.isNotBlank() &&
                        password.value.isNotBlank() &&
                        (!isRegister.value || password2.value.isNotBlank()),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AuthBlue,
                        contentColor = Color.White,
                        disabledContainerColor = AuthBlue.copy(alpha = 0.4f),
                    ),
                ) {
                    if (loading.value) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.height(22.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text(
                            if (isRegister.value) "Kayıt Ol" else "Giriş Yap",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))
                TextButton(onClick = { isRegister.value = !isRegister.value }) {
                    Text(
                        if (isRegister.value) {
                            "Zaten hesabın var mı? Giriş Yap"
                        } else {
                            "Hesabın yok mu? Kayıt Ol"
                        },
                        color = AuthCyan,
                        fontSize = 14.sp,
                    )
                }
            }
        }

        SnackbarHost(
            hostState = snackbar,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(16.dp),
        )
    }
}

@Composable
private fun AuthField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    keyboardType: KeyboardType,
    isPassword: Boolean = false,
    showPassword: Boolean = false,
    onTogglePassword: (() -> Unit)? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        placeholder = { Text(placeholder, color = AuthMuted) },
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        visualTransformation = if (isPassword && !showPassword) {
            PasswordVisualTransformation()
        } else {
            VisualTransformation.None
        },
        trailingIcon = if (isPassword && onTogglePassword != null) {
            {
                IconButton(onClick = onTogglePassword) {
                    Icon(
                        if (showPassword) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = "Şifreyi göster",
                        tint = AuthMuted,
                    )
                }
            }
        } else {
            null
        },
        shape = RoundedCornerShape(10.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedTextColor = AuthText,
            unfocusedTextColor = AuthText,
            cursorColor = AuthCyan,
            focusedBorderColor = AuthCyan.copy(alpha = 0.55f),
            unfocusedBorderColor = Color(0x4794A3B8),
            focusedContainerColor = AuthInputBg,
            unfocusedContainerColor = AuthInputBg,
            disabledContainerColor = AuthInputBg,
        ),
    )
}

private fun validateRegisterPassword(password: String): String? {
    if (password.length < 6) return "Şifre en az 6 karakter olmalı."
    if (!password.any { it.isLowerCase() }) return "Şifrede en az bir küçük harf (a-z) olmalı."
    if (!password.any { it.isUpperCase() }) return "Şifrede en az bir büyük harf (A-Z) olmalı."
    if (!password.any { it.isDigit() }) return "Şifrede en az bir sayı (0-9) olmalı."
    if (password.all { it.isLetterOrDigit() }) {
        return "Şifrede en az bir özel karakter olmalı (harf/rakam dışı herhangi bir işaret)."
    }
    return null
}
