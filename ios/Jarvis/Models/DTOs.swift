import Foundation

// Responses (decoded with .convertFromSnakeCase)

struct TokenResponse: Decodable {
    let accessToken: String
    let tokenType: String
}

struct UserProfile: Decodable, Identifiable {
    let id: String
    let email: String?
    let topics: [String]
    let configuredProviders: [String]
    let dailyQuestionQuota: Int
}

struct Episode: Decodable, Identifiable {
    let id: String
    let title: String?
    let status: String
    let topics: [String]
    let durationSeconds: Double?
    let createdAt: String?
    let audioUrl: String?
    let error: String?

    var isReady: Bool { status == "ready" }
    var isFailed: Bool { status == "failed" }
    var displayTitle: String { title ?? topics.first ?? "Untitled" }
}

/// For endpoints whose body we don't need (extra keys are ignored).
struct EmptyResponse: Decodable {}

// Request bodies (encoded with .convertToSnakeCase)

struct SignupBody: Encodable {
    let email: String
    let password: String
    let topics: [String]
}

struct LoginBody: Encodable {
    let email: String
    let password: String
}

struct TopicsBody: Encodable {
    let topics: [String]
}

struct KeysBody: Encodable {
    let keys: [String: String]
}
