import Foundation

public struct OpenWebUIAPIClient: Sendable {
    private let rootURL: URL
    private let apiToken: String
    private let session: URLSession

    public init(settings: OpenWebUISettings, session: URLSession = .shared) {
        let settings = settings.sanitized
        self.rootURL = settings.rootURL
        self.apiToken = settings.apiToken
        self.session = session
    }

    public func fetchModels() async throws -> [OpenWebUIModel] {
        let data = try await send(path: "api/models", method: "GET")
        return try JSONDecoder().decode(ModelListResponse.self, from: data).data
    }

    public func sendChatCompletion(
        model: String,
        messages: [OpenWebUIChatPayloadMessage]
    ) async throws -> OpenWebUIChatPayloadMessage {
        let request = ChatCompletionRequest(model: model, messages: messages, stream: false)
        let body = try JSONEncoder().encode(request)
        let data = try await send(path: "api/chat/completions", method: "POST", body: body)
        let response = try JSONDecoder().decode(ChatCompletionResponse.self, from: data)

        if let message = response.choices.first?.message {
            return message
        }

        throw OpenWebUIAPIError.emptyResponse
    }

    private func send(path: String, method: String, body: Data? = nil) async throws -> Data {
        let url = rootURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        if !apiToken.isEmpty {
            request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw OpenWebUIAPIError.invalidResponse
        }

        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8)
            throw OpenWebUIAPIError.http(statusCode: httpResponse.statusCode, message: message)
        }

        return data
    }
}

public struct OpenWebUIModel: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let name: String?

    public init(id: String, name: String? = nil) {
        self.id = id
        self.name = name
    }

    public var displayName: String {
        let trimmedName = name?.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedName?.isEmpty == false ? trimmedName! : id
    }
}

public struct OpenWebUIChatPayloadMessage: Codable, Equatable, Sendable {
    public let role: String
    public let content: String

    public init(role: String, content: String) {
        self.role = role
        self.content = content
    }
}

public enum OpenWebUIAPIError: LocalizedError, Equatable {
    case invalidResponse
    case http(statusCode: Int, message: String?)
    case emptyResponse

    public var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Open WebUI returned an invalid response."
        case .http(let statusCode, let message):
            if let message, !message.isEmpty {
                return "Open WebUI request failed with HTTP \(statusCode): \(message)"
            }
            return "Open WebUI request failed with HTTP \(statusCode)."
        case .emptyResponse:
            return "Open WebUI returned no assistant message."
        }
    }
}

private struct ModelListResponse: Decodable {
    let data: [OpenWebUIModel]
}

private struct ChatCompletionRequest: Encodable {
    let model: String
    let messages: [OpenWebUIChatPayloadMessage]
    let stream: Bool
}

private struct ChatCompletionResponse: Decodable {
    let choices: [Choice]

    struct Choice: Decodable {
        let message: OpenWebUIChatPayloadMessage?
    }
}
