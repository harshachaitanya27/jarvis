import SwiftUI

struct AuthView: View {
    @Environment(AppModel.self) private var model

    enum Mode: String, CaseIterable { case signUp = "Sign Up", logIn = "Log In" }

    @State private var mode: Mode = .signUp
    @State private var email = ""
    @State private var password = ""
    @State private var topics = ""
    @State private var error: String?
    @State private var working = false

    private var canSubmit: Bool {
        !email.isEmpty && password.count >= 8 && !working
    }

    var body: some View {
        NavigationStack {
            Form {
                Picker("Mode", selection: $mode) {
                    ForEach(Mode.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)

                Section {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password (8+ characters)", text: $password)
                        .textContentType(mode == .signUp ? .newPassword : .password)
                }

                if mode == .signUp {
                    Section("Topics") {
                        TextField("space, jazz history, AI", text: $topics)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }
                }

                if let error {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                Section {
                    Button(action: submit) {
                        HStack {
                            Spacer()
                            if working { ProgressView() } else { Text(mode.rawValue).bold() }
                            Spacer()
                        }
                    }
                    .disabled(!canSubmit)
                }
            }
            .navigationTitle("Jarvis")
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
                    let list = topics
                        .split(separator: ",")
                        .map { $0.trimmingCharacters(in: .whitespaces) }
                        .filter { !$0.isEmpty }
                    token = try await APIClient.shared
                        .signup(email: email, password: password, topics: list)
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
