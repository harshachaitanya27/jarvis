import SwiftUI

/// Placeholder for the episode library — the list + player come in the next PR.
struct LibraryView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Eyebrow("Library")
                Spacer()
                QuietButton(title: "Sign out") { model.signOut() }
            }
            .padding(.horizontal, Theme.Space.lg)
            .padding(.top, Theme.Space.lg)

            Spacer()

            VStack(alignment: .leading, spacing: Theme.Space.md) {
                DisplayTitle("No episodes\nyet", size: 36)
                Text("Episodes generated from your topics will appear here each morning.")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.horizontal, Theme.Space.lg)

            Spacer()
            Spacer()
        }
        .screen()
    }
}
