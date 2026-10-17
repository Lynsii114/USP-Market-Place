# Inventory management fix log

Related fixes are recorded individually and may be committed together in meaningful chunks after user approval. The original inventory implementation remains credited to the team.

## Earlier combined contribution

- Commit: `cdd93f3` — inventory validation, listing visibility, reservation and order transitions, authenticated API access, regression tests, and an isolated local demo. See INVENTORY_CHANGES.md for details and test results.

## 1. Compact Sold and Reserved badges in product details

- Problem: the generic product-image span styling applied 70px vertical padding to the Sold/Reserved badge, creating a tall red/orange pill.
- Fix: give the category placeholder its own class and scope its large padding to that class. Status badges retain their existing compact padding and top-right placement, including listings with photos.
- Files: `frontend/src/components/ProductModal.jsx`, `frontend/src/Home.css`.
- Verification: frontend production build passed; browser inspection confirms the sold Campus hoodie now shows a compact top-right badge.
- Commit: approved by the user and grouped in `Fix inventory status badges and action menu spacing` (find its hash with `git log --oneline --grep="Fix inventory status badges and action menu spacing"`).

## 2. Floating Actions menu without expanded listing rows

- Problem: the Actions menu used normal document flow, expanding its listing row to the full menu height and creating excessive blank space.
- Fix: position seller listing menus below the Actions button as an overlay. Limit their width and scrolling height, keep them above neighboring rows, and remove obsolete extra right padding from listing rows. Administrator dashboard menus are unchanged.
- Files: `frontend/src/Home.css`.
- Verification: production build passed. Browser measurements confirm all five listing row heights are identical with the menu closed and open; the calculator row remains approximately 73px high. The open menu was visually checked over neighboring content.
- Commit: approved by the user and grouped with fix 1 in `Fix inventory status badges and action menu spacing`.

## 3. Require positive listing prices (SAD FR2.7)

- Problem: zero-price listings were allowed despite the SAD requiring positive prices.
- Fix: reject zero and negative prices on creation and edits; set the listing form minimum to $0.01. Valid positive prices remain accepted.
- Verification: regression tests cover numeric/string zero, negative zero, negative prices, unchanged saved prices after rejection, and a valid $0.01 price. Full suite: 82 tests and 40 subtests passed, two MySQL-only tests skipped; frontend production build passed.
- Commit: approved by the user and grouped in `Align inventory prices and sold listing visibility with SAD`.

## 4. Hide sold listings from normal browsing (SAD FR2.3)

- Problem: sold listings appeared alongside items available for purchase.
- Fix: marketplace browsing and public seller storefronts show only available/reserved listings with positive stock. Sellers retain sold and zero-stock records in My Listings; no records are deleted. Multi-unit listings remain available while stock remains.
- Verification: regression tests cover sold status, inconsistent zero-stock records, owner history, and removal from browsing after payment for the final unit. Full suite: 82 tests and 40 subtests passed, two MySQL-only tests skipped; frontend production build passed.
- Commit: approved by the user and grouped with fix 3 in `Align inventory prices and sold listing visibility with SAD`.

## 5. Repair Sell Item navigation and listing creation access

- Problem: clicking Sell Item ran the React navigation handler and then followed the anchor's native hash link. The resulting history event reset the selected view to Home, so the Add Listing form could not remain open. Home and Shop used the same conflicting navigation pattern.
- Fix: prevent native anchor navigation for Home, Shop, and Sell Item so the existing application handlers control the view and history consistently.
- Files: `frontend/src/components/Navbar.jsx`.
- Verification: reproduced the failure in the browser before the fix; afterward opened Add Listing, submitted a local demo listing successfully, and verified it appeared in My Listings and Shop. Checked Home, Shop, and repeated Sell Item navigation. Frontend production build passed.
- Demo data: added `Sell Item check — local demo` ($12.50, stock 2) to the isolated local demo database only.
- Commit: approved by the user and grouped in `Fix selling navigation and support common photo formats`.

