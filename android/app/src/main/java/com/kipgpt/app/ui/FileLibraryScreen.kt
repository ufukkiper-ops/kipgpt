package com.kipgpt.app.ui

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.AttachmentSaver
import com.kipgpt.app.data.LibraryFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FileLibraryScreen(
    apiClient: ApiClient,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val files = remember { mutableStateOf<List<LibraryFile>>(emptyList()) }
    val loading = remember { mutableStateOf(true) }
    val refreshing = remember { mutableStateOf(false) }
    val uploading = remember { mutableStateOf(false) }
    val note = remember { mutableStateOf("") }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    fun formatSize(bytes: Int): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            else -> String.format("%.1f MB", bytes / (1024f * 1024f))
        }
    }

    fun load(showSpinner: Boolean = true) {
        scope.launch {
            if (showSpinner) loading.value = true
            try {
                files.value = apiClient.api.files().files
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Dosyalar yüklenemedi")
            } finally {
                loading.value = false
                refreshing.value = false
            }
        }
    }

    LaunchedEffect(Unit) { load() }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            uploading.value = true
            try {
                val (filename, bytes, mime) = withContext(Dispatchers.IO) {
                    readUriBytes(context.contentResolver, uri)
                }
                if (bytes.size > 15 * 1024 * 1024) {
                    snackbar.showSnackbar("Dosya 15 MB sınırını aşıyor")
                    return@launch
                }
                val part = MultipartBody.Part.createFormData(
                    "file",
                    filename,
                    bytes.toRequestBody((mime.ifBlank { "application/octet-stream" }).toMediaTypeOrNull()),
                )
                val noteBody = note.value.trim().toRequestBody("text/plain".toMediaTypeOrNull())
                apiClient.api.uploadFile(part, noteBody)
                note.value = ""
                snackbar.showSnackbar("Yüklendi: $filename")
                load(showSpinner = false)
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Yükleme başarısız")
            } finally {
                uploading.value = false
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("Dosyalarım") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = refreshing.value,
            onRefresh = {
                refreshing.value = true
                load(showSpinner = false)
            },
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
            ) {
                Text(
                    "AI ile mail yazarken “şu dosyayı ekle” diyebilirsiniz.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = note.value,
                    onValueChange = { note.value = it },
                    label = { Text("Not (ör. fatura, teklif)") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = {
                        picker.launch(
                            arrayOf(
                                "application/pdf",
                                "image/*",
                                "text/*",
                                "application/msword",
                                "application/vnd.openxmlformats-officedocument.*",
                                "application/vnd.ms-excel",
                                "*/*",
                            ),
                        )
                    },
                    enabled = !uploading.value,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Filled.UploadFile, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(if (uploading.value) "Yükleniyor..." else "Dosya yükle")
                }

                Spacer(Modifier.height(16.dp))

                when {
                    loading.value -> CircularProgressIndicator()
                    files.value.isEmpty() -> Text("Henüz dosya yok.")
                    else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(files.value, key = { it.id }) { file ->
                            Card(modifier = Modifier.fillMaxWidth()) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(file.filename, style = MaterialTheme.typography.titleMedium)
                                        Text(
                                            buildString {
                                                append(formatSize(file.size))
                                                if (file.note.isNotBlank()) append(" · ${file.note}")
                                            },
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                    Row {
                                        IconButton(onClick = {
                                            scope.launch {
                                                try {
                                                    val saved = withContext(Dispatchers.IO) {
                                                        val body = apiClient.api.downloadLibraryFile(file.id)
                                                        body.use { response ->
                                                            val bytes = response.bytes()
                                                            AttachmentSaver.saveToDownloads(
                                                                context = context,
                                                                filename = file.filename,
                                                                bytes = bytes,
                                                                mime = file.mimetype,
                                                            )
                                                        }
                                                    }
                                                    snackbar.showSnackbar("İndirildi: $saved")
                                                } catch (e: Exception) {
                                                    snackbar.showSnackbar(e.message ?: "İndirilemedi")
                                                }
                                            }
                                        }) {
                                            Icon(Icons.Filled.Download, contentDescription = "İndir")
                                        }
                                        IconButton(onClick = {
                                            scope.launch {
                                                try {
                                                    apiClient.api.deleteFile(file.id)
                                                    load(showSpinner = false)
                                                } catch (e: Exception) {
                                                    snackbar.showSnackbar(e.message ?: "Silinemedi")
                                                }
                                            }
                                        }) {
                                            Icon(Icons.Filled.Delete, contentDescription = "Sil")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

internal fun readUriBytes(
    resolver: ContentResolver,
    uri: Uri,
): Triple<String, ByteArray, String> {
    var filename = "dosya"
    resolver.query(uri, null, null, null, null)?.use { cursor ->
        val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        if (cursor.moveToFirst() && nameIndex >= 0) {
            filename = cursor.getString(nameIndex) ?: filename
        }
    }
    val mime = resolver.getType(uri) ?: "application/octet-stream"
    val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
        ?: throw IllegalArgumentException("Dosya okunamadı")
    return Triple(filename, bytes, mime)
}

internal fun bytesToBase64(bytes: ByteArray): String =
    Base64.encodeToString(bytes, Base64.NO_WRAP)
