import React, { useRef } from "react";

export default function SearchInput({ value, onChange, placeholder, label = "Search", onSearch, id }) {
  const inputRef = useRef(null);
  return <div className="shared-search-control">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>
    <input ref={inputRef} id={id} type="search" value={value} autoComplete="off" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={label} onKeyDown={(event) => {
      if (event.key === "Enter" && onSearch) { event.preventDefault(); onSearch(); }
      if (event.key === "Escape" && value) { event.preventDefault(); onChange(""); }
    }} />
    {value && <button type="button" className="shared-search-clear" aria-label={`Clear ${label.toLowerCase()}`} onClick={() => { onChange(""); inputRef.current?.focus(); }}>Clear</button>}
  </div>;
}
