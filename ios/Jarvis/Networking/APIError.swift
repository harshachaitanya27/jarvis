import Foundation

enum APIError: LocalizedError {
    case http(status: Int, detail: String?)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case let .http(status, detail):
            return detail ?? "Request failed (\(status))"
        case .decoding:
            return "Couldn't read the server response."
        case let .transport(error):
            return error.localizedDescription
        }
    }
}
