package com.openwebui.android

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okio.BufferedSource
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.UUID

class SessionStore(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "openwebui_session",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    var serverUrl: String
        get() = prefs.getString("server", "") ?: ""
        set(value) = prefs.edit().putString("server", value.trimEnd('/')).apply()
    var token: String
        get() = prefs.getString("token", "") ?: ""
        set(value) = prefs.edit().putString("token", value).apply()
    var email: String
        get() = prefs.getString("email", "") ?: ""
        set(value) = prefs.edit().putString("email", value).apply()
    fun clear() = prefs.edit().clear().apply()
}

data class ChatSummary(val id: String, val title: String)
data class ChatMessage(val role: String, val content: String)

data class AuthResult(val token: String, val name: String?, val email: String?)

class OpenWebUIClient(private val session: SessionStore) {
    private val http = OkHttpClient.Builder().build()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    private fun url(path: String) = session.serverUrl.trimEnd('/') + "/" + path.trimStart('/')
    private fun request(path: String): Request.Builder = Request.Builder().url(url(path)).apply {
        if (session.token.isNotBlank()) header("Authorization", "Bearer ${session.token}")
        header("Accept", "application/json")
    }

    suspend fun signIn(email: String, password: String): AuthResult = withContext(Dispatchers.IO) {
        val body = JSONObject().put("email", email).put("password", password)
            .toString().toRequestBody(jsonType)
        val response = http.newCall(request("api/v1/auths/signin").post(body).build()).execute()
        val text = response.body?.string().orEmpty()
        if (!response.isSuccessful) throw IOException("Sign in failed (${response.code}): $text")
        val json = JSONObject(text)
        val token = json.optString("token")
        if (token.isBlank()) throw IOException("Open WebUI did not return a session token")
        session.token = token
        session.email = json.optString("email", email)
        AuthResult(token, json.optString("name").ifBlank { null }, session.email)
    }

    suspend fun signOut() = withContext(Dispatchers.IO) {
        if (session.token.isNotBlank()) {
            runCatching { http.newCall(request("api/v1/auths/signout").post("{}".toRequestBody(jsonType)).build()).execute().close() }
        }
        session.clear()
    }

    suspend fun checkSession(): Boolean = withContext(Dispatchers.IO) {
        if (session.serverUrl.isBlank() || session.token.isBlank()) return@withContext false
        val response = http.newCall(request("api/v1/auths/").get().build()).execute()
        response.use { it.isSuccessful }
    }

    suspend fun models(): List<String> = withContext(Dispatchers.IO) {
        val response = http.newCall(request("api/models").get().build()).execute()
        val text = response.body?.string().orEmpty()
        if (!response.isSuccessful) throw IOException("Models request failed (${response.code})")
        val root = JSONObject(text)
        val array = root.optJSONArray("data") ?: JSONArray()
        buildList { for (i in 0 until array.length()) add(array.getJSONObject(i).optString("id")) }
    }

    suspend fun chats(): List<ChatSummary> = withContext(Dispatchers.IO) {
        val response = http.newCall(request("api/v1/chats/?page=1").get().build()).execute()
        val text = response.body?.string().orEmpty()
        if (!response.isSuccessful) throw IOException("Chats request failed (${response.code})")
        val array = JSONArray(text)
        buildList {
            for (i in 0 until array.length()) {
                val item = array.getJSONObject(i)
                add(ChatSummary(item.optString("id"), item.optString("title").ifBlank { "New chat" }))
            }
        }
    }

    suspend fun chatHistory(id: String): List<ChatMessage> = withContext(Dispatchers.IO) {
        val response = http.newCall(request("api/v1/chats/$id").get().build()).execute()
        val text = response.body?.string().orEmpty()
        if (!response.isSuccessful) throw IOException("Chat request failed (${response.code})")
        val root = JSONObject(text)
        val messages = root.optJSONObject("chat")?.optJSONArray("messages") ?: root.optJSONArray("messages") ?: JSONArray()
        buildList {
            for (i in 0 until messages.length()) {
                val m = messages.getJSONObject(i)
                add(ChatMessage(m.optString("role"), m.optString("content")))
            }
        }
    }

    suspend fun streamChat(model: String, messages: List<ChatMessage>, chatId: String, onDelta: (String) -> Unit) = withContext(Dispatchers.IO) {
        val messageArray = JSONArray().apply { messages.forEach { put(JSONObject().put("role", it.role).put("content", it.content)) } }
        val payload = JSONObject()
            .put("model", model)
            .put("messages", messageArray)
            .put("stream", true)
            .put("chat_id", chatId)
            .toString()
        val response = http.newCall(
            request("api/chat/completions").post(payload.toRequestBody(jsonType)).header("Accept", "text/event-stream").build()
        ).execute()
        if (!response.isSuccessful) {
            val error = response.body?.string().orEmpty()
            response.close()
            throw IOException("Chat failed (${response.code}): $error")
        }
        response.use { parseSse(it.body?.source() ?: throw IOException("Empty stream"), onDelta) }
    }

    private fun parseSse(source: BufferedSource, onDelta: (String) -> Unit) {
        while (!source.exhausted()) {
            val line = source.readUtf8Line() ?: break
            if (!line.startsWith("data:")) continue
            val data = line.removePrefix("data:").trim()
            if (data == "[DONE]") break
            runCatching {
                val obj = JSONObject(data)
                val delta = obj.optJSONArray("choices")?.optJSONObject(0)?.optJSONObject("delta")?.optString("content")
                if (!delta.isNullOrEmpty()) onDelta(delta)
            }
        }
    }

    fun newChatId(): String = UUID.randomUUID().toString()
}
