import Foundation
import OpenWebUIMacCore

@MainActor
final class AppState: ObservableObject {
    let settingsStore: SettingsStore
    let service: OpenWebUIService

    init(settingsStore: SettingsStore = SettingsStore()) {
        self.settingsStore = settingsStore
        self.service = OpenWebUIService()
    }

    func startIfNeeded() {
        guard settingsStore.settings.autoStartService else {
            Task {
                await service.refreshHealth(settings: settingsStore.settings)
            }
            return
        }

        service.start(settings: settingsStore.settings)
    }

    func restart() {
        service.restart(settings: settingsStore.settings)
    }

    func stopForQuitIfNeeded() {
        guard settingsStore.settings.stopServiceOnQuit else {
            return
        }

        service.stop()
    }
}