## 6. Support common listing photo formats

- Problem: the picker and JavaScript accepted only JPG/JPEG, excluding common PNG and WebP photos, while relying on file extensions without checking that the image opens.
- Fix: accept JPEG/JFIF, PNG, WebP, and AVIF; rename the field to Item Photo and the preview to Review Photo. Use concise help text: "JPEG, PNG, WebP or AVIF. Max 5 MB." Decode and optimize images to WebP up to 1600px and approximately 1 MB for JSON upload. GIF uploads are excluded at the user's request.
- Handling: reject empty, oversized, unsupported, and unreadable files; prevent submission while a preview is being prepared; ignore stale asynchronous previews after changing/resetting photos; allow reselecting the same file.
- Verification: frontend production build passed. Browser checks passed for PNG, WebP, JPEG/JFIF, rejection of a non-image file, and confirming the PNG preview into the listing form. AVIF is supported through browser decoding but was not separately exercised with a sample file.
- Files: `frontend/src/App.jsx`, `frontend/src/components/SellerPanel.jsx`, `frontend/src/utils/listingPhoto.js`.
- Commit: approved by the user and grouped with fix 5 in `Fix selling navigation and support common photo formats`.

## 7. Require a valid listing photo (SAD FR2.1, FR2.6)

- Require a confirmed photo before saving in the frontend and enforce the rule in the API for new listings and edits. Edits retain the existing photo unless replaced; legacy listings without photos need a photo when edited.
- Verify real JPEG, PNG, WebP or AVIF contents on the server; reject GIF, unsupported data, invalid base64, corrupt/mislabeled images, excessive dimensions and uploads over the saved-image limit. Existing client optimization keeps saved photos around 1 MB or less.
- Verification: API regressions cover missing/invalid photos, supported formats, preserving/removing photos, and editing legacy listings. Browser blocked a photo-less save, then accepted and saved a PNG on the existing local test listing.
- Commit: approved by the user and grouped in `Add inventory photo requirements, filters and seller overview`.

## 8. Add buyer price-range filtering (SAD FR2.4)

- Add inclusive minimum/maximum price filters to marketplace browsing, Shop, and category pages. Combine them with existing search, category and sorting controls. Add an explicit search field to the listings toolbar so keyword search is available in Shop as well.
- Allow either price bound to be omitted; reject negative/non-finite/reversed ranges with a clear message. Clear Filters resets the price bounds too.
- Verification: unit tests cover inclusive boundaries, open bounds, numeric comparisons and invalid ranges. Browser checked $20–$30 filtering, invalid reversed bounds, combined textbook/Books search, and clearing filters.
- Commit: approved by the user and grouped in `Add inventory photo requirements, filters and seller overview`.

## 9. Search and filter My Listings

- Search the seller's own names, descriptions and categories. Combine search with Available, Reserved, Sold and Inactive filters; provide Clear Filters, result counts and a distinct no-matches message.
- Inactive includes administrator-hidden listings; existing restriction labels and disabled actions remain visible.
- Verification: browser search for hoodie plus Sold returned one of six listings, and clearing restored the full inventory.
- Commit: approved by the user and grouped in `Add inventory photo requirements, filters and seller overview`.

## 10. Add a seller inventory summary

- Show total listings, available/reserved/sold/inactive counts, and units currently available. Summary totals use the full seller inventory, independent of search/status filters. Reserved or inactive stock is excluded from available units.
- Initially presented these figures as six cards; the simplified presentation in fix 12 below replaces those cards while keeping the same inventory calculations.
- Verification: unit tests cover empty inventory, status classification and excluding unavailable units. Browser totals matched the six local listings: 3 available, 0 reserved, 1 sold, 2 inactive, 9 available units.
- Commit: approved by the user and grouped in `Add inventory photo requirements, filters and seller overview`.

## 11. Improve seller Actions menu interactions

