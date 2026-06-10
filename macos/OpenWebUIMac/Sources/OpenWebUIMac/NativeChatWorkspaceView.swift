import OpenWebUIMacCore
import SwiftUI

struct NativeChatWorkspaceView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var store = NativeChatStore()

    var body: some View {
        GeometryReader { proxy in
            HSplitView {
                ChatSidebar(store: store)
                    .frame(minWidth: 220, idealWidth: 280, maxWidth: 340)

                ChatTranscriptPane(store: store)
                    .frame(minWidth: 440)

                if proxy.size.width >= 1080 {
                    ModelToolsInspector(store: store)
                        .frame(minWidth: 260, idealWidth: 320, maxWidth: 380)
                }
            }
        }
        .task(id: appState.service.status) {
            await refreshModelsIfReady()
        }
        .task(id: appState.settingsStore.settings) {
            await refreshModelsIfReady()
        }
    }

    private func refreshModelsIfReady() async {
        guard appState.service.status.isRunning else {
            return
        }
        await store.loadModels(settings: appState.settingsStore.settings)
    }
}

private struct ChatSidebar: View {
    @ObservedObject var store: NativeChatStore

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Open WebUI")
                    .font(.title3.bold())
                Spacer()
                Button {
                    store.newChat()
                } label: {
                    Image(systemName: "square.and.pencil")
                }
                .help("New Chat")
            }
            .padding(.horizontal, 16)
            .padding(.top, 16)

            Button {
                store.newChat()
            } label: {
                Label("New Chat", systemImage: "plus")
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, 16)

            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                Text("Search")
                    .foregroundStyle(.secondary)
                Spacer()
                Text("⌘K")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 12)
            .frame(height: 34)
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal, 16)

            List(selection: $store.selectedSessionID) {
                Section("Recent") {
                    ForEach(store.sessions) { session in
                        ChatSessionRow(session: session)
                            .tag(session.id)
                    }
                }

                Section("Folders") {
                    Label("Engineering", systemImage: "folder")
                    Label("Product", systemImage: "folder")
                    Label("Research", systemImage: "folder")
                }
            }
            .listStyle(.sidebar)

            HStack(spacing: 10) {
                Circle()
                    .fill(.blue.gradient)
                    .frame(width: 30, height: 30)
                    .overlay(Text("OW").font(.caption2.bold()).foregroundStyle(.white))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Local Workspace")
                        .font(.callout.weight(.semibold))
                    Text("Native macOS client")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(16)
        }
        .background(.bar)
    }
}

private struct ChatSessionRow: View {
    let session: NativeChatSession

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(session.title)
                .lineLimit(1)
            Text(session.preview)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .padding(.vertical, 3)
    }
}

private struct ChatTranscriptPane: View {
    @EnvironmentObject private var appState: AppState
    @ObservedObject var store: NativeChatStore

    var body: some View {
        VStack(spacing: 0) {
            chatHeader

            Divider()

            if appState.service.status.isRunning {
                messages
            } else {
                NativeServicePlaceholder(status: appState.service.status, restart: appState.restart)
            }

            Divider()

            composer
        }
        .background(Color(nsColor: .textBackgroundColor))
    }

    private var chatHeader: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(store.selectedSession?.title ?? "New Chat")
                    .font(.title2.bold())
                    .lineLimit(1)
                Text("Native Open WebUI workspace")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Picker("Model", selection: $store.selectedModelID) {
                if store.models.isEmpty {
                    Text("No models").tag("")
                } else {
                    ForEach(store.models) { model in
                        Text(model.displayName).tag(model.id)
                    }
                }
            }
            .labelsHidden()
            .frame(width: 220)
            .disabled(store.models.isEmpty || store.isLoadingModels)

            ServiceStatusChip(status: appState.service.status)
        }
        .padding(.horizontal, 28)
        .padding(.vertical, 18)
    }

    private var messages: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 18) {
                    if store.selectedSession?.messages.isEmpty != false {
                        EmptyChatPrompt()
                    } else {
                        ForEach(store.selectedSession?.messages ?? []) { message in
                            NativeMessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                }
                .padding(.horizontal, 32)
                .padding(.vertical, 24)
            }
            .onChange(of: store.selectedSession?.messages.last?.id) { messageID in
                guard let messageID else {
                    return
                }
                withAnimation {
                    proxy.scrollTo(messageID, anchor: .bottom)
                }
            }
        }
    }

    private var composer: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let errorMessage = store.errorMessage {
                Label(errorMessage, systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(2)
            }

            HStack(alignment: .bottom, spacing: 12) {
                Button {} label: {
                    Image(systemName: "paperclip")
                }
                .help("Attach File")

                TextEditor(text: $store.composerText)
                    .font(.body)
                    .scrollContentBackground(.hidden)
                    .frame(minHeight: 56, maxHeight: 110)
                    .overlay(alignment: .topLeading) {
                        if store.composerText.isEmpty {
                            Text("Ask anything...")
                                .foregroundStyle(.tertiary)
                                .padding(.top, 8)
                                .padding(.leading, 4)
                                .allowsHitTesting(false)
                        }
                    }

                Button {
                    Task {
                        await store.sendComposer(settings: appState.settingsStore.settings)
                    }
                } label: {
                    Image(systemName: store.isSending ? "stop.fill" : "arrow.up")
                        .frame(width: 26, height: 26)
                }
                .buttonStyle(.borderedProminent)
                .clipShape(Circle())
                .disabled(store.isSending || store.composerText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .keyboardShortcut(.return, modifiers: .command)
                .help("Send")
            }
            .padding(12)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))

            Text("Open WebUI may produce inaccurate information.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .frame(maxWidth: .infinity, alignment: .center)
        }
        .padding(.horizontal, 28)
        .padding(.vertical, 18)
    }
}

