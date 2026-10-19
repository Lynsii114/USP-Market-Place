import Breadcrumbs from "./Breadcrumbs";
import React, { useEffect, useRef } from "react";

const questions = [
  { id: "sign-in", question: "How do I register and verify my email?", answer: "Choose Create an account and enter your details, preferably using your USP student email. Enter the six-digit code sent to that address, then set up Microsoft Authenticator to finish registration. If the email does not arrive, check spam and the address you entered. Use Resend code when the countdown ends. Each email verification code expires after 10 minutes." },
  { id: "authenticator", question: "How do I sign in with Microsoft Authenticator?", answer: "Sign in with your username or email and password, then enter the current six-digit code from Microsoft Authenticator. Use the account you added for USP Marketplace. During first-time setup, scan the QR code or enter the setup key in the app before confirming. If a code expires, wait for the next one and check that your phone uses automatic date and time. Back to sign in lets you start again. Password reset does not remove the authenticator requirement, and emergency backup codes are not currently available." },
  { id: "password-reset", question: "How do I reset my password?", answer: "Choose Forgot password on the sign-in screen. Enter the email registered to your account, verify the six-digit code from your inbox, then enter and confirm a new password of at least six characters. Return to sign in and use the new password. Reset codes expire after 10 minutes and can be used once. Request a new code if yours has expired. You will still need your authenticator app when signing in." },
  { id: "listing", question: "How do I sell one item or multiple units?", answer: "Open Sell Item, add a photo, and complete the listing details. Leave Multiple units unchecked for one item. For several units of the same item at the same unit price, enable Multiple units and enter the quantity. JPEG, PNG, WebP and AVIF photos are accepted up to 5 MB; GIF is not supported. The price must be greater than zero. Manage the saved listing from My Activity, then My Listings." },
  { id: "availability", question: "Why can’t I buy a listing?", answer: "You cannot buy your own listing, and sold-out, inactive or administrator-removed listings cannot be purchased. Stock may also have been reserved since you opened the page. Refresh the listing and reduce the quantity if fewer units are available. Cancel an existing unpaid order for the same item before placing another one. Fully reserved listings are hidden from unrelated buyers." },
  { id: "reservations", question: "How do reservations affect the remaining stock?", answer: "An unpaid order holds only the quantity ordered. A seller’s Reserve One Unit action holds one unit for the selected buyer. Other buyers can purchase the unreserved units. Reserved for you identifies your reservation. Multiple-unit listings keep their quantity badge when only one unit remains. A single-item listing does not need a quantity badge. A reservation is not proof that payment has been received." },
  { id: "payments", question: "How do payments and cancellations work?", answer: "With Cash, place the order and pay the seller at pickup or delivery. The seller confirms payment only after receiving it. M-PAiSA, MyCash and card checkout are simulated in this project; a successful simulation is not a real transfer. To cancel an unpaid order, open My Purchases and choose Cancel Order. Sellers can manage unpaid orders from My Sales. Paid or completed orders cannot use this cancellation flow; arrange any refund directly with the seller." },
  { id: "orders", question: "What do the order stages and Sold out mean?", answer: "The tracker shows Order Placed, Payment Confirmed, Preparing Item, On the Way, Item Received and Completed. Order Placed can mean an unpaid reservation. The seller confirms receipt of cash, prepares the item and marks it ready for handoff. A completed order and a sold-out listing are different: a listing is sold out when no stock remains, while a multiple-unit listing can stay available after a sale." },
];

export default function HelpPage({ topic, onBack, signedIn }) {
  const heading = useRef(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return (
    <main className="help-page">
      <Breadcrumbs items={[{ label: signedIn ? "Home" : "Sign in", onClick: onBack }, { label: "Help & FAQs" }]} />
      <button type="button" className="secondary-button" onClick={onBack}>
        {signedIn ? "Back to marketplace" : "Back to sign in"}
      </button>
      <section className="help-card" aria-labelledby="help-heading">
        <p className="auth-kicker">USP Marketplace</p>
        <h1 id="help-heading" tabIndex={-1} ref={heading}>Help & FAQs</h1>
        <p className="help-intro">Find help with your account, listings and orders. Select a question to read the answer.</p>
        <div className="faq-list">
          {questions.map(({ id, question, answer }) => (
            <details className="faq-item" key={id} id={`faq-${id}`} open={topic === id || undefined}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
}
