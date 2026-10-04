import CarPlay
import UIKit

/// CarPlay entry point. Shows the user's ready episodes as a list; selecting one
/// drives the shared PlayerModel (so phone and car stay in lockstep) and pushes
/// the system Now Playing screen, whose transport buttons are wired through the
/// MPRemoteCommandCenter targets PlayerModel already registers.
final class CarPlaySceneDelegate: UIResponder, CPTemplateApplicationSceneDelegate {
    private var interfaceController: CPInterfaceController?
    private let root = CPListTemplate(title: "Jarvis", sections: [])

    func templateApplicationScene(
        _ scene: CPTemplateApplicationScene,
        didConnect interfaceController: CPInterfaceController
    ) {
        self.interfaceController = interfaceController
        root.updateSections([Self.messageSection("Loading…")])
        interfaceController.setRootTemplate(root, animated: false, completion: nil)
        Task { @MainActor in await refresh() }
    }

    func templateApplicationScene(
        _ scene: CPTemplateApplicationScene,
        didDisconnectInterfaceController interfaceController: CPInterfaceController
    ) {
        self.interfaceController = nil
    }

    // MARK: - Content

    @MainActor
    private func refresh() async {
        guard let token = TokenStore.load() else {
            root.updateSections([Self.messageSection("Sign in on your phone to see episodes.")])
            return
        }
        do {
            let ready = try await APIClient.shared.episodes(token: token).filter(\.isReady)
            guard !ready.isEmpty else {
                root.updateSections([Self.messageSection("No episodes yet — new ones arrive each morning.")])
                return
            }
            let items = ready.map { episode -> CPListItem in
                let item = CPListItem(text: episode.displayTitle, detailText: Self.subtitle(for: episode))
                item.handler = { [weak self] _, completion in
                    Task { @MainActor in
                        PlayerModel.shared.load(episode, token: token)
                        self?.pushNowPlaying()
                        completion()
                    }
                }
                return item
            }
            root.updateSections([CPListSection(items: items)])
        } catch {
            root.updateSections([Self.messageSection("Couldn't load episodes.")])
        }
    }

    private func pushNowPlaying() {
        interfaceController?.pushTemplate(CPNowPlayingTemplate.shared, animated: true, completion: nil)
    }

    // MARK: - Helpers

    private static func subtitle(for episode: Episode) -> String? {
        guard let seconds = episode.durationSeconds, seconds > 0 else { return episode.topics.first }
        return "\(Int(seconds / 60)) min"
    }

    private static func messageSection(_ text: String) -> CPListSection {
        CPListSection(items: [CPListItem(text: text, detailText: nil)])
    }
}
