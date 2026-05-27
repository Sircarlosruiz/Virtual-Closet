# UX Guide

## Overview

shadcn/ui component library on top of Tailwind CSS. WCAG AA accessibility. Mobile-first responsive design. The target user is a wholesale clothing vendor (mayorista) — not a developer — so interfaces must be intuitive and visually trust-building.

---

## Design System / Component Library

**Library**: shadcn/ui
**Base**: Radix UI primitives (accessible by default)
**Registry**: components added via `npx shadcn-ui@latest add {component}`

**Conventions**:
- shadcn components live in `frontend/components/ui/`
- Never modify shadcn base components directly — extend via composition or wrapper components
- Use shadcn variants (`variant`, `size` props) before reaching for custom CSS

---

## Styling Approach

**Tool**: Tailwind CSS (utility-first)
**Config**: `tailwind.config.ts` defines the design tokens (colors, fonts, spacing)

**Rules**:
- Utility classes in JSX — no separate CSS files unless unavoidable
- Custom tokens via `theme.extend` in Tailwind config, not hardcoded hex values
- Dark mode: class-based (`class="dark"`) if supported — shadcn/ui handles this natively
- No inline `style={{}}` except for dynamic values that can't be expressed as utilities (e.g., computed widths for image previews)

**Color palette**:
- Brand colors defined in `tailwind.config.ts` under `theme.extend.colors`
- Status colors: success (green), warning (amber), error (red), info (blue) — use Tailwind semantic names

---

## Accessibility Standards

**Target**: WCAG AA (Level 2.1)

**Requirements**:
- All images have meaningful `alt` text (garment photos must describe the garment)
- Color is never the only way to convey information (always pair with text or icon)
- Interactive elements have visible focus indicators (Tailwind `focus-visible:ring` pattern)
- Form inputs have associated `<label>` elements
- Modals trap focus and are dismissible with Escape
- Minimum touch target size: 44×44px (mobile)
- Radix UI primitives (via shadcn/ui) handle ARIA roles and keyboard navigation automatically — don't override without good reason

---

## Responsive Design Strategy

**Approach**: Mobile-first — base styles target mobile, `sm:`, `md:`, `lg:` breakpoints scale up

**Breakpoints** (Tailwind defaults):
- `sm`: 640px — tablet portrait
- `md`: 768px — tablet landscape
- `lg`: 1024px — desktop
- `xl`: 1280px — wide desktop

**Key patterns**:
- Catalog grids: 1 column (mobile) → 2 columns (sm) → 3–4 columns (lg)
- Garment upload: full-screen on mobile, side-by-side panel on desktop
- Navigation: bottom nav bar (mobile) → sidebar (desktop)
- VTON preview: stacked (mobile) → side-by-side before/after (md+)

---

## Key UX Principles

**Trust through visuals**: The product sells by showing realistic AI-generated catalog images. Image quality and loading states are first-class concerns.

**Progress transparency**: VTON jobs take time. Always show job status (queued → processing → done), never leave the user guessing.

**WhatsApp-first sharing**: Catalog links are shared via WhatsApp. OpenGraph metadata (`og:title`, `og:image`) must be correct on all public catalog pages so previews render correctly.

**Onboarding speed**: A mayorista should be able to upload their first garment and see a generated catalog image within 5 minutes of signing up.
