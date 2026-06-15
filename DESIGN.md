---
name: Study Pilot Professional
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#4b41e1'
  on-secondary: '#ffffff'
  secondary-container: '#645efb'
  on-secondary-container: '#fffbff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#191c1e'
  on-tertiary-container: '#818486'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#3323cc'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  stats-num:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  section-gap: 64px
---

## Brand & Style

The design system is engineered for the high-performing student, evoking a sense of calm authority, precision, and cognitive clarity. It utilizes a **Modern Corporate** aesthetic with **Minimalist** foundations to eliminate academic overwhelm. 

The visual narrative centers on "The Path of Least Resistance"—using expansive whitespace to frame complex data, ensuring the user feels in control rather than buried under tasks. Every interface element serves a functional purpose, with subtle "intelligent" flourishes like soft background blurs and micro-interactions that reinforce the AI’s sophisticated nature. The result is a premium workspace that feels like a private digital tutor: focused, reliable, and effortless.

## Colors

The palette is anchored by **Midnight Navy** (#0F172A) for deep contrast and authoritative text, paired with **Electric Indigo** (#4F46E5) as the primary action color to signal intelligence and technological precision. 

- **Primary (Midnight Navy):** Used for primary headings and heavy structural elements.
- **Secondary (Electric Indigo):** Reserved for primary CTAs, active states, and AI-driven insights.
- **Background (Slate Tint):** A base of #F8FAFC keeps the interface feeling airy and "high-end."
- **Success (Emerald):** Used sparingly for "Standard" or "Complete" statuses to provide a calming reassurance.
- **Neutral (Slate):** Various shades of slate are used for secondary text and borders to maintain low visual noise.

## Typography

The design system exclusively utilizes **Inter** to leverage its exceptional legibility and neutral, modern character. 

Hierarchy is established through tight letter-spacing in headlines for a "compact" premium look, while body text is given generous line height to promote readability during long study planning sessions. Labels use a slightly increased letter-spacing and semi-bold weight to differentiate themselves from instructional text without requiring additional color weight. For numerical data (like study hours), a specialized `stats-num` style ensures progress metrics are the most prominent elements on the dashboard.

## Layout & Spacing

This design system follows a **Fixed-Fluid hybrid grid**. On desktop, the main content is housed in a 1280px central container with a 12-column structure. On mobile, it transitions to a single-column layout with 16px safe margins.

The spacing rhythm is strictly based on an **8px base unit**. 
- **Section Gaps:** 64px (8 units) between major content blocks to ensure "plenty of whitespace" as requested.
- **Component Padding:** Internal card padding is set to 24px or 32px to provide a luxurious, uncrowded feel.
- **Vertical Rhythm:** Smaller 8px and 16px increments are used to group related labels and inputs, creating clear "information clusters" that reduce cognitive load.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layering** and **Ambient Shadows**. Instead of heavy borders, the system uses "Soft Depth" to define interactive areas.

- **Level 0 (Base):** The main background in #F8FAFC.
- **Level 1 (Cards):** Pure white (#FFFFFF) surfaces with a very soft, high-diffusion shadow (0px 4px 20px rgba(15, 23, 42, 0.05)).
- **Level 2 (Active/Hover):** Enhanced shadow (0px 10px 30px rgba(15, 23, 42, 0.08)) to indicate interactivity.
- **Glassmorphism:** Navigation bars and sticky headers utilize a backdrop blur (20px) with 80% opacity to maintain context of the content underneath while providing a modern, premium feel.

## Shapes

The shape language is defined as **Rounded**, striking a balance between professional precision and approachable modern software.

- **Standard Elements:** Inputs and buttons use a 0.5rem (8px) radius.
- **Container Elements:** Cards and study blocks use 1rem (16px) to soften the large surface areas.
- **Status Pills:** Badges and "Chips" use full pill-rounding (999px) to clearly distinguish them from actionable buttons.

## Components

### Buttons
- **Primary:** Electric Indigo background, white text, no border. Subtle scale-down effect on click (0.98x).
- **Secondary:** Transparent background with a thin 1px Slate-200 border. Transitions to a light slate ghost-fill on hover.

### Input Fields
- Floating label style with 1px border (#E2E8F0).
- **Focus State:** Border changes to Electric Indigo with a 3px soft outer glow (Indigo at 10% opacity).

### Cards
- **Study Block Cards:** Feature a left-accent border (4px) in Indigo to indicate "active" or "next."
- **Dashboard Widgets:** Use centered typography for "Quick Stats" to emphasize the data.

### Progress & Visualization
- **AI Indicator:** A subtle animated gradient (Indigo to Violet) used for "Generating" states.
- **Study Limit Slider:** Custom-styled with a prominent Indigo thumb and a light Slate track to maintain the "clean" aesthetic.

### Lists
- Subject lists use generous vertical padding (16px) with hairline dividers (#F1F5F9) to prevent visual clutter in data-heavy views.