- Render the menu as a viewport-positioned overlay without expanding rows or clipping inside containers. Open upward when there is insufficient space below, constrain width/height, and reposition on scroll/resize.
- Close on outside click, focus moving outside, Escape, or selecting an action. Focus the first available action when opened and return focus to the trigger on Escape. Filtering closes any open menu.
- Verification: browser confirmed upward placement with the entire menu within the viewport, Escape focus restoration, outside-click dismissal, and successful Edit selection.
- Commit: approved by the user and grouped in `Add inventory photo requirements, filters and seller overview`.

## Verification for priorities 1–5

- Backend: 85 tests and 49 subtests passed; two MySQL-only concurrency tests skipped on SQLite.
- Frontend: five inventory calculation/filter unit tests passed (`node --test src/utils/inventory.test.mjs`); production build passed.
- Local browser checks are recorded above. No production database or remote branch was modified.

## 12. Simplify the My Listings overview

- User feedback: the six summary cards and separate status dropdown made the page feel crowded.
- Replace the six cards with a compact line showing total listings and available units. Move the status counts into clickable All, Available, Reserved, Sold and Inactive filters so each count also performs a useful action.
- Remove the repeated My Listings heading, shorten the search placeholder, and show the result-count message and Clear filters only when filters are active. Keep a visible selected status and keyboard focus indication. On narrow screens the search gets its own row and status filters can scroll horizontally.
- Verification: five frontend inventory/filter tests passed, production build passed, and browser checks confirmed Sold plus hoodie search returned one listing, totals stayed unchanged, and Clear filters restored the complete inventory. Visually reviewed the compact layout in the local browser.
- Files: `frontend/src/components/SellerPanel.jsx`, `frontend/src/Home.css`.
- Commit: approved by the user and grouped with priorities 1–5 in `Add inventory photo requirements, filters and seller overview`.

## 13. Place photo format guidance beneath the picker

- Problem: the accepted image types occupied the neighboring form column and appeared disconnected from the photo input.
- Group the photo label, input and help text in a single form row. Place the accepted formats and size limit directly below the input in smaller, muted text, and retain the screen-reader description link.
- Verification: production build passed; browser inspection confirmed the help text is below the picker and aligned with its left edge. Visually reviewed the updated form.
- Commit: approved by the user; committed in `d58d561`.

## 14. Expand and synchronize listing categories

- Add Study Supplies, Sports & Fitness, Personal Care and Other alongside Books, Electronics, Clothing, Furniture and Footwear. Correct the old Footwares label and keep existing listings compatible with it.
- Share the built-in category definitions across API validation, category responses and demo seeding. Keep frontend options consistent across category cards, browsing filters, listing forms and administrator views. Other appears last and works as a regular product category.
- Bundle representative stock photos locally for the four new categories. Sources, photographers and license details are recorded in `frontend/src/assets/categories/CREDITS.md`.
- Keep administrator-created categories available without duplicate built-in options. Renaming a custom category updates its listings; deleting a category that still contains listings is rejected. Built-in categories cannot be renamed or deleted.
- Verification: backend suite passed 93 tests and 53 subtests, with two MySQL-only concurrency tests skipped locally. Eight frontend tests and the production build passed. Browser verified all nine images loaded, the Sell Item options, administrator cards and the Other page.
- During verification, corrected dashboard daily sales to use the configured timezone consistently; added a regression test for purchases near midnight in Fiji.
- Commit: approved by the user; grouped in `Expand marketplace categories and add stock photos`. No push or production database change.

## 15. Populate the local presentation marketplace

- Extend the isolated local seed command with 75 fictional listings across all nine categories, distributed among admin and three clearly named showcase sellers. Include varied prices and stock, 69 available records, three sold and three seller-inactive records.
- Reuse bundled category photos as representative images; descriptions explicitly identify fictional demo data and category imagery. Personal-care examples are new/unopened. No fake reservations or transaction histories are created.
- Preserve existing listings and edited demo records on reruns. Identify showcase records by the `[IS314 showcase demo]` description prefix and seller/name combination. The command refuses non-local settings and non-SQLite engines.
- Verification: first execution added 75 records; second added zero and found 75 existing. Local database contains 81 listings total, including the previous six; 72 are publicly available. Browser confirmed the populated Shop view.
- Commit: approved by the user; committed in `8787903`. Local SQLite data only; shared MySQL unchanged.

