import React from "react";

function Footer({ logo, onLegalNavigate }) {
  const handleLegalClick = (event, page) => {
    event.preventDefault();
    onLegalNavigate(page);
  };

  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-brand">
          <h2>USP Buy & Sell</h2>
          <p>
            Buy and sell safely within the
            <br />
            USP student community.
          </p>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="footer-safe">
          <strong>Safe. Trusted. For Students.</strong>
          <span>Verified USP students only.</span>
        </div>

        <div className="footer-copyright">
          <img src={logo} alt="USP logo" className="footer-logo" />
          <p>&copy; 2026 USP Buy & Sell. All rights reserved.</p>
        </div>

        <div className="footer-legal">
          <a href="/privacy" onClick={(event) => handleLegalClick(event, "privacy")}>
            Privacy Policy
          </a>
          <span>|</span>
          <a href="/terms" onClick={(event) => handleLegalClick(event, "terms")}>
            Terms of Use
          </a>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
