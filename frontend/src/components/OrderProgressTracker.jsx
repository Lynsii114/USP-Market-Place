import React from "react";

export const orderSteps = [
  { key: "order_placed", label: "Order Placed" },
  { key: "payment_confirmed", label: "Payment Confirmed" },
  { key: "preparing_item", label: "Preparing Item" },
  { key: "ready_for_collection", label: "On the Way" },
  { key: "item_received", label: "Item Received" },
  { key: "completed", label: "Completed" },
];

function OrderProgressTracker({ stage }) {
  const currentIndex = Math.max(
    orderSteps.findIndex((step) => step.key === stage),
    stage === "completed" ? orderSteps.length - 1 : 1
  );

  return (
    <div className="order-progress-tracker">
      {orderSteps.map((step, index) => {
        const isCompleted = index < currentIndex || stage === "completed";
        const isCurrent = index === currentIndex && stage !== "completed";
        const state = isCompleted ? "completed" : isCurrent ? "current" : "upcoming";

        return (
          <div className={`order-progress-step ${state}`} key={step.key}>
            <span>{index + 1}</span>
            <strong>{step.label}</strong>
            <small>{state}</small>
          </div>
        );
      })}
    </div>
  );
}

export default OrderProgressTracker;
