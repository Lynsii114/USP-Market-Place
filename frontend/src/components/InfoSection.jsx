import React from "react";

function InfoSection() {
  return (
    <section className="info-section">
      <h2>Why USP Buy & Sell?</h2>

      <div className="info-container">
        <div className="info-card">
          <span>USP</span>
          <h3>USP Community</h3>
          <p>A marketplace designed specifically for USP students.</p>
        </div>

        <div className="info-card">
          <span>Buy</span>
          <h3>Easy Buying</h3>
          <p>Browse products and find affordable items from other students.</p>
        </div>

        <div className="info-card">
          <span>Sell</span>
          <h3>Easy Selling</h3>
          <p>List items you no longer need and sell them to other students.</p>
        </div>
      </div>
    </section>
  );
}

export default InfoSection;
