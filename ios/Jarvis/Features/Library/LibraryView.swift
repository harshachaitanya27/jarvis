import SwiftUI

/// Placeholder for the episode library — filled in by the next PR.
struct LibraryView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "waveform.circle.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.tint)
                Text("You're all set")
                    .font(.title2.bold())
                Text("Episodes generated from your topics will appear here.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            .padding()
            .navigationTitle("Library")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sign out") { model.signOut() }
                }
            }
        }
    }
}
