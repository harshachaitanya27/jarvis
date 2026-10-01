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
