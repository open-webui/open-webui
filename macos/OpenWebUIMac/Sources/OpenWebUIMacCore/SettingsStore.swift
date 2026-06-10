import Combine
import Foundation
import Security

public final class SettingsStore: ObservableObject {
    private static let storageKey = "OpenWebUIMac.settings.v1"
    private static let apiTokenService = "com.openwebui.mac"
    private static let apiTokenAccount = "open-webui-api-token"

    @Published public private(set) var settings: OpenWebUISettings

    private let defaults: UserDefaults
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        var loadedSettings = Self.load(from: defaults, decoder: JSONDecoder())
        if let keychainToken = Self.loadAPIToken(), !keychainToken.isEmpty {
            loadedSettings.apiToken = keychainToken
        }
        self.settings = loadedSettings
    }

    public func save(_ newSettings: OpenWebUISettings) {
        let sanitizedSettings = newSettings.sanitized
        settings = sanitizedSettings
        Self.saveAPIToken(sanitizedSettings.apiToken)

        var persistedSettings = sanitizedSettings
        persistedSettings.apiToken = ""

        if let data = try? encoder.encode(persistedSettings) {
            defaults.set(data, forKey: Self.storageKey)
        }
    }

    public func reset() {
        defaults.removeObject(forKey: Self.storageKey)
        Self.deleteAPIToken()
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

    private static func loadAPIToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: apiTokenService,
            kSecAttrAccount as String: apiTokenAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }

        return String(data: data, encoding: .utf8)
    }

    private static func saveAPIToken(_ token: String) {
        if token.isEmpty {
            deleteAPIToken()
            return
        }

        let data = Data(token.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: apiTokenService,
            kSecAttrAccount as String: apiTokenAccount
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updateStatus == errSecItemNotFound {
            var addQuery = query
            addQuery[kSecValueData as String] = data
            SecItemAdd(addQuery as CFDictionary, nil)
        }
    }

    private static func deleteAPIToken() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: apiTokenService,
            kSecAttrAccount as String: apiTokenAccount
        ]
        SecItemDelete(query as CFDictionary)
    }
}
