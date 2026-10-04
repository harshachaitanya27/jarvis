import SwiftUI

struct PlayerView: View {
    let episode: Episode
    let token: String

    @Environment(\.dismiss) private var dismiss
    private let player = PlayerModel.shared
    @State private var scrubbing = false
    @State private var scrubValue: Double = 0

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Space.lg) {
            HStack {
                QuietButton(title: "Close") {
                    // Keep playing — audio continues on the lock screen / CarPlay.
                    dismiss()
                }
                Spacer()
            }

            Spacer()

            VStack(alignment: .leading, spacing: Theme.Space.md) {
                Eyebrow(episode.topics.first ?? "Episode")
                DisplayTitle(episode.displayTitle, size: 34)
            }

            Spacer()

            scrubber
            controls

            Spacer()
        }
        .padding(.horizontal, Theme.Space.lg)
        .padding(.vertical, Theme.Space.xl)
        .screen()
        .task { player.load(episode, token: token) }
        .onChange(of: player.currentTime) { _, newValue in
            if !scrubbing { scrubValue = newValue }
        }
    }

    private var scrubber: some View {
        VStack(spacing: Theme.Space.sm) {
            Slider(
                value: $scrubValue,
                in: 0...max(player.duration, 1),
                onEditingChanged: { editing in
                    scrubbing = editing
                    if !editing { player.seek(to: scrubValue) }
                }
            )
            .tint(Theme.accent)

            HStack {
                Text(timeString(scrubValue))
                Spacer()
                Text(timeString(player.duration))
            }
            .font(.system(size: 12, weight: .medium))
            .foregroundStyle(Theme.muted)
        }
    }

    private var controls: some View {
        HStack {
            Spacer()
            Button { player.toggle() } label: {
                Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(Theme.paper)
                    .frame(width: 76, height: 76)
                    .background(Theme.accent)
                    .clipShape(Circle())
            }
            Spacer()
        }
    }

    private func timeString(_ seconds: Double) -> String {
        guard seconds.isFinite, seconds >= 0 else { return "0:00" }
        let total = Int(seconds)
        return String(format: "%d:%02d", total / 60, total % 60)
    }
}
