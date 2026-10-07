import Observation

@MainActor
@Observable
final class LibraryModel {
    private(set) var episodes: [Episode] = []
    private(set) var loading = false
    private(set) var generating = false   // a run was triggered; waiting for it to appear
    var error: String?

    @ObservationIgnored private var pollTask: Task<Void, Never>?

    /// True while anything is still being produced — a just-triggered run that
    /// hasn't surfaced yet, or an episode mid-generation.
    private var hasPending: Bool {
        generating || episodes.contains { !$0.isReady && !$0.isFailed }
    }

    /// An episode failed to generate — surface a retry.
    var hasFailure: Bool { episodes.contains(where: \.isFailed) }

    func load(token: String) async {
        loading = true
        defer { loading = false }
        do {
            episodes = try await APIClient.shared.episodes(token: token)
            if generating, !episodes.isEmpty { generating = false }
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// First-run generation: trigger a run and keep refreshing until it appears
    /// and settles. The button is replaced by a progress state meanwhile, so it
    /// can't be fired twice.
    func generateFirst(token: String) async {
        error = nil
        generating = true
        do {
            try await APIClient.shared.generateNow(token: token)
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            generating = false
            return
        }
        await load(token: token)
        startPolling(token: token)
    }

    /// Refresh on an interval while there's pending work, so statuses flip
    /// (queued → … → ready) live. Stops once everything has settled.
    func startPolling(token: String) {
        guard pollTask == nil, hasPending else { return }
        pollTask = Task { [weak self] in
            guard let self else { return }
            var ticks = 0
            while !Task.isCancelled, ticks < 60 {   // cap ~3 min
                try? await Task.sleep(for: .seconds(3))
                if Task.isCancelled { break }
                await self.load(token: token)
                ticks += 1
                if !self.hasPending { break }
            }
            self.pollTask = nil
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }
}