## 16. Keep Recent Listings on Home concise

- Show only the six newest available listings on Home, independent of Shop filters. Remove the repeated search/category/sort/price controls from this preview; the hero search still opens Shop.
- Add View all listings to open the complete Shop with filters reset. Shop retains all available products and its search, category, sorting and price controls. Product details and seller links remain available in the preview.
- Verification: production build passed; browser checks recorded for the six-card Home preview and full Shop navigation.
- Commit: approved by the user; grouped in `Keep the home preview concise and align product seller rows`.

## 17. Align seller details at the bottom of product cards

- Use a vertical flex layout and an automatic top margin on the seller row so variable title heights do not pull seller details upward. Keep consistent bottom padding and allow long seller names to wrap inside the card.
- Applies to every view using ProductCard, including Home, Shop and category listings.
- Verification: production build passed. Browser measured all 72 Shop cards, including one- and two-line titles; every seller row ended 17px from its card bottom (including border). Visually reviewed adjacent cards with different title lengths.
- Commit: approved by the user; grouped in `Keep the home preview concise and align product seller rows`.

## 18. Paginate My Listings

- Display ten matching listings per page with Previous, Next and a bounded set of page numbers. Announce the displayed range and matching total; retain the overall inventory counts independently of pagination.
- Search and status filters operate on the full seller inventory and reset to page one. Close open action menus when changing pages; clamp the current page when the result count shrinks. Hide navigation for zero or one page and disable Previous/Next at the boundaries.
- Verification: production build passed. Browser checked 30 listings over three pages, disabled boundary controls, searching across pages, zero matches, filter resets, unchanged totals, and a final partial page with one of 21 Available listings.
- Commit: approved by the user; grouped in `Paginate inventory and Shop views and fill Home rows`. Frontend only; no database changes.

## 19. Paginate My Sales tabs

- Show ten rows per page in Active Listings, Sold Out Listings and Sales History. Keep tab counts based on all matching records, reset pagination on tab changes, and clamp the page when records change.
- Reuse inventory status classification so hidden/removed listings are excluded from Active Listings and Sold Out Listings. Reserved listings are labelled Reserved.
- Verification: production build passed; browser checked 21 active listings across three pages, a one-row last page, tab reset to four sold listings, and empty sales history. The demo has no orders, so multi-page sales history was not browser-tested.
- Commit: approved by the user; grouped in `Paginate inventory and Shop views and fill Home rows`. No database changes.

## 20. Paginate Shop using complete grid rows

- Show 12 products per page: three rows of four on desktop and complete two-column rows at the existing intermediate breakpoint. Home uses the eight-item preview in fix 21.
- Search, category, price and sort apply to the full loaded catalogue before pagination and reset to page one. Show matching totals, bounded page numbers and disabled boundary controls.
- Verification: production build and eight existing frontend tests passed. Browser checked 12 cards on the first and last of six pages for 72 listings. Full-catalogue search and page reset were also verified during pagination checks.
- Commit: approved by the user; grouped in `Paginate inventory and Shop views and fill Home rows`. Pagination currently limits rendered cards; the API still loads the full catalogue.

## 21. Fill complete rows in Home's recent preview

- Increase the recent preview from six to eight items: two rows of four on desktop or four rows of two at the intermediate breakpoint. Keep View all listings and newest-first ordering. Fewer than eight available listings still display normally.
- Verification: production build passed; checked the eight-item limit against the existing four/two/one-column responsive grid.
- Commit: approved by the user; grouped in `Paginate inventory and Shop views and fill Home rows`.
