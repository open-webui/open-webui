import XCTest
@testable import OpenWebUIMacCore

final class OpenWebUISettingsTests: XCTestCase {
    func testSanitizedSettingsClampPortAndRestoreDefaults() {
        let settings = OpenWebUISettings(
            host: "   ",
            port: 99_999,
            serviceCommand: "",
            ollamaBaseURL: "",
            dataDirectory: "~/Open WebUI Test"
        ).sanitized

        XCTAssertEqual(settings.host, OpenWebUISettings.defaultHost)
        XCTAssertEqual(settings.port, 65_535)
        XCTAssertEqual(settings.serviceCommand, OpenWebUISettings.defaultServiceCommand)
        XCTAssertEqual(settings.ollamaBaseURL, OpenWebUISettings.defaultOllamaBaseURL)
        XCTAssertFalse(settings.dataDirectory.contains("~"))
    }

    func testURLsUseConfiguredHostAndPort() {
        let settings = OpenWebUISettings(host: "localhost", port: 5050)

        XCTAssertEqual(settings.rootURL.absoluteString, "http://localhost:5050")
        XCTAssertEqual(settings.healthURL.absoluteString, "http://localhost:5050/health")
        XCTAssertEqual(settings.readyURL.absoluteString, "http://localhost:5050/ready")
    }

    func testInvalidURLFallsBackToDefaultAddress() {
        let settings = OpenWebUISettings(host: "not a host", port: 5050)

        XCTAssertEqual(settings.rootURL.absoluteString, "http://127.0.0.1:8080")
    }

    func testShellQuoteHandlesSingleQuotes() {
        XCTAssertEqual(ServiceCommandBuilder.shellQuote("John's Mac"), "'John'\\''s Mac'")
    }

    func testLaunchPlanExportsDesktopDefaults() {
        let settings = OpenWebUISettings(
            host: "127.0.0.1",
            port: 9090,
            serviceCommand: "python -m open_webui serve",
            ollamaBaseURL: "http://127.0.0.1:11434",
            dataDirectory: "/tmp/open webui"
        )

        let plan = ServiceCommandBuilder.launchPlan(for: settings)

        XCTAssertEqual(plan.executableURL.path, "/bin/zsh")
        XCTAssertEqual(plan.environment["DATA_DIR"], "/tmp/open webui")
        XCTAssertEqual(plan.environment["OLLAMA_BASE_URL"], "http://127.0.0.1:11434")
        XCTAssertEqual(plan.environment["ENV"], "prod")
        XCTAssertTrue(plan.arguments.last?.contains("--host '127.0.0.1' --port 9090") ?? false)
    }
}
