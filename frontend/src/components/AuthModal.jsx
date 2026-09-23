import React, { useEffect, useState } from "react";

function PasswordField({ name, value, onChange, label, required = true }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <label className="password-field">
      {label}
      <span className="password-input-wrap">
        <input type={isVisible ? "text" : "password"} name={name} value={value} onChange={onChange} required={required} />
        <button
          type="button"
          className="password-visibility-button"
          onClick={() => setIsVisible((visible) => !visible)}
          aria-label={isVisible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          title={isVisible ? "Hide password" : "Show password"}
        >
          {isVisible ? "◉" : "◌"}
        </button>
      </span>
    </label>
  );
}

function AuthModal({
  authMode,
  authForm,
  emailError,
  formMessage,
  isSubmitting,
  verificationEmail,
  onClose,
  onSubmit,
  onFieldChange,
  onResendVerification,
  onCancelVerification,
  onMicrosoftLogin,
  microsoftLoginAvailable,
  standalone = false,
  onSwitchMode,
  authenticatorSecret,
  authenticatorUri,
  authenticatorQr,
}) {
  const [setupAcknowledged, setSetupAcknowledged] = useState(false);

  useEffect(() => {
    setSetupAcknowledged(false);
  }, [authMode]);
  if (!authMode) {
    return null;
  }

  const authContent = (
    <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
      <div className="auth-header">
        <div>
          <p className="auth-kicker">USP Marketplace</p>
          <h2>
            {authMode === "signup"
              ? "Create your account"
              : authMode === "verify-email"
                ? "Verify your email"
                : authMode === "forgot-password"
                  ? "Reset your password"
                  : authMode === "reset-password"
                    ? "Choose a new password"
                    : "Welcome back"}
          </h2>
          {authMode === "signup" && <p className="auth-subtitle">Use your USP student email to get started.</p>}
          {authMode === "authenticator-setup" && (
            <p className="auth-subtitle">Add this account to Microsoft Authenticator, then enter the six-digit code.</p>
          )}
          {authMode === "verify-email" && (
            <p className="auth-subtitle">Enter the six-digit code sent to {verificationEmail}.</p>
          )}
          {authMode === "forgot-password" && (
            <p className="auth-subtitle">Enter your USP student email and we will send a reset code.</p>
          )}
          {authMode === "reset-password" && (
            <p className="auth-subtitle">Enter the code sent to {verificationEmail}, then choose a new password.</p>
          )}
        </div>
        {!standalone && (
          <button
            type="button"
            className="close-button"
            onClick={authMode === "verify-email" ? onCancelVerification : onClose}
            aria-label="Close"
          >
            x
          </button>
        )}
      </div>

      {/* FUTURE MICROSOFT ENTRA INTEGRATION:
      {authMode !== "verify-email" && microsoftLoginAvailable && (
        <button type="button" className="microsoft-login-button" onClick={onMicrosoftLogin} disabled={isSubmitting}>
          Continue with USP Microsoft
        </button>
      )}
      */}

      <form onSubmit={onSubmit} className="auth-form">
        {authMode === "verify-email" || authMode === "authenticator" || authMode === "authenticator-setup" || authMode === "reset-password" ? (
          <>
            {authMode === "authenticator-setup" && (
              <div className="authenticator-setup">
                <p>First link this account in Microsoft Authenticator. Scan the QR code below, or enter the setup key manually.</p>
                {authenticatorQr && (
                  <img className="authenticator-qr" src={authenticatorQr} alt="Microsoft Authenticator setup QR code" />
                )}
                <p>In Microsoft Authenticator, choose <strong>+</strong>, select <strong>Other account</strong>, then scan this QR code.</p>
                <code>{authenticatorSecret}</code>
                <p className="authenticator-uri">Or use this setup URI:</p>
                <code>{authenticatorUri}</code>
                <label className="authenticator-confirmation">
                  <input
                    type="checkbox"
                    checked={setupAcknowledged}
                    onChange={(event) => setSetupAcknowledged(event.target.checked)}
                  />
                  I linked USP Marketplace in Microsoft Authenticator
                </label>
              </div>
            )}
            <label>
              {authMode === "verify-email" ? "Verification code" : authMode === "reset-password" ? "Password reset code" : "Microsoft Authenticator code"}
              <input
                type="text"
                name={authMode === "verify-email" ? "verification_code" : authMode === "reset-password" ? "reset_code" : "authenticator_code"}
                value={authMode === "verify-email" ? authForm.verification_code : authMode === "reset-password" ? authForm.reset_code : authForm.authenticator_code}
                onChange={onFieldChange}
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                required
                disabled={authMode === "authenticator-setup" && !setupAcknowledged}
              />
            </label>
            {authMode === "reset-password" && (
              <>
                <PasswordField name="new_password" value={authForm.new_password} onChange={onFieldChange} label="New password" />
                <PasswordField
                  name="new_password_confirmation"
                  value={authForm.new_password_confirmation}
                  onChange={onFieldChange}
                  label="Confirm new password"
                />
              </>
            )}
            {authMode === "verify-email" && (
              <button type="button" className="auth-resend-button" onClick={onResendVerification} disabled={isSubmitting}>
                Resend code
              </button>
            )}
          </>
        ) : (
          <>
            <label>
              {authMode === "signup" ? "Marketplace username" : authMode === "forgot-password" ? "USP student email" : "Username or Email"}
              <input
                type={authMode === "forgot-password" ? "email" : "text"}
                name={authMode === "forgot-password" ? "email" : "username"}
                value={authMode === "forgot-password" ? authForm.email : authForm.username}
                onChange={onFieldChange}
                placeholder={authMode === "forgot-password" ? "S12345678@student.usp.ac.fj" : ""}
                required
              />
            </label>

            {authMode === "signup" && (
              <>
                <label>
                  Personal email
                  <input
                    type="email"
                    name="email"
                    value={authForm.email}
                    onChange={onFieldChange}
                    className={emailError ? "input-error" : ""}
                    placeholder="S12345678@student.usp.ac.fj"
                    required
                  />
                </label>
                {emailError && <p className="email-error-message">{emailError}</p>}
              </>
            )}

            {authMode !== "forgot-password" && <PasswordField name="password" value={authForm.password} onChange={onFieldChange} label="Password" />}

            {authMode === "signup" && (
              <PasswordField
                name="password_confirmation"
                value={authForm.password_confirmation}
                onChange={onFieldChange}
                label="Confirm password"
              />
            )}

            {authMode === "signup" && (
              <p className="auth-verification-note">Your email and authenticator app will be used to verify your account.</p>
            )}
          </>
        )}

        {formMessage && <p className="auth-message">{formMessage}</p>}

        <button type="submit" className="auth-submit" disabled={isSubmitting}>
          {isSubmitting
            ? "Please wait..."
            : authMode === "signup"
              ? "Sign Up"
              : authMode === "verify-email"
                ? "Verify email"
                : authMode === "forgot-password"
                  ? "Send reset code"
                  : authMode === "reset-password"
                    ? "Reset password"
                : ["authenticator", "authenticator-setup"].includes(authMode)
                  ? "Confirm code"
                  : "Login"}
        </button>
      </form>

      {standalone && !["verify-email", "authenticator", "authenticator-setup", "forgot-password", "reset-password"].includes(authMode) && (
        <p className="auth-switch">
          {authMode === "login" ? "New to USP Marketplace?" : "Already have an account?"}{" "}
          <button type="button" onClick={() => onSwitchMode(authMode === "login" ? "signup" : "login")}>
            {authMode === "login" ? "Create an account" : "Log in"}
          </button>
        </p>
      )}
      {standalone && authMode === "login" && (
        <p className="auth-switch">
          <button type="button" onClick={() => onSwitchMode("forgot-password")}>Forgot password?</button>
        </p>
      )}
      {standalone && ["forgot-password", "reset-password"].includes(authMode) && (
        <p className="auth-switch">
          <button type="button" onClick={() => onSwitchMode("login")}>Back to login</button>
        </p>
      )}
    </div>
  );

  if (standalone) {
    return <main className="auth-page">{authContent}</main>;
  }

  return (
    <div className="auth-modal-backdrop" onClick={authMode === "verify-email" ? onCancelVerification : onClose}>
      {authContent}
    </div>
  );
}

export default AuthModal;
