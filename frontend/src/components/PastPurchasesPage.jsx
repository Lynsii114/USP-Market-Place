import React, { useState } from "react";

function PastPurchasesPage({ currentUser, purchases, onBack, onLogin }) {
  const [isConfirmingDownload, setIsConfirmingDownload] = useState(false);
  const totalSpent = purchases.reduce((total, purchase) => total + Number(purchase.price), 0);
  const formatPurchaseDate = (value) =>
    new Date(value).toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  const cleanPdfText = (value) =>
    String(value)
      .replace(/[^\x20-\x7E]/g, "?")
      .replace(/[\\()]/g, "\\$&");
  const truncatePdfText = (value, maxLength = 70) => {
    const text = cleanPdfText(value);
    return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
  };
  const createPdfReport = () => {
    const generatedAt = new Date().toLocaleString();
    const commands = [];
    const addText = (text, x, y, size = 10, font = "F1", color = "0.08 0.14 0.22") => {
      commands.push(`${color} rg BT /${font} ${size} Tf ${x} ${y} Td (${cleanPdfText(text)}) Tj ET`);
    };
    const addLine = (x1, y1, x2, y2) => {
      commands.push(`0.84 0.88 0.93 RG ${x1} ${y1} m ${x2} ${y2} l S`);
    };

    commands.push("0.05 0.18 0.30 rg 40 710 532 52 re f");
    addText("USP", 58, 730, 18, "F2", "1 1 1");
    addText("USP MARKETPLACE", 112, 736, 16, "F2", "1 1 1");
    addText("Past Purchases Report", 112, 720, 10, "F1", "1 1 1");
    addText("Generated from the USP student marketplace system", 365, 720, 8, "F1", "1 1 1");

    addText("Customer Details", 44, 680, 12, "F2");
    addText(`Name: ${truncatePdfText(currentUser.username, 45)}`, 44, 662);
    addText(`USP Email: ${truncatePdfText(currentUser.email, 55)}`, 44, 646);
    addText(`Generated: ${generatedAt}`, 44, 630);
    addText("Report Contact", 350, 680, 12, "F2");
    addText("Use seller contact details for each item.", 350, 662);
    addText("Marketplace: USP student community", 350, 646);

    addLine(40, 610, 572, 610);
    addText("Items Paid", 44, 588, 12, "F2");
    addText("Item", 44, 566, 9, "F2");
    addText("Seller Contact", 230, 566, 9, "F2");
    addText("Unit Cost", 405, 566, 9, "F2");
    addText("Date & Time", 485, 566, 9, "F2");
    addLine(40, 556, 572, 556);

    let y = 536;
    purchases.slice(0, 18).forEach((purchase, index) => {
      addText(`${index + 1}. ${truncatePdfText(purchase.item_name, 28)}`, 44, y);
      addText(truncatePdfText(purchase.category, 28), 44, y - 14, 8);
      addText(truncatePdfText(purchase.seller_contact || purchase.seller_username, 28), 230, y);
      addText(`Seller: ${truncatePdfText(purchase.seller_username, 24)}`, 230, y - 14, 8);
      addText(`$${Number(purchase.price).toFixed(2)}`, 405, y);
      addText(formatPurchaseDate(purchase.purchased_at), 485, y, 8);
      addLine(40, y - 24, 572, y - 24);
      y -= 42;
    });

    if (purchases.length > 18) {
      addText(`Additional purchases not shown: ${purchases.length - 18}`, 44, y);
      y -= 28;
    }

    addText("Total Amount Paid", 350, Math.max(y, 72), 12, "F2");
    addText(`$${totalSpent.toFixed(2)}`, 486, Math.max(y, 72), 14, "F2");
    addText("This report is generated for personal record keeping.", 44, 44, 8);
    const textCommands = commands.join("\n");
    const objects = [
      "<< /Type /Catalog /Pages 2 0 R >>",
      "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
      `<< /Length ${textCommands.length} >>\nstream\n${textCommands}\nendstream`,
    ];
    let pdf = "%PDF-1.4\n";
    const offsets = [0];

    objects.forEach((object, index) => {
      offsets.push(pdf.length);
      pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });

    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    offsets.slice(1).forEach((offset) => {
      pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

    const blob = new Blob([pdf], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `usp-marketplace-purchases-${Date.now()}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setIsConfirmingDownload(false);
  };

  return (
    <section className="purchase-page" id="past-purchases">
      <div className="cart-header">
        <div className="section-heading">
          <span className="section-kicker">Report</span>
          <p>Items you have checked out, including purchase date and time.</p>
        </div>
        <button type="button" className="close-panel-button" onClick={onBack} aria-label="Close past purchases">
          x
        </button>
      </div>

      {currentUser ? (
        purchases.length ? (
          <>
            <div className="report-download-actions">
              <button type="button" className="auth-submit report-download-button" onClick={() => setIsConfirmingDownload(true)}>
                Download PDF Report
              </button>
            </div>

            <div className="purchase-report-table-head">
              <span>Item</span>
              <span>Unit Cost</span>
              <span>Date &amp; Time</span>
            </div>
            <div className="purchase-report-list">
              {purchases.map((purchase) => (
                <div className="purchase-report-item" key={purchase.id}>
                  <div>
                    <strong>{purchase.item_name}</strong>
                    <small>{purchase.category}</small>
                  </div>
                  <div>
                    <span>${Number(purchase.price).toFixed(2)}</span>
                    <small>Contact: {purchase.seller_contact || purchase.seller_username}</small>
                  </div>
                  <time dateTime={purchase.purchased_at}>{formatPurchaseDate(purchase.purchased_at)}</time>
                </div>
              ))}
            </div>

            <div className="purchase-total-card">
              <div>
                <span>Total Amount</span>
                <strong>${totalSpent.toFixed(2)}</strong>
              </div>
            </div>

            {isConfirmingDownload && (
              <div className="auth-modal-backdrop" onClick={() => setIsConfirmingDownload(false)}>
                <div className="report-confirm-modal" onClick={(event) => event.stopPropagation()}>
                  <h3>Download PDF Report?</h3>
                  <p>Your browser will save the purchase report as a PDF in your downloads folder.</p>
                  <div className="checkout-actions">
                    <button type="button" className="secondary-button" onClick={() => setIsConfirmingDownload(false)}>
                      Cancel
                    </button>
                    <button type="button" className="auth-submit" onClick={createPdfReport}>
                      Confirm Download
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="empty-state">No past purchases yet.</p>
        )
      ) : (
        <div className="signin-prompt">
          <p>Login to view your past purchases.</p>
          <button type="button" className="auth-submit" onClick={onLogin}>
            Login
          </button>
        </div>
      )}
    </section>
  );
}

export default PastPurchasesPage;
