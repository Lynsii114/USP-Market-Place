import React from "react";

function InfoSection() {
  return (
    <section className="info-section">
      <h2>Why USP Online Marketplace?</h2>

      <div className="info-container">
        <div className="info-card">
          <span>USP</span>
          <h3>USP Community</h3>
          <p>An Online marketplace designed specifically for current USP students.</p>
        </div>

        <div className="info-card">
          <span>Buy</span>
          <h3>Easy Buying</h3>
          <p>Browse used products and find affordable items from other students.</p>
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
