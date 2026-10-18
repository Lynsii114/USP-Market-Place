import React from "react";

const legalContent = {
  privacy: {
    title: "Privacy Policy",
    intro: "USP Marketplace collects only the information needed to provide and manage marketplace services.",
    points: [
      "We may collect your name, USP student email, account information, listings, and order details.",
      "Your information is used for account verification and marketplace operations.",
      "Personal information will not be sold or shared unnecessarily with third parties.",
      "Users are responsible for keeping their login details secure.",
      "Marketplace administrators may access necessary account information for system management and security.",
    ],
  },
  terms: {
    title: "Terms of Use",
    intro: "USP Marketplace is designed for USP students to buy and sell items within the university community.",
    points: [
      "Users must provide accurate information when creating an account or listing an item.",
      "Sellers are responsible for the accuracy, condition, and price of their listed items.",
      "Buyers should review item details before making a purchase.",
      "Users must not post illegal, harmful, misleading, or inappropriate items.",
      "The marketplace administrator may remove listings or suspend accounts that violate these terms.",
      "Users are responsible for their own transactions and interactions with other users.",
    ],
  },
};

function LegalPage({ page, onBack }) {
  if (!page) {
    return null;
  }

  const content = legalContent[page];
  if (!content) {
    return null;
  }

  return (
    <section className="legal-page">
      <button type="button" className="secondary-button" onClick={onBack}>
        Back Home
      </button>
      <div className="legal-card">
        <h1>{content.title}</h1>
        <p>{content.intro}</p>
        <ul>
          {content.points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default LegalPage;
