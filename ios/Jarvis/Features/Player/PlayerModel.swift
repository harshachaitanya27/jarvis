import AVFoundation
import MediaPlayer
import Observation

/// Wraps AVPlayer for one episode: play/pause/seek, progress, background audio,
/// lock-screen Now Playing, and play/complete feedback to the backend.
@MainActor
@Observable
final class PlayerModel {
    /// Shared across the phone UI and the CarPlay scene so both drive one
    /// AVPlayer / audio session rather than fighting over playback.
    static let shared = PlayerModel()

    private(set) var isPlaying = false
    private(set) var currentTime: Double = 0
    private(set) var duration: Double = 0
    private(set) var currentEpisode: Episode?

    @ObservationIgnored private var player: AVPlayer?
    @ObservationIgnored private var timeObserver: Any?
    @ObservationIgnored private var endObserver: NSObjectProtocol?
    @ObservationIgnored private var token: String?
    @ObservationIgnored private var sessionConfigured = false
    @ObservationIgnored private var remoteConfigured = false

    static func audioURL(for episode: Episode) -> URL? {
        guard let path = episode.audioUrl else { return nil }
        return URL(string: path, relativeTo: Config.baseURL)?.absoluteURL
    }

    func load(_ episode: Episode, token: String) {
        // Prefer an offline copy; fall back to streaming from the backend.
        guard let url = DownloadStore.shared.localURL(for: episode.id) ?? Self.audioURL(for: episode) else { return }
        // Already on this episode (e.g. started from CarPlay, now opened on the
        // phone) — keep the stream, just make sure it's playing.
        if currentEpisode?.id == episode.id, player != nil {
            self.token = token
            play()
            return
        }
        teardown()
        self.currentEpisode = episode
        self.token = token
        self.duration = episode.durationSeconds ?? 0
        configureSessionOnce()

        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)
        self.player = player

        let interval = CMTime(seconds: 0.5, preferredTimescale: 600)
        timeObserver = player.addPeriodicTimeObserver(forInterval: interval, queue: .main) { [weak self] time in
            Task { @MainActor in
                guard let self else { return }
                self.currentTime = time.seconds
                let itemDuration = item.duration.seconds
                if self.duration <= 0, itemDuration.isFinite, itemDuration > 0 {
                    self.duration = itemDuration
                }
                self.updateNowPlaying()
            }
        }

        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime, object: item, queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.handleEnded() }
        }

        setupRemoteCommands()
        play()
    }

    func play() {
        player?.play()
        isPlaying = true
        updateNowPlaying()
        logFeedback("play")
    }

    func pause() {
        player?.pause()
        isPlaying = false
        updateNowPlaying()
    }

    func toggle() { isPlaying ? pause() : play() }

    func seek(to seconds: Double) {
        currentTime = seconds
        player?.seek(to: CMTime(seconds: seconds, preferredTimescale: 600))
        updateNowPlaying()
    }

    func stop() { teardown() }

    // MARK: - Internals

    private func handleEnded() {
        isPlaying = false
        currentTime = duration
        updateNowPlaying()
        logFeedback("complete")
    }

    private func configureSessionOnce() {
        guard !sessionConfigured else { return }
        sessionConfigured = true
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio)
        try? session.setActive(true)
    }

    private func logFeedback(_ type: String) {
        guard let episode = currentEpisode, let token else { return }
        let position = currentTime
        Task {
            try? await APIClient.shared.logFeedback(
                episodeId: episode.id, type: type, position: position, token: token
            )
        }
    }

    private func updateNowPlaying() {
        var info: [String: Any] = [
            MPMediaItemPropertyTitle: currentEpisode?.displayTitle ?? "Jarvis",
            MPNowPlayingInfoPropertyElapsedPlaybackTime: currentTime,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? 1.0 : 0.0,
        ]
        if duration > 0 { info[MPMediaItemPropertyPlaybackDuration] = duration }
        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }

    private func setupRemoteCommands() {
        guard !remoteConfigured else { return }  // targets persist; add them once
        remoteConfigured = true
        let center = MPRemoteCommandCenter.shared()
        center.playCommand.addTarget { [weak self] _ in
            Task { @MainActor in self?.play() }
            return .success
        }
        center.pauseCommand.addTarget { [weak self] _ in
            Task { @MainActor in self?.pause() }
            return .success
        }
        center.togglePlayPauseCommand.addTarget { [weak self] _ in
            Task { @MainActor in self?.toggle() }
            return .success
        }
        center.changePlaybackPositionCommand.addTarget { [weak self] event in
            guard let event = event as? MPChangePlaybackPositionCommandEvent else {
                return .commandFailed
            }
            Task { @MainActor in self?.seek(to: event.positionTime) }
            return .success
        }
    }

    private func teardown() {
        if let timeObserver { player?.removeTimeObserver(timeObserver) }
        timeObserver = nil
        if let endObserver { NotificationCenter.default.removeObserver(endObserver) }
        endObserver = nil
        player?.pause()
        player = nil
        isPlaying = false
    }
}
