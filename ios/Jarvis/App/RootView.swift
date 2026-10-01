import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        switch model.stage {
        case .auth:
            AuthView()
        case .loading:
            ProgressView("Loading…")
                .task { await model.refresh() }
        case .setup:
            SetupView()
        case .ready:
            LibraryView()
        }
    }
}
