package com.stella.connect.ui

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.SolidColor
import android.content.Intent
import android.net.Uri
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.stella.connect.core.AgentStateStore
import com.stella.connect.core.ChatMessage
import com.stella.connect.core.OrbState
import com.stella.connect.core.AgentHeadState
import com.stella.connect.ui.theme.StellaTheme
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onSendMessage: (String) -> Unit,
    bottomInset: Dp = 0.dp,
    enableVoiceInput: Boolean = true,
    onVoiceStateChanged: ((OrbState) -> Unit)? = null,
    onOpenSettings: () -> Unit = {},
) {
    val chatHistory by AgentStateStore.chatHistory.collectAsState()
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val haptic = LocalHapticFeedback.current
    val context = LocalContext.current

    var inputText by remember { mutableStateOf("") }
    var attached by remember { mutableStateOf("") }

    var voiceModeActive by remember { mutableStateOf(false) }
    var voiceState by remember { mutableStateOf(OrbState.IDLE) }
    var agentHeadState by remember { mutableStateOf(AgentHeadState.IDLE) }

    LaunchedEffect(voiceState) {
        when (voiceState) {
            OrbState.LISTENING -> agentHeadState = AgentHeadState.LISTENING
            OrbState.SPEAKING -> agentHeadState = AgentHeadState.SPEAKING
            else -> agentHeadState = AgentHeadState.IDLE
        }
    }

    val attachLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: Exception) {}
            // Just store filename for context attachment, no model download
            val name = try {
                val c = context.contentResolver.query(uri, null, null, null, null)
                c?.use {
                    val idx = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    if (idx >= 0 && it.moveToFirst()) it.getString(idx) else uri.lastPathSegment
                } ?: uri.lastPathSegment
            } catch (_: Exception) { uri.lastPathSegment }
            attached = name ?: ""
        }
    }

    val submit: () -> Unit = {
        val typed = inputText.trim()
        if (typed.isNotEmpty()) {
            val payload = if (attached.isNotEmpty()) "$typed\n[attached: $attached]" else typed
            onSendMessage(payload)
            inputText = ""
            attached = ""
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
        }
    }

    LaunchedEffect(chatHistory.size) {
        if (chatHistory.isNotEmpty()) {
            listState.animateScrollToItem(chatHistory.size - 1)
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            WorkspacesDrawerContent(
                onClose = { coroutineScope.launch { drawerState.close() } },
                onSelectWorkspace = { /* TODO: switch workspace */ },
                onNewWorkspace = { /* TODO: create new workspace */ }
            )
        }
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(StellaTheme.colors.bg)
            )
            HolographicBackground()
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(StellaTheme.colors.bg.copy(alpha = 0.78f))
                    .padding(bottom = bottomInset)
            ) {
                TopAppBar(
                    navigationIcon = {
                        IconButton(onClick = { coroutineScope.launch { drawerState.open() } }) {
                            Icon(
                                Icons.Default.Menu,
                                contentDescription = "Open drawer",
                                tint = StellaTheme.colors.textPrimary,
                                modifier = Modifier.size(22.dp)
                            )
                        }
                    },
                    title = {
                        Text(
                            text = "Stella",
                            color = StellaTheme.colors.textPrimary,
                            fontWeight = FontWeight.Black,
                            style = MaterialTheme.typography.titleLarge,
                        )
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent,
                        titleContentColor = StellaTheme.colors.textPrimary,
                        actionIconContentColor = StellaTheme.colors.textPrimary,
                    ),
                    actions = {
                        IconButton(onClick = onOpenSettings) {
                            Icon(
                                Icons.Default.Settings,
                                contentDescription = "Open settings",
                                tint = StellaTheme.colors.textPrimary,
                                modifier = Modifier.size(22.dp),
                            )
                        }
                    }
                )

                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                        .padding(horizontal = 16.dp),
                    state = listState,
                    contentPadding = PaddingValues(vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    if (chatHistory.isEmpty()) {
                        item {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 64.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "S  T  E  L  L  A",
                                    color = StellaTheme.colors.textPrimary,
                                    fontWeight = FontWeight.Black,
                                    fontSize = 22.sp,
                                    letterSpacing = 6.sp,
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Start a conversation to begin",
                                    color = StellaTheme.colors.textMuted,
                                    fontSize = 13.sp,
                                )
                            }
                        }
                    }
                    items(
                        items = chatHistory,
                        key = { it.id },
                    ) { message ->
                        Box(modifier = Modifier.testTag("bubble_${message.id}")) {
                            ChatMessageBubble(message = message)
                        }
                    }
                    // if (chatHistory.any { it.status.contains("think", ignoreCase = true) }) {
                    //     TypingIndicator()
                    // }
                }
            }

            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = bottomInset + 12.dp, start = 16.dp, end = 16.dp, top = 8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(StellaTheme.colors.surfaceRaised)
                        .clip(RoundedCornerShape(24.dp))
                        .border(1.dp, StellaTheme.colors.border)
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(
                        onClick = { attachLauncher.launch(arrayOf("*/*")) },
                        modifier = Modifier
                            .size(38.dp)
                            .clip(CircleShape)
                            .background(StellaTheme.colors.surface),
                    ) {
                        Icon(
                            Icons.Default.Add,
                            contentDescription = "Attach file",
                            tint = StellaTheme.colors.textPrimary,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        if (attached.isNotEmpty()) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .padding(bottom = 4.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(StellaTheme.colors.primary.copy(alpha = 0.15f))
                                    .padding(horizontal = 8.dp, vertical = 2.dp),
                            ) {
                                Text(
                                    text = "\uD83D\uDCCE $attached",
                                    color = StellaTheme.colors.primary,
                                    fontSize = 12.sp,
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "\u2715",
                                    color = StellaTheme.colors.textSecondary,
                                    fontSize = 12.sp,
                                    modifier = Modifier
                                        .clip(CircleShape)
                                        .background(StellaTheme.colors.glassBorder)
                                        .clickable { attached = "" }
                                        .padding(2.dp),
                                )
                            }
                        }
                        OutlinedTextField(
                            value = inputText,
                            onValueChange = { newText: String -> inputText = newText },
                            modifier = Modifier.fillMaxWidth(),
                            placeholder = { Text("Message Stella...", color = StellaTheme.colors.textMuted) },
                            colors = androidx.compose.material3.TextFieldDefaults.colors(
                                focusedIndicatorColor = StellaTheme.colors.focusRing.copy(alpha = 0.4f),
                                unfocusedIndicatorColor = Color.Transparent,
                                cursorColor = StellaTheme.colors.textPrimary,
                                focusedTextColor = StellaTheme.colors.textPrimary,
                                unfocusedTextColor = StellaTheme.colors.textPrimary,
                                focusedContainerColor = Color.Transparent,
                                unfocusedContainerColor = Color.Transparent,
                            ),
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                            keyboardActions = KeyboardActions(onSend = { submit() }),
                            maxLines = 4,
                            singleLine = false,
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            voiceModeActive = !voiceModeActive
                            voiceState = if (voiceModeActive) OrbState.LISTENING else OrbState.IDLE
                        },
                        modifier = Modifier.size(42.dp)
                    ) {
                        Icon(
                            Icons.Default.Mic,
                            contentDescription = "Voice",
                            tint = StellaTheme.colors.textPrimary,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(
                                Brush.radialGradient(
                                    listOf(
                                        StellaTheme.colors.tertiary.copy(alpha = 0.6f),
                                        StellaTheme.colors.secondary.copy(alpha = 0.6f),
                                        StellaTheme.colors.primary.copy(alpha = 0.27f),
                                    ),
                                    radius = 110f,
                                )
                            )
                            .border(1.5.dp, StellaTheme.colors.textPrimary.copy(alpha = 0.35f), CircleShape)
                            .padding(4.dp)
                            .clickable {
                                submit()
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            },
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Send",
                            tint = StellaTheme.colors.textPrimary,
                            modifier = Modifier.size(22.dp),
                        )
                    }
                }
            }
            if (voiceModeActive) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.7f))
                        .clickable { voiceModeActive = false; voiceState = OrbState.IDLE },
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            modifier = Modifier
                                .size(180.dp)
                                .clip(CircleShape)
                                .background(
                                    Brush.radialGradient(
                                        colors = listOf(
                                            StellaTheme.colors.primary.copy(alpha = 0.4f),
                                            StellaTheme.colors.secondary.copy(alpha = 0.2f),
                                            Color.Transparent
                                        )
                                    )
                                )
                                .border(2.dp, StellaTheme.colors.primary.copy(alpha = 0.5f), CircleShape)
                        )
                        Spacer(Modifier.height(24.dp))
                        Text(
                            text = when (voiceState) {
                                OrbState.LISTENING -> "Listening..."
                                OrbState.SPEAKING -> "Speaking..."
                                else -> "Voice mode"
                            },
                            color = StellaTheme.colors.textPrimary,
                            fontSize = 18.sp
                        )
                        Spacer(Modifier.height(16.dp))
                        Row {
                            TextButton(onClick = { /* mute */ }) { Text("Mute") }
                            Spacer(Modifier.width(16.dp))
                            TextButton(onClick = { voiceModeActive = false; voiceState = OrbState.IDLE }) { Text("Close") }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkspacesDrawerContent(
    onClose: () -> Unit,
    onSelectWorkspace: (String) -> Unit,
    onNewWorkspace: () -> Unit
) {
    val workspaces = listOf(
        "Personal",
        "Work",
        "Design Review",
        "Research"
    )
    Scaffold(
        containerColor = StellaTheme.colors.surface,
        topBar = {
            TopAppBar(
                title = { Text("Workspaces", color = StellaTheme.colors.textPrimary) },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Close",
                            tint = StellaTheme.colors.textPrimary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = StellaTheme.colors.surface
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = onNewWorkspace,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = StellaTheme.colors.primary)
            ) {
                Text("New Workspace")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Recent Workspaces",
                color = StellaTheme.colors.textMuted,
                fontSize = 12.sp,
                modifier = Modifier.padding(horizontal = 4.dp)
            )
            workspaces.forEach { ws ->
                ElevatedCard(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSelectWorkspace(ws) },
                    colors = CardDefaults.elevatedCardColors(containerColor = StellaTheme.colors.surfaceRaised)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Add,
                            contentDescription = null,
                            tint = StellaTheme.colors.textSecondary
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(ws, color = StellaTheme.colors.textPrimary)
                    }
                }
            }
        }
    }
}

