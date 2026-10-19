import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function NotificationTrashIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6" />
    </svg>
  );
}

export default function NotificationDismissDialog({ notification, onConfirm, onClose }) {
  const dialogRef = useRef(null);
  const submittingRef = useRef(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    return () => {
      dialog.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);

  const confirm = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      if (await onConfirm(notification.id) === false) {
        setError("Unable to remove this notification. Please try again.");
      } else {
        onClose();
      }
    } catch {
      setError("Unable to remove this notification. Please try again.");
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <dialog ref={dialogRef} className="notification-dismiss-dialog" aria-labelledby="notification-dismiss-title" aria-describedby="notification-dismiss-description" onCancel={(event) => { event.preventDefault(); if (!submittingRef.current) onClose(); }}>
      <span className="notification-dismiss-icon"><NotificationTrashIcon /></span>
      <h3 id="notification-dismiss-title">Remove notification?</h3>
      <p id="notification-dismiss-description">This will remove “{notification.title}” from your notifications. This action cannot be undone.</p>
      {error && <p role="alert" className="notification-dismiss-error">{error}</p>}
      <div className="notification-dismiss-actions">
        <button type="button" className="secondary-button" autoFocus disabled={isSubmitting} onClick={onClose}>Cancel</button>
        <button type="button" className="danger-outline-button" disabled={isSubmitting} onClick={confirm}>{isSubmitting ? "Removing…" : "Confirm removal"}</button>
      </div>
    </dialog>,
    document.body
  );
}
