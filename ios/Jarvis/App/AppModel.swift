import Foundation
import Observation

/// Single source of truth for auth + onboarding state. Drives which screen the
/// root shows based on whether there's a token and whether the user has a key.
@MainActor
@Observable
final class AppModel {
    enum Stage {
        case auth      // no token — sign up / log in
        case loading   // have a token, fetching the profile
        case topics    // signed in but no topics yet
        case setup     // has topics but no provider key yet
        case ready     // fully configured
    }

    var token: String?
    var profile: UserProfile?

    init() {
        token = TokenStore.load()
    }

    var stage: Stage {
        if token == nil { return .auth }
        guard let profile else { return .loading }
        if profile.topics.isEmpty { return .topics }
        return profile.configuredProviders.isEmpty ? .setup : .ready
    }

    func signedIn(token: String) {
        TokenStore.save(token)
        self.token = token
        profile = nil
    }

    func signOut() {
        TokenStore.clear()
        token = nil
        profile = nil
    }

    func refresh() async {
        guard let token else { return }
        profile = try? await APIClient.shared.me(token: token)
    }
}