@Composable
fun ChatMessageBubble(message: ChatMessage) {
    val isUser = message.role.lowercase(Locale.getDefault()) == "user"
    val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
    val timeStr = timeFormat.format(Date(message.timestamp))

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        if (!isUser) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary)
                    .border(1.dp, StellaTheme.colors.textPrimary.copy(alpha = 0.25f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "S",
                    color = StellaTheme.colors.onPrimary,
                    fontWeight = FontWeight.Black,
                    fontSize = 18.sp,
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
        }
        Column(
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
            modifier = Modifier.weight(1f, fill = false),
        ) {
            Box(
                modifier = Modifier
                    .clip(
                        RoundedCornerShape(
                            topStart = 16.dp,
                            topEnd = 16.dp,
                            bottomStart = if (isUser) 16.dp else 4.dp,
                            bottomEnd = if (isUser) 4.dp else 16.dp,
                        )
                    )
                    .background(
                        SolidColor(
                            if (isUser) StellaTheme.colors.bubbleUser
                            else StellaTheme.colors.bubbleStella
                        )
                    )
                    .border(
                        1.dp,
                        if (isUser) Color.Transparent
                        else StellaTheme.colors.border,
                        RoundedCornerShape(
                            topStart = 16.dp,
                            topEnd = 16.dp,
                            bottomStart = if (isUser) 16.dp else 4.dp,
                            bottomEnd = if (isUser) 4.dp else 16.dp,
                        )
                    )
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                ) {
                    Text(
                        text = message.text,
                        color = if (isUser) StellaTheme.colors.bubbleUserText else StellaTheme.colors.bubbleStellaText,
                        fontSize = 15.sp,
                        lineHeight = 22.sp,
                    )
                }
            Row(
                modifier = Modifier.padding(top = 4.dp, start = 4.dp, end = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = timeStr,
                    color = StellaTheme.colors.textMuted,
                    fontSize = 11.sp,
                )
                if (isUser && message.status.isNotEmpty()) {
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "\u2022 $message.status",
                        color = StellaTheme.colors.textMuted,
                        fontSize = 11.sp,
                    )
                }
                if (!isUser) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Copy",
                        color = StellaTheme.colors.primary,
                        fontSize = 11.sp,
                        modifier = Modifier.clickable { /* Copy to clipboard */ },
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Read aloud",
                        color = StellaTheme.colors.primary,
                        fontSize = 11.sp,
                        modifier = Modifier.clickable { /* Read aloud */ },
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Edit",
                        color = StellaTheme.colors.primary,
                        fontSize = 11.sp,
                        modifier = Modifier.clickable { /* Edit message */ },
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Retry",
                        color = StellaTheme.colors.primary,
                        fontSize = 11.sp,
                        modifier = Modifier.clickable { /* Retry message */ },
                    )
                }
            }
        }
    }
}

@Composable
fun TypingIndicator() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
    ) {
        Box(
            modifier = Modifier
                .size(12.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.35f))
        )
        Spacer(modifier = Modifier.width(8.dp))
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier
                .padding(vertical = 4.dp)
                .width(42.dp),
        ) {
            repeat(3) { index ->
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(
                            if (index % 2 == 0) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                StellaTheme.colors.textMuted
                            }
                        )
                    )
                }
            }
        }
    }
