import Foundation

public struct OpenWebUISettings: Codable, Equatable, Sendable {
    public static let defaultHost = "127.0.0.1"
    public static let defaultPort = 8080
    public static let defaultServiceCommand = "open-webui serve"
    public static let defaultOllamaBaseURL = "http://127.0.0.1:11434"

    public var host: String
    public var port: Int
    public var serviceCommand: String
    public var ollamaBaseURL: String
    public var dataDirectory: String
    public var apiToken: String
    public var autoStartService: Bool
    public var stopServiceOnQuit: Bool

    public init(
        host: String = Self.defaultHost,
        port: Int = Self.defaultPort,
        serviceCommand: String = Self.defaultServiceCommand,
        ollamaBaseURL: String = Self.defaultOllamaBaseURL,
        dataDirectory: String = Self.defaultDataDirectory,
        apiToken: String = "",
        autoStartService: Bool = true,
        stopServiceOnQuit: Bool = true
    ) {
        self.host = host
        self.port = port
        self.serviceCommand = serviceCommand
        self.ollamaBaseURL = ollamaBaseURL
        self.dataDirectory = dataDirectory
        self.apiToken = apiToken
        self.autoStartService = autoStartService
        self.stopServiceOnQuit = stopServiceOnQuit
    }

    private enum CodingKeys: String, CodingKey {
        case host
        case port
        case serviceCommand
        case ollamaBaseURL
        case dataDirectory
        case apiToken
        case autoStartService
        case stopServiceOnQuit
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            host: try container.decodeIfPresent(String.self, forKey: .host) ?? Self.defaultHost,
            port: try container.decodeIfPresent(Int.self, forKey: .port) ?? Self.defaultPort,
            serviceCommand: try container.decodeIfPresent(String.self, forKey: .serviceCommand)
                ?? Self.defaultServiceCommand,
            ollamaBaseURL: try container.decodeIfPresent(String.self, forKey: .ollamaBaseURL)
                ?? Self.defaultOllamaBaseURL,
            dataDirectory: try container.decodeIfPresent(String.self, forKey: .dataDirectory)
                ?? Self.defaultDataDirectory,
            apiToken: try container.decodeIfPresent(String.self, forKey: .apiToken) ?? "",
            autoStartService: try container.decodeIfPresent(Bool.self, forKey: .autoStartService) ?? true,
            stopServiceOnQuit: try container.decodeIfPresent(Bool.self, forKey: .stopServiceOnQuit) ?? true
        )
    }

    public static var defaultDataDirectory: String {
        let baseURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")

        return baseURL
            .appendingPathComponent("Open WebUI Mac", isDirectory: true)
            .path
    }

    public var sanitized: OpenWebUISettings {
        var copy = self
        copy.host = host.trimmingCharacters(in: .whitespacesAndNewlines)
        if copy.host.isEmpty {
            copy.host = Self.defaultHost
        }

        copy.port = min(max(port, 1), 65_535)

        copy.serviceCommand = serviceCommand.trimmingCharacters(in: .whitespacesAndNewlines)
        if copy.serviceCommand.isEmpty {
            copy.serviceCommand = Self.defaultServiceCommand
        }

        copy.ollamaBaseURL = ollamaBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if copy.ollamaBaseURL.isEmpty {
            copy.ollamaBaseURL = Self.defaultOllamaBaseURL
        }

        copy.dataDirectory = NSString(string: dataDirectory.trimmingCharacters(in: .whitespacesAndNewlines))
            .expandingTildeInPath
        if copy.dataDirectory.isEmpty {
            copy.dataDirectory = Self.defaultDataDirectory
        }

        copy.apiToken = apiToken.trimmingCharacters(in: .whitespacesAndNewlines)

        return copy
    }

    public var rootURL: URL {
        var components = URLComponents()
        components.scheme = "http"
        components.host = host
        components.port = port
        components.path = "/"

        return components.url ?? URL(string: "http://\(Self.defaultHost):\(Self.defaultPort)/")!
    }

    public var healthURL: URL {
        rootURL.appendingPathComponent("health")
    }

    public var readyURL: URL {
        rootURL.appendingPathComponent("ready")
    }
}
