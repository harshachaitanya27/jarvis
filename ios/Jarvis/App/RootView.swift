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
        case .setup:
            SetupView()
        case .ready:
            LibraryView()
        }
    }
}
