import OpenWebUIMacCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @State private var showingSettings = false
    @State private var showingLogs = false

    var body: some View {
        NativeChatWorkspaceView()
        .frame(minWidth: 900, minHeight: 680)
        .toolbar {
            ToolbarItemGroup {
                Button {
                    appState.restart()
                } label: {
                    Label("Restart Service", systemImage: "arrow.clockwise")
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

                Button {
                    NSWorkspace.shared.open(appState.settingsStore.settings.rootURL)
                } label: {
                    Label("Open in Browser", systemImage: "safari")
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
