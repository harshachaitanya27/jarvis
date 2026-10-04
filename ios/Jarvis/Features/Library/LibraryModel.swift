import Observation

@MainActor
@Observable
final class LibraryModel {
    private(set) var episodes: [Episode] = []
    private(set) var loading = false
    var error: String?

    func load(token: String) async {
        loading = true
        defer { loading = false }
        do {
            episodes = try await APIClient.shared.episodes(token: token)
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
