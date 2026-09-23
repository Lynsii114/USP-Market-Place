import React from "react";

function Toast({ message, type = "success" }) {
  if (!message) {
    return null;
  }

  return (
    <div className={`toast-message toast-${type}`} role="status">
      {message}
    </div>
  );
}

export default Toast;
