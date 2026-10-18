import React from "react";

export default function Breadcrumbs({ items }) {
  if (!items || items.length < 2) return null;
  return <nav className="breadcrumbs" aria-label="Breadcrumb"><ol>
    {items.map((item, index) => <li key={`${index}-${item.label}`}>
      {index > 0 && <span className="breadcrumb-separator" aria-hidden="true">&rsaquo;</span>}
      {item.onClick && index < items.length - 1
        ? <button type="button" onClick={item.onClick}>{item.label}</button>
        : <span aria-current={index === items.length - 1 ? "page" : undefined}>{item.label}</span>}
    </li>)}
  </ol></nav>;
}
