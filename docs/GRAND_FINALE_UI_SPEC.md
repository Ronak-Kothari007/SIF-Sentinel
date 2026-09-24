# SIF Sentinel — Grand Finale UI Specification

## 1. Design Vision & Principles
**Goal:** Transform the SIF Sentinel prototype into a polished, premium enterprise industrial safety product.
**Inspiration:** High-quality modern SaaS, operational control rooms, and refined consumer interaction models (smooth transitions, clean hierarchy, purposeful micro-interactions).
**Feel:** Clean, spacious, professional, readable, calm, operational, and trustworthy. Information-dense but never crowded.

### Key Guidelines
- **No "AI Demo" Aesthetics:** Hide technical AI terms (e.g., DistilBERT, vector embeddings). Use user-centric terms like "Safety assessment", "Critical control", "Emerging pattern".
- **Progressive Disclosure:** Show high-level operational status first. Allow drilling down into assessment details.
- **Purposeful Animation:** Use motion to guide attention, indicate state changes, and smooth page transitions (using Framer Motion).

## 2. Design System Tokens (index.css)

### Typography
- **Sans-serif:** `Inter` (UI elements, body text)
- **Monospace:** `JetBrains Mono` (Report IDs, technical codes)
- **Scale:** Modular scale (0.6875rem to 2.25rem)

### Color Palette
- **Neutral (Slate):** Comprehensive slate palette (`--slate-25` through `--slate-950`) for backgrounds, borders, and text.
- **Safety Triage (HSE Standard):**
  - **CRITICAL/HIGH:** Red (`#dc2626`) with soft red glow.
  - **MEDIUM:** Amber (`#d97706`) with soft amber glow.
  - **LOW:** Emerald (`#059669`) with soft emerald glow.
- **Accent:** Industrial Blue (`#0284c7`) and Action Blue (`#2563eb`).

### Layout & Elevation
- **Spacing:** 4px base scale.
- **Elevation:** Refined shadow scale (`--shadow-xs` to `--shadow-2xl`) using subtle opacities for depth rather than harsh borders.
- **Radii:** Smoother corner radii (6px, 8px, 12px) for cards and buttons.

## 3. Shared Component Library

### Badges & Pills (`Badge.jsx`)
- **PriorityBadge:** Distinct pill shape, bold uppercase text, soft colored background, with a subtle glow on hover.
- **StatusBadge:** Confirmed (green), Pending (amber), Rejected (red), Corrected (blue).
- **SeverityBadge:** Specifically for rule severity levels 1-4.

### State Indicators
- **Skeleton.jsx:** Professional shimmer-animated placeholder components for loading states (cards, text, tables, panels).
- **EmptyState.jsx:** Centered icon, title, description, and optional call-to-action button with Framer Motion entrance.
- **ErrorState.jsx:** Clear error icon and retry mechanism.
- **LoadingState.jsx:** Animated bouncing dots or subtle spinner.
- **Toast.jsx:** Floating, stacked notification system (max 5 visible) with smooth slide-in/out animations.

### Utilities
- **PageTransition.jsx:** Wrapper for page components to provide a soft cross-fade and slide on navigation.
- **AnimatedNumber.jsx:** Smoothly counts up from 0 to target value for KPI dashboards.
- **Modal.jsx:** Blurred backdrop, scale-in animation, escape key handling.

## 4. Page-by-Page UX Specification (Upcoming Implementation)

### 4.1 Global Navigation (`Navbar.jsx`)
- **Primary Links:** Overview, Reports, Import Reports, HSE Review, Risk Patterns.
- **Secondary Links (Top-Right):** Notifications, User Profile.
- **Quick Action:** Prominent primary button for `[ + Add Report ]`.
- **Presentation Mode:** Demo controls (Load demo, reset) hidden in a secondary menu or presentation toggle.
- **Behavior:** Active states get an animated bottom underline. Mobile uses a collapsible hamburger menu.

### 4.2 Dashboard: "Safety Overview" (`DashboardPage.jsx`)
- **Focus:** "What requires attention right now?"
- **Header KPIs:** Open HSE Reviews, Critical Safety Signals, Active Actions, Reports Analyzed (using `AnimatedNumber`).
- **Needs Attention Panel:** Large, polished cards for HIGH/CRITICAL reports showing clear status, priority, time, and location.
- **Safety Pulse:** Interactive trend chart showing report activity over time (via Recharts).
- **Emerging Patterns:** Top 3-5 recurring risks with pattern name, count, and trend indicator.

### 4.3 Report Import Workflow (`ImportReportsPage.jsx` - NEW)
- **Upload Zone:** Large drag-and-drop area for PDF, DOCX, TXT, CSV, XLSX.
- **Upload Cards:** Show file name, type, size, and animated extraction status.
- **Review Step:** For text documents, show extracted narrative for editing. For CSV/XLSX, show column mapping interface before bulk import.

### 4.4 Reports Directory (`ReportsPage.jsx`)
- **List View:** Refined data table with sticky headers, subtle row hover states.
- **Filters:** Interactive filter bar for priority, date range, and text search.

### 4.5 Report Details (`ReportDetailsPage.jsx`)
- **Layout:** Two-column grid (`5fr 2fr` split).
- **Left Column:** Report narrative (highlighted), Context Extracted (cards for activity, hazard, barrier), Triggered Rules.
- **Right Column:** Priority assessment, factor scores, AI explanation, and HSE Review actions block.

### 4.6 Risk Patterns (`RiskPatternsPage.jsx`)
- **Visuals:** Visual clusters of related reports rather than simple lists. 
- **Drill-down:** Clicking a pattern reveals the reports that make it up.

### 4.7 HSE Review Workbench (`HSEReviewPage.jsx`)
- **Queue Layout:** Split-pane interface allowing rapid triage of pending reviews.

## 5. Implementation Sequence

1. **Phase 1 (Complete):** Design tokens (`index.css`), shared UI components, animation setup.
2. **Phase 2 (Next):** Global Navigation redesign and routing.
3. **Phase 3:** Overview Dashboard redesign.
4. **Phase 4:** Report Import Workflow (Frontend + Backend).
5. **Phase 5:** Polishing existing pages (Reports, Details, Review, Patterns) with new components.
