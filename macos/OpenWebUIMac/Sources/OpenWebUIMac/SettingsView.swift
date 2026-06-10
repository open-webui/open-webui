import OpenWebUIMacCore
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var draft: OpenWebUISettings = OpenWebUISettings()

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Settings")
                .font(.title2.bold())

            Grid(alignment: .leading, horizontalSpacing: 14, verticalSpacing: 12) {
                settingsRow("Host") {
                    TextField("127.0.0.1", text: $draft.host)
                        .textFieldStyle(.roundedBorder)
                }

                settingsRow("Port") {
                    HStack {
                        TextField("8080", value: $draft.port, format: .number)
                            .textFieldStyle(.roundedBorder)
                        Stepper("Port", value: $draft.port, in: 1...65_535)
                            .labelsHidden()
                    }
                }

                settingsRow("Service command") {
                    TextField("open-webui serve", text: $draft.serviceCommand)
                        .textFieldStyle(.roundedBorder)
                }

                settingsRow("API token") {
                    SecureField("Paste an Open WebUI API token", text: $draft.apiToken)
                        .textFieldStyle(.roundedBorder)
                }

                settingsRow("Ollama URL") {
                    TextField("http://127.0.0.1:11434", text: $draft.ollamaBaseURL)
                        .textFieldStyle(.roundedBorder)
                }

                settingsRow("Data directory") {
                    TextField("~/Library/Application Support/Open WebUI Mac", text: $draft.dataDirectory)
                        .textFieldStyle(.roundedBorder)
                }
            }

            VStack(alignment: .leading, spacing: 10) {
                Toggle("Start service when app opens", isOn: $draft.autoStartService)
                Toggle("Stop managed service on quit", isOn: $draft.stopServiceOnQuit)
            }

            Divider()

            HStack {
                Button {
                    draft = OpenWebUISettings()
                } label: {
                    Label("Reset", systemImage: "arrow.counterclockwise")
                }

                Spacer()

                Button("Cancel") {
                    dismiss()
                }

                Button {
                    appState.settingsStore.save(draft)
                    appState.restart()
                    dismiss()
                } label: {
                    Label("Apply and Restart", systemImage: "checkmark")
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(24)
        .frame(width: 640)
        .onAppear {
            draft = appState.settingsStore.settings
        }
    }

    private func settingsRow<Content: View>(
        _ label: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        GridRow {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .trailing)
            content()
                .frame(width: 430)
        }
    }
}
