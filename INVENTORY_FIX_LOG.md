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
