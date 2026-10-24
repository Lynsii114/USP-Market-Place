import React from "react";

export const orderSteps = [
  { key: "order_placed", label: "Order Placed" },
  { key: "preparing_item", label: "Preparing Item" },
  { key: "ready_for_collection", label: "On the Way" },
  { key: "item_received", label: "Item Received" },
  { key: "completed", label: "Completed" },
];

function OrderProgressTracker({ stage, paymentMethod, paymentStatus, onAdvance }) {
  const displayStage = stage === "payment_confirmed" ? "order_placed" : stage;
  const steps = paymentMethod === "cash"
    ? [...orderSteps.slice(0, 3), { key: "cash_received", label: "Cash Received" }, ...orderSteps.slice(3)]
    : orderSteps;
  const trackerStage = displayStage === "ready_for_collection" && paymentMethod === "cash"
    ? paymentStatus === "paid" ? "item_received" : "cash_received"
    : displayStage;
  const currentIndex =
    trackerStage === "completed"
      ? steps.length - 1
      : Math.max(steps.findIndex((step) => step.key === trackerStage), 0);

  return (
    <div className="order-progress-tracker">
      {steps.map((step, index) => {
        const isCompleted = index < currentIndex || trackerStage === "completed";
        const isCurrent = index === currentIndex && trackerStage !== "completed";
        const state = isCompleted ? "completed" : isCurrent ? "current" : "upcoming";

        const stepLabel = step.key === "item_received" ? "Received" : step.label;
        const content = <><span>{index + 1}</span><strong>{stepLabel}</strong><small>{state}</small></>;
        const canAdvanceFromHere = onAdvance && (onAdvance.stage === step.key || onAdvance.currentStage === step.key);
        return canAdvanceFromHere ? (
          <button type="button" className={`order-progress-step ${state} clickable`} key={step.key} onClick={onAdvance.run} aria-label={`Advance order to ${onAdvance.nextLabel}`} title={`Click to advance to ${onAdvance.nextLabel}`}>
            {content}
          </button>
        ) : (
          <div className={`order-progress-step ${state}`} key={step.key}>{content}</div>
        );
      })}
    </div>
  );
}

export default OrderProgressTracker;
