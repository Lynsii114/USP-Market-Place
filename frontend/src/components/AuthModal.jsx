import React from "react";

function AuthModal({
  authMode,
  authForm,
  emailError,
  formMessage,
  isSubmitting,
  onClose,
  onSubmit,
  onFieldChange,
}) {
  if (!authMode) {
    return null;
  }

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
        <div className="auth-header">
          <h2>{authMode === "signup" ? "Create Account" : "Login"}</h2>
          <button type="button" className="close-button" onClick={onClose} aria-label="Close">
            x
          </button>
        </div>

        <form onSubmit={onSubmit} className="auth-form">
          {authMode === "signup" && (
            <label>
              Name
              <input type="text" name="name" value={authForm.name} onChange={onFieldChange} required />
            </label>
          )}

          <label>
            {authMode === "signup" ? "Username" : "Username or Email"}
            <input type="text" name="username" value={authForm.username} onChange={onFieldChange} required />
          </label>

          {authMode === "signup" && (
            <div>
              <label>
                Email
                <input
                  type="email"
                  name="email"
                  value={authForm.email}
                  onChange={onFieldChange}
                  className={emailError ? "input-error" : ""}
                  placeholder="SXXXXXXXX@student.usp.ac.fj"
                  required
                />
              </label>
              {emailError && <p className="email-error-message">{emailError}</p>}
            </div>
          )}

          <label>
            Password
            <input type="password" name="password" value={authForm.password} onChange={onFieldChange} required />
          </label>

          {formMessage && <p className="auth-message">{formMessage}</p>}

          <button type="submit" className="auth-submit" disabled={isSubmitting}>
            {isSubmitting ? "Please wait..." : authMode === "signup" ? "Sign Up" : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthModal;
