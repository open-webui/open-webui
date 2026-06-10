import OpenWebUIMacCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @State private var showingSettings = false
    @State private var showingLogs = false
    @State private var reloadToken = 0

    var body: some View {
        Group {
            switch appState.service.status {
            case .running(let url, _):
                WebView(url: url, reloadToken: reloadToken)
            case .failed(let message):
                LaunchStatusView(
                    status: appState.service.status,
                    detail: message,
                    primaryAction: appState.restart,
                    secondaryAction: { showingLogs = true }
                )
            default:
                LaunchStatusView(
                    status: appState.service.status,
                    detail: "Open WebUI will appear here when the local service is ready.",
                    primaryAction: appState.restart,
                    secondaryAction: { showingLogs = true }
                )
            }
        }
        .frame(minWidth: 1024, minHeight: 720)
        .toolbar {
            ToolbarItemGroup {
                Button {
                    reloadToken += 1
                } label: {
                    Label("Reload", systemImage: "arrow.clockwise")
                }

                Button {
                    NSWorkspace.shared.open(appState.settingsStore.settings.rootURL)
                } label: {
                    Label("Open in Browser", systemImage: "safari")
                }

                Button {
                    showingLogs = true
                } label: {
                    Label("Logs", systemImage: "doc.text.magnifyingglass")
                }

                Button {
                    showingSettings = true
                } label: {
                    Label("Settings", systemImage: "gearshape")
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
                .environmentObject(appState)
        }
        .sheet(isPresented: $showingLogs) {
            LogsView()
                .environmentObject(appState)
        }
        .task {
            appState.startIfNeeded()
        }
    }
}

private struct LaunchStatusView: View {
    let status: OpenWebUIServiceStatus
    let detail: String
    let primaryAction: () -> Void
    let secondaryAction: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: iconName)
                .font(.system(size: 52, weight: .semibold))
                .foregroundStyle(iconColor)

            VStack(spacing: 8) {
                Text("Open WebUI")
                    .font(.largeTitle.bold())

                Text(status.title)
                    .font(.title3)
                    .foregroundStyle(.secondary)

                Text(detail)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: 520)
            }

            if status == .starting {
                ProgressView()
                    .controlSize(.large)
            }

            HStack(spacing: 12) {
                Button {
                    primaryAction()
                } label: {
                    Label("Restart Service", systemImage: "arrow.triangle.2.circlepath")
                }
                .buttonStyle(.borderedProminent)

                Button {
                    secondaryAction()
                } label: {
                    Label("View Logs", systemImage: "doc.text")
                }
            }
        }
        .padding(32)
    }

    private var iconName: String {
        switch status {
        case .failed:
            return "exclamationmark.triangle.fill"
        case .running:
            return "checkmark.circle.fill"
        case .starting:
            return "hourglass"
        case .stopped:
            return "power.circle"
        }
    }

    private var iconColor: Color {
        switch status {
        case .failed:
            return .orange
        case .running:
            return .green
        case .starting:
            return .accentColor
        case .stopped:
            return .secondary
        }
    }
}
