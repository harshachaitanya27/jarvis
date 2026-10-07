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
                    if model.hasFailure { retryFooter }
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

    private var retryFooter: some View {
        VStack(alignment: .leading, spacing: Theme.Space.md) {
            Text("Some episodes didn't finish generating. You can try again.")
                .font(.system(size: 15))
                .foregroundStyle(Theme.muted)
                .fixedSize(horizontal: false, vertical: true)

            PrimaryButton(title: "Try again", loading: model.generating, enabled: !model.generating) {
                Task { await generateFirst() }
            }

            if let error = model.error {
                Text(error).font(.system(size: 13)).foregroundStyle(Theme.danger)
            }
        }
        .padding(.top, Theme.Space.lg)
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
                if isGenerating {
                    ProgressView().controlSize(.small).tint(Theme.accent)
                }
                Eyebrow(statusLabel, color: statusColor)
                if episode.isReady, let duration = episode.durationSeconds {
                    Eyebrow("· \(Int(duration / 60)) min")
                }
            }

            if episode.isFailed, let reason = episode.error, !reason.isEmpty {
                Text(reason)
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(.vertical, Theme.Space.lg)
    }

    private var isGenerating: Bool { !episode.isReady && !episode.isFailed }

    /// Mirror the backend's generation phases so the row tracks real progress.
    private var statusLabel: String {
        switch episode.status {
        case "queued": return "Queued"
        case "researching": return "Researching"
        case "scripting": return "Writing script"
        case "voicing": return "Voicing"
        case "assembling": return "Assembling"
        case "ready": return "Ready"
        case "failed": return "Failed"
        default: return episode.status.capitalized
        }
    }

    private var statusColor: Color {
        if episode.isFailed { return Theme.danger }
        if isGenerating { return Theme.accent }  // active state earns the accent
        return Theme.muted
    }
}
