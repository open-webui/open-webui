import Foundation
import OpenWebUIMacCore

enum OpenWebUIServiceStatus: Equatable {
    case stopped
    case starting
    case running(URL, managed: Bool)
    case failed(String)

    var title: String {
        switch self {
        case .stopped:
            return "Stopped"
        case .starting:
            return "Starting"
        case .running(_, let managed):
            return managed ? "Running" : "Running externally"
        case .failed:
            return "Failed"
        }
    }

    var isRunning: Bool {
        if case .running = self {
            return true
        }
        return false
    }
}

@MainActor
final class OpenWebUIService: ObservableObject {
    @Published private(set) var status: OpenWebUIServiceStatus = .stopped
    @Published private(set) var logLines: [String] = []

    private var process: Process?
    private var outputPipe: Pipe?
    private var startupTask: Task<Void, Never>?

    func start(settings: OpenWebUISettings) {
        let settings = settings.sanitized
        startupTask?.cancel()
        appendLog("Preparing Open WebUI on \(settings.rootURL.absoluteString)")
        status = .starting

        startupTask = Task { [weak self] in
            guard let self else {
                return
            }

            if await self.isHealthy(settings: settings) {
                self.status = .running(settings.rootURL, managed: false)
                self.appendLog("Detected an existing Open WebUI service.")
                return
            }

            do {
                try self.launch(settings: settings)
                try await self.waitUntilReady(settings: settings)
                self.status = .running(settings.rootURL, managed: true)
                self.appendLog("Open WebUI is ready.")
            } catch is CancellationError {
                self.appendLog("Startup was cancelled.")
            } catch {
                self.status = .failed(error.localizedDescription)
                self.appendLog("Startup failed: \(error.localizedDescription)")
            }
        }
    }

    func restart(settings: OpenWebUISettings) {
        stop()
        start(settings: settings)
    }

    func stop() {
        startupTask?.cancel()
        startupTask = nil

        guard let process else {
            appendLog("No managed service process to stop.")
            if case .running(let url, managed: false) = status {
                status = .running(url, managed: false)
            } else {
                status = .stopped
            }
            return
        }

        appendLog("Stopping managed Open WebUI service.")
        process.terminate()
        self.process = nil
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        outputPipe = nil
        status = .stopped
    }

    func refreshHealth(settings: OpenWebUISettings) async {
        let settings = settings.sanitized
        status = await isHealthy(settings: settings) ? .running(settings.rootURL, managed: process != nil) : .stopped
    }

    private func launch(settings: OpenWebUISettings) throws {
        if let process, process.isRunning {
            appendLog("Managed service is already running.")
            return
        }

        let plan = ServiceCommandBuilder.launchPlan(for: settings)
        appendLog("Launching: \(plan.displayCommand)")

        let process = Process()
        let pipe = Pipe()
        process.executableURL = plan.executableURL
        process.arguments = plan.arguments
        process.environment = plan.environment
        process.standardOutput = pipe
        process.standardError = pipe

        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let output = String(data: data, encoding: .utf8) else {
                return
            }

            Task { @MainActor [weak self] in
                self?.appendLog(output)
            }
        }

        process.terminationHandler = { [weak self] terminatedProcess in
            Task { @MainActor [weak self] in
                guard let self else {
                    return
                }

                let exitCode = terminatedProcess.terminationStatus
                self.appendLog("Service process exited with status \(exitCode).")
                self.process = nil
                self.outputPipe?.fileHandleForReading.readabilityHandler = nil
                self.outputPipe = nil

                if self.status.isRunning || self.status == .starting {
                    self.status = exitCode == 0 ? .stopped : .failed("Service exited with status \(exitCode).")
                }
            }
        }

        try process.run()
        self.process = process
        self.outputPipe = pipe
    }

    private func waitUntilReady(settings: OpenWebUISettings) async throws {
        let deadline = Date().addingTimeInterval(90)

        while Date() < deadline {
            try Task.checkCancellation()

            let ready = await isReady(settings: settings)
            let healthy = ready ? true : await isHealthy(settings: settings)
            if healthy {
                return
            }

            try await Task.sleep(for: .milliseconds(750))
        }

        throw ServiceError.timedOut(settings.rootURL)
    }

    private func isReady(settings: OpenWebUISettings) async -> Bool {
        await requestReturnsSuccess(settings.readyURL)
    }

    private func isHealthy(settings: OpenWebUISettings) async -> Bool {
        await requestReturnsSuccess(settings.healthURL)
    }

    private nonisolated func requestReturnsSuccess(_ url: URL) async -> Bool {
        var request = URLRequest(url: url)
        request.timeoutInterval = 2

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                return false
            }

            return (200..<300).contains(httpResponse.statusCode)
        } catch {
            return false
        }
    }

    private func appendLog(_ text: String) {
        let lines = text
            .split(whereSeparator: \.isNewline)
            .map(String.init)

        if lines.isEmpty {
            return
        }

        logLines.append(contentsOf: lines)
        if logLines.count > 400 {
            logLines.removeFirst(logLines.count - 400)
        }
    }
}

private enum ServiceError: LocalizedError {
    case timedOut(URL)

    var errorDescription: String? {
        switch self {
        case .timedOut(let url):
            return "Timed out waiting for Open WebUI at \(url.absoluteString)."
        }
    }
}
