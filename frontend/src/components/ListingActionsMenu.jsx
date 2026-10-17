import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export default function ListingActionsMenu({ listing, isOpen, onToggle, onClose, children }) {
  const trigger = useRef(null);
  const panel = useRef(null);
  const [position, setPosition] = useState(null);
  const panelId = `listing-actions-${listing.id}`;

  useLayoutEffect(() => {
    if (!isOpen) { setPosition(null); return; }
    const updatePosition = () => {
      if (!trigger.current || !panel.current) return;
      const bounds = trigger.current.getBoundingClientRect();
      const width = Math.min(220, window.innerWidth - 24);
      const below = window.innerHeight - bounds.bottom - 20;
      const above = bounds.top - 20;
      const naturalHeight = Math.min(panel.current.scrollHeight + 2, 320);
      const opensUp = below < naturalHeight && above > below;
      const maxHeight = Math.max(32, Math.min(320, opensUp ? above : below));
      const height = Math.min(naturalHeight, maxHeight);
      setPosition({ width, maxHeight, left: Math.max(12, Math.min(bounds.right - width, window.innerWidth - width - 12)), top: opensUp ? bounds.top - height - 8 : bounds.bottom + 8 });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const frame = window.requestAnimationFrame(() => panel.current?.querySelector("button:not(:disabled)")?.focus({ preventScroll: true }));
    return () => window.cancelAnimationFrame(frame);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const outsideClick = (event) => {
      if (!trigger.current?.contains(event.target) && !panel.current?.contains(event.target)) onClose();
    };
    const escape = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        trigger.current?.focus({ preventScroll: true });
      }
    };
    document.addEventListener("pointerdown", outsideClick);
    document.addEventListener("focusin", outsideClick);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outsideClick);
      document.removeEventListener("focusin", outsideClick);
      document.removeEventListener("keydown", escape);
    };
  }, [isOpen, onClose]);

  return <div className="admin-action-dropdown">
    <button ref={trigger} type="button" className="admin-action-trigger" aria-label={`Open actions for ${listing.name}`} aria-expanded={isOpen} aria-controls={isOpen ? panelId : undefined} onClick={onToggle}>Actions</button>
    {isOpen && createPortal(
      <div ref={panel} id={panelId} role="group" aria-label={`Actions for ${listing.name}`} className="admin-action-menu listing-actions-popover" style={position || { visibility: "hidden" }} onClick={(event) => { if (event.target.closest("button:not(:disabled)")) onClose(); }}>
        {children}
      </div>, document.body,
    )}
  </div>;
}
