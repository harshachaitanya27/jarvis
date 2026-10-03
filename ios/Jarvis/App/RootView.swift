import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        switch model.stage {
        case .auth:
            AuthView()
        case .loading:
            VStack { ProgressView().tint(Theme.ink) }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .screen()
                .task { await model.refresh() }
        case .topics:
            TopicsView()
        case .setup:
            SetupView()
        case .ready:
            LibraryView()
        }
    }
}
