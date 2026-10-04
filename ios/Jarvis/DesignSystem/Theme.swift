import SwiftUI

/// Noir palette and type scale. Near-black / near-white, monochrome by default;
/// the one warm accent is reserved for the active/playing state. A soft red is
/// used only for errors. Nothing else carries color.
enum Theme {
    // Palette
    static let paper = Color(red: 0.05, green: 0.05, blue: 0.055)   // background
    static let surface = Color(red: 0.10, green: 0.10, blue: 0.11)  // elevated, rare
    static let ink = Color(red: 0.96, green: 0.96, blue: 0.95)      // primary text
    static let muted = Color(red: 0.60, green: 0.60, blue: 0.63)    // secondary text
    static let faint = Color(red: 0.20, green: 0.20, blue: 0.22)    // hairlines / disabled
    static let accent = Color(red: 0.90, green: 0.72, blue: 0.42)   // warm gold — active only
    static let danger = Color(red: 0.85, green: 0.35, blue: 0.33)   // errors only

    enum Space {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 40
    }
}

extension View {
    /// Full-bleed Noir background + top alignment for a screen's root content.
    func screen() -> some View {
        frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(Theme.paper.ignoresSafeArea())
            .tint(Theme.accent)
    }
}
