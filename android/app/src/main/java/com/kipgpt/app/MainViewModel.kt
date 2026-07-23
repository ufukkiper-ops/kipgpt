package com.kipgpt.app

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.kipgpt.app.data.SessionManager
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed interface AuthState {
    data object Loading : AuthState
    data object LoggedOut : AuthState
    data class LoggedIn(val token: String) : AuthState
}

class MainViewModel(
    private val sessionManager: SessionManager,
) : ViewModel() {
    val authState = sessionManager.tokenFlow
        .map { token ->
            if (token.isNullOrBlank()) {
                AuthState.LoggedOut
            } else {
                AuthState.LoggedIn(token)
            }
        }
        .stateIn(viewModelScope, SharingStarted.Eagerly, AuthState.Loading)

    val baseUrl = sessionManager.baseUrlFlow.stateIn(
        viewModelScope,
        SharingStarted.Eagerly,
        SessionManager.DEFAULT_BASE_URL,
    )

    var showGuestSettings by mutableStateOf(false)
        private set

    fun openGuestSettings() {
        showGuestSettings = true
    }

    fun closeGuestSettings() {
        showGuestSettings = false
    }

    init {
        viewModelScope.launch {
            sessionManager.applyLocalServerDefaultIfNeeded()
            val url = sessionManager.baseUrlFlow.first()
            if (SessionManager.isPlaceholderLanUrl(url)) {
                showGuestSettings = true
            }
        }
    }

    suspend fun logout() {
        sessionManager.clearToken()
        showGuestSettings = false
    }

    class Factory(
        private val sessionManager: SessionManager,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            if (modelClass.isAssignableFrom(MainViewModel::class.java)) {
                return MainViewModel(sessionManager) as T
            }
            throw IllegalArgumentException("Unknown ViewModel class")
        }
    }
}
