import Foundation
import Observation

/// Saves episode audio on-device for offline playback (the morning commute with
/// no signal). Files live in Application Support so the OS won't purge them like
/// it can with Caches; they're excluded from iCloud backup since they're
/// re-downloadable. One file per episode, named by id.
@MainActor
@Observable
final class DownloadStore {
    static let shared = DownloadStore()

    private(set) var downloaded: Set<String> = []
    private(set) var inProgress: Set<String> = []

    @ObservationIgnored private let dir: URL

    init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        dir = base.appendingPathComponent("Episodes", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        var excluded = dir
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? excluded.setResourceValues(values)

        // Rebuild the set from whatever's already on disk.
        let names = (try? FileManager.default.contentsOfDirectory(atPath: dir.path)) ?? []
        downloaded = Set(names.filter { $0.hasSuffix(".mp3") }.map { String($0.dropLast(4)) })
    }

    func isDownloaded(_ id: String) -> Bool { downloaded.contains(id) }
    func isDownloading(_ id: String) -> Bool { inProgress.contains(id) }

    /// Local file for an episode, if it's been downloaded — used by the player
    /// to play offline.
    func localURL(for id: String) -> URL? {
        let url = fileURL(id)
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }

    func download(_ episode: Episode) async {
        let id = episode.id
        guard !downloaded.contains(id), !inProgress.contains(id) else { return }
        guard let remote = PlayerModel.audioURL(for: episode) else { return }

        inProgress.insert(id)
        defer { inProgress.remove(id) }
        do {
            let (tmp, _) = try await URLSession.shared.download(from: remote)
            let dest = fileURL(id)
            try? FileManager.default.removeItem(at: dest)
            try FileManager.default.moveItem(at: tmp, to: dest)
            downloaded.insert(id)
        } catch {
            // Leave it un-downloaded; the control falls back to the download icon.
        }
    }

    func remove(_ id: String) {
        try? FileManager.default.removeItem(at: fileURL(id))
        downloaded.remove(id)
    }

    private func fileURL(_ id: String) -> URL {
        dir.appendingPathComponent("\(id).mp3")
    }
}
