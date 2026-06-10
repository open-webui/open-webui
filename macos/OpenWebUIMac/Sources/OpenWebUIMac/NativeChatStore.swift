import Foundation
import OpenWebUIMacCore

struct NativeChatSession: Identifiable, Equatable {
    let id: UUID
    var title: String
    var messages: [NativeChatMessage]
    var createdAt: Date

    init(
        id: UUID = UUID(),
        title: String = "New Chat",
        messages: [NativeChatMessage] = [],
        createdAt: Date = Date()
    ) {
        self.id = id
        self.title = title
        self.messages = messages
        self.createdAt = createdAt
    }

    var preview: String {
        messages.last?.content ?? "Start a native Open WebUI conversation"
    }
}

struct NativeChatMessage: Identifiable, Equatable {
    let id: UUID
    var role: NativeChatRole
    var content: String
    var createdAt: Date

    init(id: UUID = UUID(), role: NativeChatRole, content: String, createdAt: Date = Date()) {
        self.id = id
        self.role = role
        self.content = content
        self.createdAt = createdAt
    }
}

enum NativeChatRole: String, Equatable {
    case user
    case assistant
    case system

    var title: String {
        switch self {
        case .user:
            return "You"
        case .assistant:
            return "Open WebUI"
        case .system:
            return "System"
        }
    }

    var apiRole: String {
        rawValue
    }
}

@MainActor
final class NativeChatStore: ObservableObject {
    @Published var sessions: [NativeChatSession]
    @Published var selectedSessionID: NativeChatSession.ID?
    @Published var models: [OpenWebUIModel] = []
    @Published var selectedModelID = ""
    @Published var composerText = ""
    @Published var isLoadingModels = false
    @Published var isSending = false
    @Published var errorMessage: String?

    init() {
        let session = NativeChatSession()
        self.sessions = [session]
        self.selectedSessionID = session.id
    }

    var selectedSession: NativeChatSession? {
        guard let selectedSessionID else {
            return sessions.first
        }
        return sessions.first { $0.id == selectedSessionID }
    }

    var selectedModel: OpenWebUIModel? {
        models.first { $0.id == selectedModelID }
    }

    func newChat() {
        let session = NativeChatSession()
        sessions.insert(session, at: 0)
        selectedSessionID = session.id
        composerText = ""
        errorMessage = nil
    }

    func loadModels(settings: OpenWebUISettings) async {
        guard !isLoadingModels else {
            return
        }

        isLoadingModels = true
        errorMessage = nil

        do {
            let fetchedModels = try await OpenWebUIAPIClient(settings: settings).fetchModels()
            models = fetchedModels
            if selectedModelID.isEmpty || !fetchedModels.contains(where: { $0.id == selectedModelID }) {
                selectedModelID = fetchedModels.first?.id ?? ""
            }
        } catch {
            models = []
            selectedModelID = ""
            errorMessage = error.localizedDescription
        }

        isLoadingModels = false
    }

    func sendComposer(settings: OpenWebUISettings) async {
        let prompt = composerText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !prompt.isEmpty, !isSending else {
            return
        }

        guard !selectedModelID.isEmpty else {
            errorMessage = "Select a model before sending a message."
            return
        }

        guard let sessionIndex = selectedSessionIndex else {
            return
        }

        let userMessage = NativeChatMessage(role: .user, content: prompt)
        sessions[sessionIndex].messages.append(userMessage)
        if sessions[sessionIndex].title == "New Chat" {
            sessions[sessionIndex].title = prompt.chatTitle
        }

        composerText = ""
        isSending = true
        errorMessage = nil

        do {
            let payloadMessages = sessions[sessionIndex].messages.map {
                OpenWebUIChatPayloadMessage(role: $0.role.apiRole, content: $0.content)
            }
            let response = try await OpenWebUIAPIClient(settings: settings)
                .sendChatCompletion(model: selectedModelID, messages: payloadMessages)
            let assistantMessage = NativeChatMessage(role: .assistant, content: response.content)

            if let updatedIndex = selectedSessionIndex {
                sessions[updatedIndex].messages.append(assistantMessage)
            }
        } catch {
            errorMessage = error.localizedDescription
            if let updatedIndex = selectedSessionIndex {
                sessions[updatedIndex].messages.append(
                    NativeChatMessage(role: .system, content: error.localizedDescription)
                )
            }
        }

        isSending = false
    }

    private var selectedSessionIndex: Int? {
        guard let selectedSessionID else {
            return sessions.indices.first
        }
        return sessions.firstIndex { $0.id == selectedSessionID }
    }
}

private extension String {
    var chatTitle: String {
        let words = split(separator: " ").prefix(8).joined(separator: " ")
        if words.count > 48 {
            return String(words.prefix(45)) + "..."
        }
        return words.isEmpty ? "New Chat" : words
    }
}
