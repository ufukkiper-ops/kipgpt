package com.kipgpt.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp

val InputActionButtonSize = 48.dp
val InputActionIconSize = 24.dp

private val SendButtonBlue = Color(0xFF1A73E8)
private val SendButtonDisabled = Color(0xFFDADCE0)

@Composable
fun RoundMicButton(
    listening: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    FilledTonalIconButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.size(InputActionButtonSize),
        colors = IconButtonDefaults.filledTonalIconButtonColors(
            containerColor = if (listening) {
                MaterialTheme.colorScheme.errorContainer
            } else {
                MaterialTheme.colorScheme.secondaryContainer
            },
        ),
    ) {
        Icon(
            imageVector = if (listening) Icons.Default.Stop else Icons.Default.Mic,
            contentDescription = "Sesle konuş",
            modifier = Modifier.size(InputActionIconSize),
            tint = if (listening) {
                MaterialTheme.colorScheme.error
            } else {
                MaterialTheme.colorScheme.onSecondaryContainer
            },
        )
    }
}

@Composable
fun RoundSendButton(
    enabled: Boolean,
    loading: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    contentDescription: String = "Gönder",
) {
    FilledIconButton(
        onClick = onClick,
        enabled = enabled && !loading,
        modifier = modifier.size(InputActionButtonSize),
        colors = IconButtonDefaults.filledIconButtonColors(
            containerColor = SendButtonBlue,
            contentColor = Color.White,
            disabledContainerColor = SendButtonDisabled,
            disabledContentColor = Color(0xFF9AA0A6),
        ),
    ) {
        if (loading) {
            CircularProgressIndicator(
                modifier = Modifier.size(InputActionIconSize),
                strokeWidth = 2.dp,
                color = MaterialTheme.colorScheme.onPrimary,
            )
        } else {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.Send,
                contentDescription = contentDescription,
                modifier = Modifier.size(InputActionIconSize),
            )
        }
    }
}

@Composable
fun RoundActionButton(
    icon: ImageVector,
    contentDescription: String,
    enabled: Boolean,
    loading: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    tonal: Boolean = false,
) {
    if (tonal) {
        FilledTonalIconButton(
            onClick = onClick,
            enabled = enabled && !loading,
            modifier = modifier.size(InputActionButtonSize),
            colors = IconButtonDefaults.filledTonalIconButtonColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
            ),
        ) {
            RoundActionIcon(icon, contentDescription, loading)
        }
    } else {
        FilledIconButton(
            onClick = onClick,
            enabled = enabled && !loading,
            modifier = modifier.size(InputActionButtonSize),
        ) {
            RoundActionIcon(icon, contentDescription, loading)
        }
    }
}

@Composable
private fun RoundActionIcon(
    icon: ImageVector,
    contentDescription: String,
    loading: Boolean,
) {
    if (loading) {
        CircularProgressIndicator(
            modifier = Modifier.size(InputActionIconSize),
            strokeWidth = 2.dp,
        )
    } else {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            modifier = Modifier.size(InputActionIconSize),
        )
    }
}

@Composable
fun RoundAttachButton(
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    IconButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.size(InputActionButtonSize),
    ) {
        Icon(
            imageVector = Icons.Default.AttachFile,
            contentDescription = "Dosya ekle",
            modifier = Modifier.size(InputActionIconSize),
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
fun ChatStyleInputBar(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    enabled: Boolean,
    listening: Boolean,
    sendEnabled: Boolean,
    sending: Boolean,
    onMicClick: () -> Unit,
    onSendClick: () -> Unit,
    modifier: Modifier = Modifier,
    onAttachClick: (() -> Unit)? = null,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 4.dp, end = 6.dp, top = 4.dp, bottom = 4.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            if (onAttachClick != null) {
                RoundAttachButton(
                    enabled = enabled,
                    onClick = onAttachClick,
                )
            }
            TextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier
                    .weight(1f)
                    .widthIn(min = 0.dp),
                placeholder = { Text(placeholder) },
                enabled = enabled,
                maxLines = 4,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    disabledContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent,
                ),
            )
            Row(
                modifier = Modifier
                    .wrapContentWidth()
                    .padding(start = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RoundMicButton(
                    listening = listening,
                    enabled = enabled,
                    onClick = onMicClick,
                )
                RoundSendButton(
                    enabled = sendEnabled,
                    loading = sending,
                    onClick = onSendClick,
                )
            }
        }
    }
}

@Composable
fun InlineInputActionBar(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    enabled: Boolean,
    modifier: Modifier = Modifier,
    minLines: Int = 1,
    maxLines: Int = 4,
    trailingContent: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 4.dp, end = 6.dp, top = 4.dp, bottom = 4.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            TextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier
                    .weight(1f)
                    .widthIn(min = 0.dp),
                placeholder = { Text(placeholder) },
                enabled = enabled,
                minLines = minLines,
                maxLines = maxLines,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    disabledContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent,
                ),
            )
            Row(
                modifier = Modifier
                    .wrapContentWidth()
                    .padding(start = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                trailingContent()
            }
        }
    }
}
