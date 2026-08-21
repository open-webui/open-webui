package com.openwebui.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { OpenWebUIApp() }
    }
}

private enum class Screen { SERVER, LOGIN, CHATS, CHAT }

@OptIn(ExperimentalMaterial3Api::class)
@androidx.compose.runtime.Composable
private fun OpenWebUIApp() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val session = remember { SessionStore(context.applicationContext) }
    val client = remember { OpenWebUIClient(session) }
    var screen by remember { mutableStateOf(Screen.SERVER) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var server by remember { mutableStateOf(session.serverUrl) }
    var email by remember { mutableStateOf(session.email) }
    var password by remember { mutableStateOf("") }
    var chats by remember { mutableStateOf<List<ChatSummary>>(emptyList()) }
    var selectedChat by remember { mutableStateOf<ChatSummary?>(null) }
    var models by remember { mutableStateOf<List<String>>(emptyList()) }

    LaunchedEffect(Unit) {
        if (session.serverUrl.isNotBlank() && session.token.isNotBlank()) {
            loading = true
            runCatching {
                if (client.checkSession()) {
                    models = client.models()
                    chats = client.chats()
                    screen = Screen.CHATS
                } else session.clear()
            }.onFailure { error = it.message }
            loading = false
        }
    }

    MaterialTheme {
        Surface(Modifier.fillMaxSize()) {
            when (screen) {
                Screen.SERVER -> ServerScreen(server, { server = it }, loading, error) {
                    session.serverUrl = server.trim().removeSuffix("/")
                    error = null
                    screen = Screen.LOGIN
                }
                Screen.LOGIN -> LoginScreen(
                    server = session.serverUrl,
                    email = email,
                    password = password,
                    loading = loading,
                    error = error,
                    onEmail = { email = it },
                    onPassword = { password = it },
                    onBack = { screen = Screen.SERVER },
                    onLogin = {
                        loading = true; error = null
                        kotlinx.coroutines.MainScope().launch {
                            runCatching {
                                client.signIn(email.trim(), password)
                                models = client.models()
                                chats = client.chats()
                                screen = Screen.CHATS
                            }.onFailure { error = it.message }
                            loading = false
                        }
                    }
                )
                Screen.CHATS -> ChatListScreen(
                    chats = chats,
                    models = models,
                    onNewChat = { selectedChat = ChatSummary(client.newChatId(), "New chat"); screen = Screen.CHAT },
                    onOpenChat = { selectedChat = it; screen = Screen.CHAT },
                    onLogout = {
                        loading = true
                        kotlinx.coroutines.MainScope().launch {
                            client.signOut(); loading = false; screen = Screen.SERVER
                        }
                    }
                )
                Screen.CHAT -> selectedChat?.let { chat ->
                    ChatScreen(
                        client = client,
                        chat = chat,
                        models = models,
                        onBack = { screen = Screen.CHATS },
                        onRefresh = { chats = runCatching { client.chats() }.getOrDefault(chats) }
                    )
                }
            }
        }
    }
}

