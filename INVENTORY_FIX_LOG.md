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
