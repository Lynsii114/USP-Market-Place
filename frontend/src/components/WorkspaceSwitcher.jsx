import React from "react";

export default function WorkspaceSwitcher({ active, onAdmin, onMarketplace }) {
  return (
    <div className="workspace-switcher" role="group" aria-label="Switch workspace">
      <span className="workspace-switcher-label">Workspace</span>
      <button type="button" aria-pressed={active === "admin"} onClick={onAdmin} disabled={active === "admin"}>Admin</button>
      <button type="button" aria-pressed={active === "marketplace"} onClick={onMarketplace} disabled={active === "marketplace"}>Marketplace</button>
    </div>
  );
}
