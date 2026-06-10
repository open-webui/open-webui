import Foundation

public struct CommandLaunchPlan: Equatable, Sendable {
    public var executableURL: URL
    public var arguments: [String]
    public var environment: [String: String]
    public var displayCommand: String

    public init(
        executableURL: URL,
        arguments: [String],
        environment: [String: String],
        displayCommand: String
    ) {
        self.executableURL = executableURL
        self.arguments = arguments
        self.environment = environment
        self.displayCommand = displayCommand
    }
}

public enum ServiceCommandBuilder {
    public static func launchPlan(for settings: OpenWebUISettings) -> CommandLaunchPlan {
        let settings = settings.sanitized
        var environment = ProcessInfo.processInfo.environment
        environment["DATA_DIR"] = settings.dataDirectory
        environment["OLLAMA_BASE_URL"] = settings.ollamaBaseURL
        environment["ENV"] = "prod"

        let shellScript = [
            "mkdir -p \(shellQuote(settings.dataDirectory))",
            "export DATA_DIR=\(shellQuote(settings.dataDirectory))",
            "export OLLAMA_BASE_URL=\(shellQuote(settings.ollamaBaseURL))",
            "export ENV=prod",
            "exec \(settings.serviceCommand) --host \(shellQuote(settings.host)) --port \(settings.port)"
        ].joined(separator: "\n")

        return CommandLaunchPlan(
            executableURL: URL(fileURLWithPath: "/bin/zsh"),
            arguments: ["-lc", shellScript],
            environment: environment,
            displayCommand: "\(settings.serviceCommand) --host \(settings.host) --port \(settings.port)"
        )
    }

    public static func shellQuote(_ value: String) -> String {
        "'\(value.replacingOccurrences(of: "'", with: "'\\''"))'"
    }
}
