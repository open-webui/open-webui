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

            Form {
                TextField("Host", text: $draft.host)

                Stepper(value: $draft.port, in: 1...65_535) {
                    TextField("Port", value: $draft.port, format: .number)
                }

                TextField("Service command", text: $draft.serviceCommand)
                    .textFieldStyle(.roundedBorder)

                TextField("Ollama URL", text: $draft.ollamaBaseURL)
                    .textFieldStyle(.roundedBorder)

                TextField("Data directory", text: $draft.dataDirectory)
                    .textFieldStyle(.roundedBorder)

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
        .frame(width: 560)
        .onAppear {
            draft = appState.settingsStore.settings
        }
    }
}
