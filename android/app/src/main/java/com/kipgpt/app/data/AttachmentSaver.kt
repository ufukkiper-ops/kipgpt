package com.kipgpt.app.data

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.IOException

object AttachmentSaver {
    fun saveToDownloads(
        context: Context,
        filename: String,
        bytes: ByteArray,
        mime: String,
    ): String {
        val safeName = filename.ifBlank { "ek" }
        val mimeType = mime.ifBlank { "application/octet-stream" }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, safeName)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/KipGPT")
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: throw IOException("Dosya oluşturulamadı")
            resolver.openOutputStream(uri)?.use { stream ->
                stream.write(bytes)
            } ?: throw IOException("Dosya yazılamadı")
            return safeName
        }

        val downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val dir = File(downloads, "KipGPT").apply { mkdirs() }
        val outFile = File(dir, safeName)
        outFile.outputStream().use { it.write(bytes) }
        return outFile.name
    }
}
