import SwiftUI

struct LogsView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Service Logs")
                    .font(.title2.bold())

                Spacer()

                Button {
                    dismiss()
                } label: {
                    Label("Close", systemImage: "xmark")
                }
            }

            ScrollView {
                Text(appState.service.logLines.joined(separator: "\n"))
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
            }
            .background(Color(nsColor: .textBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .padding(24)
        .frame(width: 760, height: 460)
    }
}
