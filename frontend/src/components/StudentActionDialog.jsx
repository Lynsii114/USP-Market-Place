import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const reasons = {
  reactivate: ["The student's appeal has been reviewed and approved.", "The suspension was applied in error.", "The student has resolved the issue and agreed to follow marketplace rules.", "Further review found insufficient grounds to continue the suspension."],
  suspend: ["Repeated marketplace rule violations", "Harassment or abusive behaviour", "Suspicious or fraudulent activity", "Inappropriate or misleading listings"],
  delete: ["Student requested account deletion", "Repeated serious marketplace rule violations", "Confirmed fraudulent account activity", "Duplicate or invalid student account"],
};

export default function StudentActionDialog({ student, action, onConfirm, onClose }) {
  const dialogRef = useRef(null);
  const submittingRef = useRef(false);
  const reasonRef = useRef(null);
  const durationRef = useRef(null);
  const [reason, setReason] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [duration, setDuration] = useState("24");
  const [customHours, setCustomHours] = useState("48");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [result, setResult] = useState(null);
  const deleting = action === "delete";
  const hasValidReason = reason.trim().length >= 10 && reason.trim().length <= 500;
  const reactivating = action === "reactivate";
  const actionLabel = deleting ? "Delete" : reactivating ? "Reactivate" : "Suspend";
  const confirmationTitle = deleting ? "Account deletion confirmed" : reactivating ? "Account successfully reactivated" : "Account suspension confirmed";
  const confirmationMessage = deleting
    ? `${student.username}'s account and listings have been permanently deleted. They can no longer sign in to this account.`
    : reactivating
      ? `${student.username}'s account has been reactivated. They can now sign in, and their eligible listings are visible to other customers again.`
      : `${student.username}'s account has been suspended. They cannot sign in, and their listings are hidden from other customers until the suspension ends or an administrator reactivates the account.`;
  const emailMessage = result?.email_status === "sent"
    ? `A confirmation email has been submitted for delivery to ${student.email}.`
    : result?.email_status === "failed"
      ? `The account change is complete, but the confirmation email could not be sent to ${student.email}. Please contact the user separately.`
      : result?.email_status === "console"
        ? `Email delivery is disabled in this environment. No email was sent to ${student.email}.`
        : "Email delivery status is unavailable. Please verify before contacting the user.";

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    return () => { dialog.close(); if (previousFocus?.isConnected) previousFocus.focus(); };
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    if (submittingRef.current) return;
    const errors = {};
    const cleanReason = reason.trim();
    const hours = Number(duration === "custom" ? customHours : duration);
    if (!cleanReason) errors.reason = `Enter a reason before you ${action === "suspend" ? "suspend" : deleting ? "delete" : "reactivate"} this account.`;
    else if (cleanReason.length < 10) errors.reason = "The reason must contain at least 10 characters.";
    else if (cleanReason.length > 500) errors.reason = "The reason must contain no more than 500 characters.";
    if (action === "suspend" && (!Number.isInteger(hours) || hours < 1 || hours > 8760)) errors.duration = "Enter a whole number of hours between 1 and 8,760.";
    setFieldErrors(errors);
    setError("");
    if (Object.keys(errors).length) {
      (errors.reason ? reasonRef : durationRef).current?.focus();
      return;
    }
    submittingRef.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      const data = await onConfirm({ reason: cleanReason, ...(action === "suspend" ? { duration_hours: hours } : {}) });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete this account action.");
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <dialog ref={dialogRef} className="student-action-dialog" aria-labelledby="student-action-title" onCancel={(event) => { event.preventDefault(); if (!submittingRef.current) onClose(); }}>
      <span className="section-kicker">Student account</span>
      <h3 id="student-action-title">{result ? confirmationTitle : `${actionLabel} ${student.username}?`}</h3>
      {result ? <>
        <p role="status">{confirmationMessage}</p>
        {result.user?.suspended_until && <p>Suspended until <strong>{new Date(result.user.suspended_until).toLocaleString("en-FJ", { timeZone: "Pacific/Fiji", dateStyle: "medium", timeStyle: "short" })} (Fiji time)</strong>.</p>}
        <p className={result.email_status === "failed" ? "student-action-error" : "student-action-note"} role={result.email_status === "failed" ? "alert" : "status"}>{emailMessage}</p>
        <button type="button" className="secondary-button" autoFocus onClick={onClose}>Done</button>
      </> : <form onSubmit={submit} noValidate>
        <p>{deleting ? "This permanently deletes the student's account and listings. This cannot be undone." : reactivating ? "Reconsider this suspension and restore the student's access immediately. Record the reason for your decision below." : "The student will be unable to sign in until this suspension expires or an admin reactivates the account."}</p>
        {reactivating && <div className="student-action-note"><strong>Current suspension</strong><p>{student.suspension_reason || "No reason recorded."}</p><p>{student.suspended_until ? `Scheduled expiry: ${new Date(student.suspended_until).toLocaleString("en-FJ", { timeZone: "Pacific/Fiji" })} (Fiji time)` : "Manual reactivation required."}</p></div>}
        <label>Suggested reason
          <select autoFocus value={suggestion} disabled={isSubmitting} onChange={(event) => { setSuggestion(event.target.value); setReason(event.target.value === "Other" ? "" : event.target.value); setFieldErrors((current) => ({ ...current, reason: "" })); }}>
            <option value="">Choose a reason</option>
            {reasons[action].map((value) => <option key={value}>{value}</option>)}
            <option>Other</option>
          </select>
        </label>
        <label>Reason (required)
          <textarea ref={reasonRef} value={reason} disabled={isSubmitting} onChange={(event) => { setReason(event.target.value); setFieldErrors((current) => ({ ...current, reason: "" })); }} rows={3} minLength={10} maxLength={500} required aria-invalid={Boolean(fieldErrors.reason)} aria-describedby={fieldErrors.reason ? "student-reason-error" : undefined} placeholder="Enter a reason (10–500 characters)." />
        </label>
        {fieldErrors.reason && <p id="student-reason-error" role="alert" className="student-action-error">{fieldErrors.reason}</p>}
        {action === "suspend" && <>
          <label>Suspension duration
            <select value={duration} disabled={isSubmitting} onChange={(event) => { setDuration(event.target.value); setFieldErrors((current) => ({ ...current, duration: "" })); }}>
              <option value="1">1 hour</option><option value="24">24 hours</option><option value="72">3 days</option><option value="168">7 days</option><option value="720">30 days</option><option value="custom">Custom duration</option>
            </select>
          </label>
          {duration === "custom" && <label>Duration in hours (1–8,760)<input ref={durationRef} type="number" min="1" max="8760" step="1" required value={customHours} disabled={isSubmitting} aria-invalid={Boolean(fieldErrors.duration)} aria-describedby={fieldErrors.duration ? "student-duration-error" : undefined} onChange={(event) => { setCustomHours(event.target.value); setFieldErrors((current) => ({ ...current, duration: "" })); }} /></label>}
          {fieldErrors.duration && <p id="student-duration-error" role="alert" className="student-action-error">{fieldErrors.duration}</p>}
        </>}
        {reactivating && <p className="student-action-note">An email explaining this action will be sent to <strong>{student.email}</strong>. You will see the email result after confirmation.</p>}
        {error && <p role="alert" className="student-action-error">{error}</p>}
        <div className="notification-dismiss-actions">
          <button type="button" className="secondary-button" disabled={isSubmitting} onClick={onClose}>Cancel</button>
          <button type="submit" className={reactivating ? "auth-submit" : "danger-outline-button"} disabled={isSubmitting || (deleting && !hasValidReason)}>{isSubmitting ? "Processing…" : deleting ? "Confirm deletion" : reactivating ? "Confirm reactivation" : "Confirm suspension"}</button>
        </div>
      </form>}
    </dialog>, document.body
  );
}
