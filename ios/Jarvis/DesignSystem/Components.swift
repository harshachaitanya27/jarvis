import SwiftUI

/// Small tracked uppercase label — the "eyebrow" above titles and the status
/// microcopy on rows.
struct Eyebrow: View {
    let text: String
    var color: Color = Theme.muted
    init(_ text: String, color: Color = Theme.muted) {
        self.text = text
        self.color = color
    }

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 12, weight: .semibold))
            .tracking(1.6)
            .foregroundStyle(color)
    }
}

/// Tight-sans display title.
struct DisplayTitle: View {
    let text: String
    var size: CGFloat = 40
    init(_ text: String, size: CGFloat = 40) {
        self.text = text
        self.size = size
    }

    var body: some View {
        Text(text)
            .font(.system(size: size, weight: .bold))
            .tracking(-0.5)
            .foregroundStyle(Theme.ink)
            .fixedSize(horizontal: false, vertical: true)
    }
}

/// Full-width monochrome action — white fill, black label. No color; the accent
/// is deliberately not used here, so emphasis reads as contrast, not hue.
struct PrimaryButton: View {
    let title: String
    var loading = false
    var enabled = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                if loading {
                    ProgressView().tint(Theme.paper)
                } else {
                    Text(title).font(.system(size: 16, weight: .semibold))
                }
            }
            .frame(maxWidth: .infinity, minHeight: 54)
        }
        .foregroundStyle(Theme.paper)
        .background(enabled ? Theme.ink : Theme.faint)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .disabled(!enabled || loading)
        .animation(.easeInOut(duration: 0.15), value: enabled)
    }
}

/// A quiet text-only button (e.g. "Sign out").
struct QuietButton: View {
    let title: String
    var color: Color = Theme.muted
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title).font(.system(size: 15, weight: .medium)).foregroundStyle(color)
        }
    }
}

private struct UnderlinedField: ViewModifier {
    func body(content: Content) -> some View {
        VStack(spacing: Theme.Space.sm) {
            content
                .font(.system(size: 17))
                .foregroundStyle(Theme.ink)
                .tint(Theme.accent)
            Rectangle().fill(Theme.faint).frame(height: 1)
        }
    }
}

extension View {
    /// A text/secure field styled as a hairline-underlined line, not a boxed
    /// system field.
    func underlinedField() -> some View { modifier(UnderlinedField()) }
}

/// A full-width hairline.
struct Hairline: View {
    var body: some View {
        Rectangle().fill(Theme.faint).frame(height: 1)
    }
}
