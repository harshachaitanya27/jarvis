import SwiftUI

struct LibraryView: View {
    @Environment(AppModel.self) private var app
    @State private var model = LibraryModel()
    @State private var selected: Episode?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header

                if model.episodes.isEmpty {
                    emptyState
                } else {
                    ForEach(model.episodes) { episode in
                        Button {
                            if episode.isReady { selected = episode }
                        } label: {
                            EpisodeRow(episode: episode)
                        }
                        .buttonStyle(.plain)
                        .disabled(!episode.isReady)
                        Hairline()
                    }
                }
            }
            .padding(.horizontal, Theme.Space.lg)
            .padding(.bottom, Theme.Space.xl)
        }
        .screen()
        .refreshable { await load() }
        .task {
            await load()
            if let token = app.token { model.startPolling(token: token) }
        }
        .onDisappear { model.stopPolling() }
        .fullScreenCover(item: $selected) { episode in
            if let token = app.token {
                PlayerView(episode: episode, token: token)
            }
        }
    }

    private var header: some View {
        HStack {
            DisplayTitle("Library", size: 40)
            Spacer()
            QuietButton(title: "Sign out") { app.signOut() }
        }
        .padding(.top, Theme.Space.xl)
        .padding(.bottom, Theme.Space.lg)
    }

    @ViewBuilder
    private var emptyState: some View {
        if model.generating {
            generatingState
        } else {
            VStack(alignment: .leading, spacing: Theme.Space.lg) {
                VStack(alignment: .leading, spacing: Theme.Space.md) {
                    Text("No episodes yet")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(Theme.ink)
                    Text("New episodes arrive automatically each morning. Want one now?")
                        .font(.system(size: 15))
                        .foregroundStyle(Theme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }

                PrimaryButton(title: "Generate my first episode") {
                    Task { await generateFirst() }
                }

                if let error = model.error {
                    Text(error).font(.system(size: 13)).foregroundStyle(Theme.danger)
                }
            }
            .padding(.top, Theme.Space.xl)
        }
    }

    private var generatingState: some View {
        VStack(alignment: .leading, spacing: Theme.Space.md) {
            HStack(spacing: Theme.Space.sm) {
                ProgressView().tint(Theme.accent)
                Text("Generating your first episode")
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(Theme.ink)
            }
            Text("This takes about a minute. It'll appear here automatically when it's ready.")
                .font(.system(size: 15))
                .foregroundStyle(Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.top, Theme.Space.xl)
    }

    private func generateFirst() async {
        guard let token = app.token else { return }
        await model.generateFirst(token: token)
    }

    private func load() async {
        guard let token = app.token else { return }
        await model.load(token: token)
    }
}

private struct EpisodeRow: View {
    let episode: Episode

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            Text(episode.displayTitle)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(episode.isReady ? Theme.ink : Theme.muted)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)

            HStack(spacing: Theme.Space.sm) {
                Eyebrow(statusLabel, color: statusColor)
                if episode.isReady, let duration = episode.durationSeconds {
                    Eyebrow("· \(Int(duration / 60)) min")
                }
            }
        }
        .padding(.vertical, Theme.Space.lg)
    }

    private var statusLabel: String {
        if episode.isReady { return "Ready" }
        if episode.isFailed { return "Failed" }
        return "Generating"
    }

    private var statusColor: Color {
        episode.isFailed ? Theme.danger : Theme.muted
    }
}
