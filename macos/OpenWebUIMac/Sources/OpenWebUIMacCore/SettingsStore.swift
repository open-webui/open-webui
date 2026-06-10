import Combine
import Foundation

public final class SettingsStore: ObservableObject {
    private static let storageKey = "OpenWebUIMac.settings.v1"

    @Published public private(set) var settings: OpenWebUISettings

    private let defaults: UserDefaults
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.settings = Self.load(from: defaults, decoder: JSONDecoder())
    }

    public func save(_ newSettings: OpenWebUISettings) {
        let sanitizedSettings = newSettings.sanitized
        settings = sanitizedSettings

        if let data = try? encoder.encode(sanitizedSettings) {
            defaults.set(data, forKey: Self.storageKey)
        }
    }

    public func reset() {
        defaults.removeObject(forKey: Self.storageKey)
        settings = OpenWebUISettings()
    }

    private static func load(from defaults: UserDefaults, decoder: JSONDecoder) -> OpenWebUISettings {
        guard let data = defaults.data(forKey: storageKey),
              let decoded = try? decoder.decode(OpenWebUISettings.self, from: data)
        else {
            return OpenWebUISettings()
        }

        return decoded.sanitized
    }
}
