import SwiftUI

struct AuthView: View {
    @Environment(AppModel.self) private var model

    enum Mode { case signUp, logIn }

    @State private var mode: Mode = .signUp
    @State private var email = ""
    @State private var password = ""
    @State private var error: String?
    @State private var working = false

    private var canSubmit: Bool { !email.isEmpty && password.count >= 8 && !working }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Space.xl) {
                header
                modeToggle
                fields

                if let error {
                    Text(error).font(.system(size: 13)).foregroundStyle(Theme.danger)
                }

                PrimaryButton(
                    title: mode == .signUp ? "Create account" : "Log in",
                    loading: working,
                    enabled: canSubmit,
                    action: submit
                )
            }
            .padding(.horizontal, Theme.Space.lg)
            .padding(.vertical, Theme.Space.xl)
        }
        .screen()
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: Theme.Space.sm) {
            Eyebrow("Your daily podcast")
            DisplayTitle("Jarvis", size: 46)
        }
    }

    private var modeToggle: some View {
        HStack(spacing: Theme.Space.lg) {
            modeButton("Sign Up", .signUp)
            modeButton("Log In", .logIn)
            Spacer()
        }
    }

    private func modeButton(_ title: String, _ value: Mode) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.15)) { mode = value }
        } label: {
            VStack(spacing: 6) {
                Text(title)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(mode == value ? Theme.ink : Theme.muted)
                Rectangle()
                    .fill(mode == value ? Theme.ink : Color.clear)
                    .frame(height: 2)
            }
            .fixedSize()
        }
    }

    private var fields: some View {
        VStack(spacing: Theme.Space.lg) {
            TextField("Email", text: $email)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .underlinedField()

            SecureField("Password (8+ characters)", text: $password)
                .textContentType(mode == .signUp ? .newPassword : .password)
                .underlinedField()
        }
    }

    private func submit() {
        error = nil
        working = true
        Task {
            do {
                let token: String
                switch mode {
                case .signUp:
                    token = try await APIClient.shared
                        .signup(email: email, password: password, topics: [])
                        .accessToken
                case .logIn:
                    token = try await APIClient.shared
                        .login(email: email, password: password)
                        .accessToken
                }
                model.signedIn(token: token)
            } catch {
                self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            }
            working = false
        }
    }
}
