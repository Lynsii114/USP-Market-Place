import React, { useId } from "react";

export default function PriceRangeFields({ minimumPrice, maximumPrice, onMinimumPriceChange, onMaximumPriceChange, priceError }) {
  const errorId = useId();
  return <>
    <label>Min Price ($)
      <input type="number" min="0" step="0.01" placeholder="No minimum" value={minimumPrice} onChange={(event) => onMinimumPriceChange(event.target.value)} aria-invalid={Boolean(priceError)} aria-describedby={priceError ? errorId : undefined} />
    </label>
    <label>Max Price ($)
      <input type="number" min="0" step="0.01" placeholder="No maximum" value={maximumPrice} onChange={(event) => onMaximumPriceChange(event.target.value)} aria-invalid={Boolean(priceError)} aria-describedby={priceError ? errorId : undefined} />
    </label>
    {priceError && <p className="filter-error" id={errorId} role="alert">{priceError}</p>}
  </>;
}
