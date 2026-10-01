import Foundation

/// Thin async client over the Jarvis backend. One method per endpoint the app
/// uses; JSON is snake_case on the wire and camelCase in Swift.
actor APIClient {
    static let shared = APIClient()

    private let baseURL = Config.baseURL
    private let session = URLSession.shared

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    // MARK: Endpoints

    func signup(email: String, password: String, topics: [String]) async throws -> TokenResponse {
        try await request("auth/signup", method: "POST",
                          body: SignupBody(email: email, password: password, topics: topics))
    }

    func login(email: String, password: String) async throws -> TokenResponse {
        try await request("auth/login", method: "POST",
                          body: LoginBody(email: email, password: password))
    }

    func me(token: String) async throws -> UserProfile {
        try await request("me", method: "GET", token: token)
    }

    func setTopics(_ topics: [String], token: String) async throws -> UserProfile {
        try await request("me/topics", method: "PUT", body: TopicsBody(topics: topics), token: token)
    }

    func setKeys(_ keys: [String: String], token: String) async throws -> UserProfile {
        try await request("me/keys", method: "PUT", body: KeysBody(keys: keys), token: token)
    }

    // MARK: Request plumbing

    private func request<Response: Decodable, Body: Encodable>(
        _ path: String, method: String, body: Body, token: String? = nil
    ) async throws -> Response {
        let data = try encoder.encode(body)
        return try await send(path, method: method, token: token, bodyData: data)
    }

    private func request<Response: Decodable>(
        _ path: String, method: String, token: String? = nil
    ) async throws -> Response {
        try await send(path, method: method, token: token, bodyData: nil)
    }

    private func send<Response: Decodable>(
        _ path: String, method: String, token: String?, bodyData: Data?
    ) async throws -> Response {
        var req = URLRequest(url: baseURL.appending(path: path))
        req.httpMethod = method
        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let bodyData {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = bodyData
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.http(status: -1, detail: nil)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(status: http.statusCode, detail: Self.detail(from: data))
        }
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private static func detail(from data: Data) -> String? {
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let detail = json["detail"] as? String {
            return detail
        }
        return String(data: data, encoding: .utf8)
    }
}