private struct NativeMessageBubble: View {
    let message: NativeChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            avatar

            VStack(alignment: .leading, spacing: 8) {
                Text(message.role.title)
                    .font(.headline)

                Text(message.content)
                    .textSelection(.enabled)
                    .lineSpacing(3)
                    .padding(message.role == .user ? 12 : 0)
                    .background(message.role == .user ? Color.accentColor.opacity(0.10) : .clear)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
            }
            .frame(maxWidth: 720, alignment: .leading)

            Spacer(minLength: 0)
        }
    }

    private var avatar: some View {
        Circle()
            .fill(fillStyle)
            .frame(width: 34, height: 34)
            .overlay {
                Text(message.role == .user ? "You" : "OW")
                    .font(.caption2.bold())
                    .foregroundStyle(message.role == .assistant ? Color.primary : Color.white)
            }
    }

    private var fillStyle: AnyShapeStyle {
        switch message.role {
        case .user:
            return AnyShapeStyle(Color.accentColor.gradient)
        case .assistant:
            return AnyShapeStyle(Color(nsColor: .controlBackgroundColor).gradient)
        case .system:
            return AnyShapeStyle(Color.orange.opacity(0.18))
        }
    }
}

private struct EmptyChatPrompt: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Start a native Open WebUI chat")
                .font(.largeTitle.bold())
            Text("Choose a model, then send a message. The macOS app talks directly to the Open WebUI backend API.")
                .foregroundStyle(.secondary)
                .frame(maxWidth: 560, alignment: .leading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        .padding(.top, 120)
    }
}

private struct NativeServicePlaceholder: View {
    let status: OpenWebUIServiceStatus
    let restart: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: status.isRunning ? "checkmark.circle.fill" : "bolt.horizontal.circle")
                .font(.system(size: 44, weight: .semibold))
                .foregroundStyle(status.isRunning ? .green : .secondary)
            Text("Local service is \(status.title.lowercased())")
                .font(.title2.bold())
            Text("The native client will connect as soon as the Open WebUI backend is healthy.")
                .foregroundStyle(.secondary)
            Button {
                restart()
            } label: {
                Label("Restart Service", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct ModelToolsInspector: View {
    @EnvironmentObject private var appState: AppState
    @ObservedObject var store: NativeChatStore

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Model & Tools")
                .font(.title3.bold())

            inspectorSection("Model") {
                Picker("Model", selection: $store.selectedModelID) {
                    if store.models.isEmpty {
                        Text("No models loaded").tag("")
                    } else {
                        ForEach(store.models) { model in
                            Text(model.displayName).tag(model.id)
                        }
                    }
                }
                .labelsHidden()

                LabeledContent("Context length", value: "Backend default")
            }

            Divider()

            inspectorSection("Knowledge") {
                InspectorRow(icon: "books.vertical", title: "Company Docs", detail: "Ready")
                InspectorRow(icon: "doc.text.magnifyingglass", title: "API Reference", detail: "Ready")
                InspectorRow(icon: "folder", title: "Local Files", detail: "Off")
            }

            Divider()

            inspectorSection("Tools") {
                Toggle("Web Search", isOn: .constant(false))
                Toggle("Code Interpreter", isOn: .constant(false))
                Toggle("File Analysis", isOn: .constant(false))
            }

            Divider()

            inspectorSection("Local Service") {
                ServiceStatusChip(status: appState.service.status)
                Button {
                    Task {
                        await store.loadModels(settings: appState.settingsStore.settings)
                    }
                } label: {
                    Label("Refresh Models", systemImage: "arrow.clockwise")
                }
                .disabled(!appState.service.status.isRunning || store.isLoadingModels)
            }

            inspectorSection("Ollama Connection") {
                Label(appState.settingsStore.settings.sanitized.ollamaBaseURL, systemImage: "circle.fill")
                    .foregroundStyle(.green)
                    .font(.caption)
            }

            Spacer()
        }
        .padding(22)
        .background(.regularMaterial)
    }

    private func inspectorSection<Content: View>(
        _ title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
            content()
        }
    }
}

private struct InspectorRow: View {
    let icon: String
    let title: String
    let detail: String

    var body: some View {
        HStack {
            Label(title, systemImage: icon)
            Spacer()
            Text(detail)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

private struct ServiceStatusChip: View {
    let status: OpenWebUIServiceStatus

    var body: some View {
        Label(status.isRunning ? "Running locally" : status.title, systemImage: "circle.fill")
            .font(.caption.weight(.semibold))
            .lineLimit(1)
            .foregroundStyle(status.isRunning ? .green : .secondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.quaternary, in: Capsule())
    }
}
