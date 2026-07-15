package com.kipgpt.app.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.kipgpt.app.data.ChatMessage
import com.kipgpt.app.data.SpeechHelper
import kotlinx.coroutines.delay

private val UserBubbleBlue = Color(0xFF2563EB)
private val BotBubbleBg = Color(0xFFFFFFFF)
private val BotBubbleBorder = Color(0xFFE5E7EB)
private val BotText = Color(0xFF111827)

@Composable
fun AiThinkingStatus(
    modifier: Modifier = Modifier,
) {
    val labels = listOf("Düşünüyor", "Hazırlıyor")
    val labelIndex = remember { mutableIntStateOf(0) }
    val infinite = rememberInfiniteTransition(label = "ai-dots")
    val dotAlpha by infinite.animateFloat(
        initialValue = 0.2f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "dot-alpha",
    )

    LaunchedEffect(Unit) {
        while (true) {
            delay(1600)
            labelIndex.intValue = (labelIndex.intValue + 1) % labels.size
        }
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
            .clip(CircleShape)
            .background(Color(0xFFEEF2FF))
            .border(1.dp, Color(0xFFDBEAFE), CircleShape)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(
            labels[labelIndex.intValue],
            color = Color(0xFF1D4ED8),
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.Medium,
        )
        Spacer(Modifier.width(2.dp))
        listOf(0, 1, 2).forEach { index ->
            val phaseAlpha = ((dotAlpha + index * 0.25f) % 1.2f).coerceIn(0.15f, 1f)
            Text(
                ".",
                color = Color(0xFF1D4ED8).copy(alpha = phaseAlpha),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
fun ChatMessageBubble(
    message: ChatMessage,
    speechHelper: SpeechHelper,
    modifier: Modifier = Modifier,
) {
    val isUser = message.role == "user"
    val bg = if (isUser) UserBubbleBlue else BotBubbleBg
    val fg = if (isUser) Color.White else BotText
    val shape = if (isUser) {
        RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomStart = 20.dp, bottomEnd = 6.dp)
    } else {
        RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomStart = 6.dp, bottomEnd = 20.dp)
    }

    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Row(
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
        ) {
            if (!isUser && speechHelper.isSpeakAvailable()) {
                IconButton(
                    onClick = {
                        if (speechHelper.isSpeaking()) {
                            speechHelper.stopSpeaking()
                        } else {
                            speechHelper.speak(message.content)
                        }
                    },
                    modifier = Modifier.size(36.dp),
                ) {
                    Icon(
                        if (speechHelper.isSpeaking()) Icons.Default.Stop else Icons.Default.VolumeUp,
                        contentDescription = "Dinle",
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
            }
            Column(
                modifier = Modifier
                    .widthIn(max = 300.dp)
                    .shadow(1.dp, shape)
                    .clip(shape)
                    .background(bg)
                    .then(
                        if (isUser) Modifier else Modifier.border(1.dp, BotBubbleBorder, shape),
                    )
                    .padding(horizontal = 14.dp, vertical = 10.dp),
            ) {
                Text(
                    if (isUser) "Sen" else "KipGPT",
                    color = if (isUser) Color.White.copy(alpha = 0.85f) else UserBubbleBlue,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
                message.file?.let { file ->
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(bottom = 6.dp),
                    ) {
                        Icon(
                            Icons.Default.InsertDriveFile,
                            contentDescription = null,
                            tint = fg.copy(alpha = 0.9f),
                            modifier = Modifier.size(16.dp),
                        )
                        Text(
                            file.name,
                            color = fg.copy(alpha = 0.9f),
                            style = MaterialTheme.typography.labelMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(start = 6.dp),
                        )
                    }
                }
                Text(
                    text = message.content,
                    color = fg,
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        }
    }
}
