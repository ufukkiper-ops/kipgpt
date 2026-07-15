package com.kipgpt.app.data

import android.content.ContentValues
import android.content.Context
import android.os.Environment
import android.provider.MediaStore
import java.io.IOException

object AttachmentSaver {
    fun saveToDownloads(
        context: Context,
        filename: String,
        bytes: ByteArray,
        mime: String,
    ): String {
        val safeName = filename.ifBlank { "ek" }
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, safeName)
            put(MediaStore.Downloads.MIME_TYPE, mime.ifBlank { "application/octet-stream" })
            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/KipAsistan")
        }

        val resolver = context.contentResolver
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw IOException("Dosya oluşturulamadı")

        resolver.openOutputStream(uri)?.use { stream ->
            stream.write(bytes)
        } ?: throw IOException("Dosya yazılamadı")

        return safeName
    }
}
