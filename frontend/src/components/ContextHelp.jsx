import React from "react";

export default function ContextHelp({ label, topic, onOpenHelp, children }) {
  return <details className="context-help">
    <summary aria-label={label} title={label}>?</summary>
    <div className="context-help-content">
      <p>{children}</p>
      {onOpenHelp && <button type="button" className="context-help-link" onClick={() => onOpenHelp(topic)}>Read the FAQ</button>}
    </div>
  </details>;
}