@Composable
private fun ServerScreen(server: String, onServer: (String) -> Unit, loading: Boolean, error: String?, onContinue: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Open WebUI", style = MaterialTheme.typography.headlineLarge)
        Spacer(Modifier.height(8.dp))
        Text("Connect this Android client to your Open WebUI server.")
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(server, onServer, Modifier.fillMaxWidth(), label = { Text("Server URL") }, singleLine = true, placeholder = { Text("https://your-open-webui.example") })
        Spacer(Modifier.height(16.dp))
        Button(onClick = onContinue, enabled = server.startsWith("https://") && !loading, Modifier.fillMaxWidth()) { Text("Continue") }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp)) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LoginScreen(server: String, email: String, password: String, loading: Boolean, error: String?, onEmail: (String) -> Unit, onPassword: (String) -> Unit, onBack: () -> Unit, onLogin: () -> Unit) {
    Scaffold(topBar = { TopAppBar(title = { Text("Sign in") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null) } }) }) { padding ->
        Column(Modifier.padding(padding).padding(24.dp), verticalArrangement = Arrangement.Center) {
            Text(server, style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(email, onEmail, Modifier.fillMaxWidth(), label = { Text("Email") }, singleLine = true, keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next))
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(password, onPassword, Modifier.fillMaxWidth(), label = { Text("Password") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done), keyboardActions = KeyboardActions(onDone = { onLogin() }))
            Spacer(Modifier.height(16.dp))
            Button(onClick = onLogin, enabled = email.isNotBlank() && password.isNotBlank() && !loading, Modifier.fillMaxWidth()) {
                if (loading) CircularProgressIndicator(modifier = Modifier.width(20.dp).height(20.dp)) else Text("Sign in")
            }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp)) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatListScreen(chats: List<ChatSummary>, models: List<String>, onNewChat: () -> Unit, onOpenChat: (ChatSummary) -> Unit, onLogout: () -> Unit) {
    Scaffold(topBar = { TopAppBar(title = { Text("Chats") }, actions = { IconButton(onClick = onNewChat) { Icon(Icons.Default.Add, "New chat") }; IconButton(onClick = onLogout) { Icon(Icons.Default.Logout, "Sign out") } }) }) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            if (models.isNotEmpty()) Text("${models.size} model(s) available", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.labelLarge)
            if (chats.isEmpty()) Text("No conversations yet. Start a new chat.", modifier = Modifier.padding(16.dp))
            LazyColumn(Modifier.fillMaxSize()) { items(chats, key = { it.id }) { chat -> OutlinedButton(onClick = { onOpenChat(chat) }, modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp)) { Text(chat.title, modifier = Modifier.weight(1f)) } } }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatScreen(client: OpenWebUIClient, chat: ChatSummary, models: List<String>, onBack: () -> Unit, onRefresh: () -> Unit) {
    val messages = remember { mutableStateListOf<ChatMessage>() }
    var input by remember { mutableStateOf("") }
    var selectedModel by remember(models) { mutableStateOf(models.firstOrNull().orEmpty()) }
    var streaming by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    val listState = rememberLazyListState()

    LaunchedEffect(chat.id) {
        if (chat.title != "New chat") {
            runCatching { messages.addAll(client.chatHistory(chat.id)) }.onFailure { error = it.message }
        }
    }
    LaunchedEffect(messages.size) { if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex) }

    fun send() {
        val text = input.trim()
        if (text.isEmpty() || selectedModel.isEmpty() || streaming) return
        input = ""
        messages.add(ChatMessage("user", text))
        streaming = true; error = null
        messages.add(ChatMessage("assistant", ""))
        scope.launch {
            runCatching { client.streamChat(selectedModel, messages.dropLast(1), chat.id) { delta ->
                androidx.compose.runtime.snapshots.Snapshot.withMutableSnapshot {
                    val last = messages.lastIndex
                    messages[last] = ChatMessage("assistant", messages[last].content + delta)
                }
            } }.onFailure { error = it.message; messages.removeAt(messages.lastIndex) }
            streaming = false
            onRefresh()
        }
    }

    Scaffold(topBar = { TopAppBar(title = { Text(chat.title) }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, null) } }) }, bottomBar = {
        Column(Modifier.navigationBarsPadding().padding(8.dp)) {
            if (models.size > 1) OutlinedTextField(selectedModel, { selectedModel = it }, Modifier.fillMaxWidth(), label = { Text("Model") }, singleLine = true)
            Row(verticalAlignment = Alignment.Bottom, modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(input, { input = it }, Modifier.weight(1f), label = { Text("Message") }, enabled = !streaming, maxLines = 5, keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send), keyboardActions = KeyboardActions(onSend = { send() }))
                Spacer(Modifier.width(8.dp)); IconButton(onClick = { send() }, enabled = input.isNotBlank() && !streaming) { Icon(Icons.Default.Send, "Send") }
            }
        }
    }) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            LazyColumn(state = listState, modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp)) {
                items(messages) { message ->
                    Surface(tonalElevation = 2.dp, shape = MaterialTheme.shapes.medium, modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text(message.role.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.labelMedium)
                            Spacer(Modifier.height(4.dp))
                            Text(message.content, fontFamily = if (message.content.contains("```")) FontFamily.Monospace else FontFamily.Default)
                        }
                    }
                }
            }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(12.dp)) }
        }
    }
}
