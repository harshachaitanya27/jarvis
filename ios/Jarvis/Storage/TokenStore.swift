import Foundation
import Security

/// Access token persisted in the Keychain.
enum TokenStore {
    private static let service = "com.jarvis.app"
    private static let account = "access_token"

    private static var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    static func save(_ token: String) {
        SecItemDelete(baseQuery as CFDictionary)
        var add = baseQuery
        add[kSecValueData as String] = Data(token.utf8)
        SecItemAdd(add as CFDictionary, nil)
    }

    static func load() -> String? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8)
        else { return nil }
        return token
    }

    static func clear() {
        SecItemDelete(baseQuery as CFDictionary)
    }
}
