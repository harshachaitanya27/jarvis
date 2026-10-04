import Observation

@MainActor
@Observable
final class LibraryModel {
    private(set) var episodes: [Episode] = []
    private(set) var loading = false
    private(set) var starting = false
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

    /// First-run generation: trigger a run, then refresh so the queued episodes
    /// appear. The nightly scheduler remains the primary path.
    func generateFirst(token: String) async {
        error = nil
        starting = true
        defer { starting = false }
        do {
            try await APIClient.shared.generateNow(token: token)
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            return
        }
        // Give the background task a moment to create the queued rows, then show them.
        try? await Task.sleep(for: .seconds(1.5))
        await load(token: token)
    }
}
