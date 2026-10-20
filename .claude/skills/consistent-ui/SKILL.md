---
name: consistent-ui
description: Enforce UI consistency across an entire codebase, regardless of language, framework, or styling approach. Detects drift in spacing, typography, colors, components, iconography, and interaction patterns across every UI surface. Works for web (React, Vue, Svelte, Angular, Solid, plain HTML/CSS), native mobile (SwiftUI, Jetpack Compose, Flutter, React Native), and server-rendered templates (Blade, ERB, Twig, Razor, JSP, Pug, Liquid). Generates a consistency report with P0-P3 findings and a remediation plan, then optionally fixes drift in place. Use when the user mentions "consistency", "looks different on page X vs Y", "design drift", "unify styles", "audit components", or wants to align a codebase to its design system.
user-invocable: true
argument-hint: "[path or feature]"
---

Run a cross-codebase consistency sweep. Unlike `/audit` (technical quality on one surface) or `/polish` (final pass on one feature), this skill compares **every UI surface against every other UI surface** and against the project's design system. The goal: same elements look the same everywhere.

If the user provides a scope argument, restrict analysis to that path or feature. Otherwise scan the entire UI codebase.

## Phase 0 — Detect the stack (language-agnostic)

The same drift exists in every stack — only the file extensions and syntax change. Identify what you're scanning before you scan it.

1. **Inventory file types** present in the project. Map to a stack profile:
   - **Web — component frameworks**: `.tsx .jsx .vue .svelte .astro .qwik .solid` (React, Vue, Svelte, Astro, Qwik, Solid)
   - **Web — Angular**: `.ts` paired with `.html` and `.scss`/`.css` templates
   - **Web — plain**: `.html .css .scss .less .styl` and any `<style>` blocks
   - **Web — CSS-in-JS**: `styled-components`, `emotion`, `vanilla-extract`, `panda`, `stitches` (look for `styled.`, `css\``, `sva(`, `cva(`)
   - **Utility CSS**: Tailwind, UnoCSS, Windi (look for `tailwind.config.*`, `uno.config.*`, `class=` strings dense with utility tokens)
   - **Server templates**: `.erb .haml .slim` (Rails) · `.blade.php` (Laravel) · `.twig` (Symfony) · `.cshtml .razor` (.NET) · `.jsp .jspx` (Java) · `.pug .jade` (Pug) · `.liquid` (Shopify/Jekyll) · `.hbs .mustache` · `.html.heex .html.eex` (Phoenix) · `.djhtml` (Django)
   - **Native iOS**: `.swift` with SwiftUI (`View`, `.padding`, `.font`, `Color`) or UIKit (`UIView`, `NSLayoutConstraint`)
   - **Native Android**: `.kt` Jetpack Compose (`@Composable`, `Modifier.padding`, `MaterialTheme`) or `.xml` layouts/styles in `res/`
   - **Flutter**: `.dart` (`Widget`, `EdgeInsets`, `TextStyle`, `ThemeData`)
   - **React Native**: `.tsx .jsx` with `StyleSheet.create`, `View`, `Text`
   - **Other**: Qt `.qml .ui`, GTK `.ui`, Tauri/Electron (web stack inside)

2. **Pick detection patterns** based on stack profile (table in Appendix A). Apply the patterns to drive grep/search. For mixed stacks, scan each profile separately and report per-stack scores plus a combined score.

3. **Detect natural-language locale**: scan a sample of UI strings to learn the project's primary language(s) (English, Spanish, Japanese, etc.). Consistency checks for copy/microcopy must be applied **per locale** — don't compare a Spanish label to an English one. If the project is multilingual, score copy consistency separately for each locale and call out missing translations as a finding.

State the detected stacks and locales back to the user before scanning.

## Phase 1 — Discover the system

Before judging drift, establish the source of truth. Files to look for vary by stack — search broadly, not just for the patterns most common in the stack you saw first.

1. **Locate the design system** — try all that apply:
   - **Tokens**: `tokens.{ts,js,css,json,scss,yaml}`, `theme.{ts,js,css,scss}`, `:root` CSS variables, `design-tokens.json`, Style Dictionary configs, `tailwind.config.*`, `uno.config.*`, `panda.config.*`
   - **Web components**: `components/ui/`, `packages/ui/`, `src/components/`, shadcn registry (`components.json`), MUI/Chakra/Mantine/Ant theme files, Radix wrappers
   - **Native iOS**: `Theme.swift`, `Colors.swift`, `Typography.swift`, `DesignSystem/`, `Assets.xcassets/Colors`, SwiftUI `Environment` extensions
   - **Native Android**: `Theme.kt`, `Color.kt`, `Type.kt`, `Shape.kt`, `res/values/colors.xml`, `res/values/styles.xml`, `res/values/dimens.xml`
   - **Flutter**: `theme.dart`, `app_theme.dart`, `colors.dart`, `text_styles.dart`, `ThemeData` definitions
   - **Style guide docs**: `STYLEGUIDE.md`, `DESIGN.md`, `BRAND.md`, Storybook stories, Figma references in code comments
   - **Other**: Sass partials (`_variables.scss`, `_tokens.scss`), Less variables, design system READMEs in `docs/`

2. **Extract the canon** — record what *should* be used:
   - Spacing scale (e.g., `4, 8, 12, 16, 24, 32, 48, 64` — same scale whether expressed as `space-md`, `EdgeInsets.all(16)`, `.padding(16)`, or `dimen/spacing_md`)
   - Color tokens (semantic names: `bg-primary`, `colorPrimary`, `MaterialTheme.colorScheme.primary`)
   - Typography scale (sizes, weights, line-heights, families)
   - Radius/shape, elevation/shadow, border tokens
   - Motion tokens (durations, easings)
   - Shared components and their canonical APIs (Button, Card, Modal, Input, etc.) — naming may differ (`Button` / `UIButton` / `MaterialButton` / `ElevatedButton` / `<v-btn>`) but role is universal
   - Icon library and conventions (lucide, heroicons, SF Symbols, Material Icons, custom)

3. **If no design system exists**: derive the implicit convention from frequency. The most common values become the de-facto canon. Flag the absence of a system as a P1 systemic finding.

State the discovered system back to the user before scanning, so they can confirm or correct it.

## Phase 2 — Scan for drift

Walk the UI surface area. For each dimension, log every deviation from the canon with file:line.

Each dimension below describes the **role** to check; concrete patterns by stack live in Appendix A. When checking a mixed-stack repo, run each dimension across every detected profile.

### 1. Spacing & Layout
- **Off-scale values**: any padding/margin/gap/inset that isn't in the spacing scale, regardless of how it's expressed (utility class, CSS px/rem, `EdgeInsets`, `Modifier.padding`, `dimen` resource, SwiftUI `.padding`)
- **Inconsistent rhythm**: same section type using different vertical spacing across pages (e.g., page header → body gap is one value here, another there)
- **Container widths**: pages using different max widths for the same content type
- **Stack/grid gaps**: same list pattern using different gap values
- **Mixing units**: `px`, `rem`, `em`, `dp`, `pt`, `sp`, raw points used inconsistently for the same role

### 2. Typography
- **Font families**: more than one sans/serif/mono in use without intent (includes mixing system fonts with bundled fonts, or `SF Pro` with `Roboto` in cross-platform code)
- **Off-scale sizes**: any font size outside the canonical type scale
- **Heading drift**: page titles / H1 / H2 styled differently across pages or screens
- **Weight mixing**: same role using different weights across surfaces
- **Line-height / letter-spacing** inconsistency for the same text role
- **Label/caption** treatment that varies surface-to-surface
- **Native-specific**: SwiftUI `.font(.system(size:))` raw values vs `Font` extensions; Android `sp` literals vs `MaterialTheme.typography`; Flutter inline `TextStyle` vs `Theme.of(context).textTheme`

### 3. Color & Theme
- **Hard-coded values**: any literal hex/rgb/hsl/`Color(red:green:blue:)` / `Color(0xFF...)` / hex in XML outside the token/asset catalog
- **Token bypass**: arbitrary color escape hatches (`text-[#1a1a1a]`, inline `style="color:..."`, `Color.fromARGB`, `UIColor(red:...)`)
- **Token misuse**: same color role used for two different semantics (e.g., red used for both errors AND brand accents)
- **Theme/dark-mode gaps**: components missing dark variants while peers have them; missing `@media (prefers-color-scheme)`, missing iOS/Android dark resources, missing Flutter `darkTheme` mappings
- **Border colors**: ad-hoc borders not from the border token set
- **Opacity hacks**: arbitrary alphas (`bg-black/40`, `Color.black.opacity(0.4)`, `Colors.black54`) instead of defined overlay tokens

### 4. Components & Composition
- **Duplicate components**: multiple implementations of the same role (Button, Modal, Card, Avatar, Tooltip) anywhere in the repo, regardless of file type
- **Inline reimplementation**: pages building a component out of primitives when a shared component exists (`<div onClick>` instead of `<Button>`; `Container + GestureDetector` instead of `ElevatedButton`; `HStack` with raw shadow instead of a `Card` view)
- **API drift**: same shared component called with different prop/parameter conventions across files
- **Variant explosion**: many ad-hoc variants of the same component, none reused
- **Wrapper sprawl**: thin wrappers around shared components that each diverge slightly

### 5. Iconography
- **Multiple icon libraries** mixed without intent (lucide + heroicons + custom SVGs; SF Symbols + bundled PNGs; Material Icons + custom drawables)
- **Size drift**: same icon role rendered at varying sizes across pages
- **Stroke weight / fill style** mismatch: outline icons next to filled icons in the same role
- **Color treatment**: icons inheriting different colors for the same role

### 6. Borders, Radius, Shadows / Elevation
- **Radius / shape drift**: same surface type using different corner radii (CSS `rounded-*`, SwiftUI `.cornerRadius`, Compose `RoundedCornerShape`, Flutter `BorderRadius`)
- **Shadow / elevation inconsistency**: varying shadow intensity for the same element type (CSS `shadow-*`, SwiftUI `.shadow`, Compose `elevation`, Flutter `BoxShadow`/`Material elevation`)
- **Border thickness/style**: inconsistent stroke for the same role

### 7. Interaction & Motion
- **Hover/press/focus states**: inconsistent treatment for the same element type (web hover/focus, native press effects, ripples, scale animations)
- **Transition durations**: varying durations for the same interaction across surfaces
- **Easing functions** mixed without intent (CSS `ease`, SwiftUI `.spring`/`.easeInOut`, Compose `tween`/`spring`, Flutter `Curves.*`)
- **Focus ring / selection indicator**: inconsistent width/color/offset
- **Disabled state**: opacity/color values varying for the same disabled treatment
- **Reduced-motion**: respected on some surfaces, ignored on others

### 8. Form Elements
- **Input heights / touch targets**: varied for the same input role; mobile minimums (44pt iOS, 48dp Android) honored inconsistently
- **Label placement**: above on one form, beside on another, floating on a third
- **Error message** styling that varies form-to-form
- **Required indicators** inconsistent (`*`, `(required)`, color cue, none)
- **Keyboard / IME types**: same input role using different keyboard configs across screens

### 9. Navigation & Page Chrome
- **Page / screen header** patterns differing across routes
- **Breadcrumb / back affordance** style/presence inconsistent
- **Empty states**, **loading states**, **error states** styled differently per surface
- **Toast/snackbar/notification** patterns (position, duration, style) differing
- **Tab bar / bottom nav / sidebar** items styled inconsistently

### 10. Copy & Microcopy (per locale)
- **Capitalization**: Title Case vs Sentence case for the same role (button labels, headings) — apply within each locale
- **Terminology**: same concept named differently ("User" vs "Member" vs "Account") within a locale
- **Punctuation in labels** inconsistent (some end in `:`, some don't)
- **Date/number/currency formatting** varying across views
- **Translation gaps**: strings present in one locale's resource file but missing in another (`.strings`, `strings.xml`, `.arb`, `i18n` JSON, `.po`, `.resx`)
- **Locale leakage**: hard-coded English (or any single language) in code while the rest of the app is localized through resources

## Phase 3 — Report

### Consistency Health Score

| # | Dimension | Score | Top Drift |
|---|-----------|-------|-----------|
| 1 | Spacing & Layout | ?/4 | |
| 2 | Typography | ?/4 | |
| 3 | Color & Theme | ?/4 | |
| 4 | Components | ?/4 | |
| 5 | Iconography | ?/4 | |
| 6 | Borders/Radius/Shadows | ?/4 | |
| 7 | Interaction & Motion | ?/4 | |
| 8 | Forms | ?/4 | |
| 9 | Page Chrome | ?/4 | |
| 10 | Copy & Microcopy | ?/4 | |
| **Total** | | **??/40** | |

**Score guide per dimension**:
- 0 = anarchy (no consistent pattern detectable)
- 1 = mostly inconsistent (scattered tokens, frequent drift)
- 2 = partial system (canon exists but bypassed often)
- 3 = mostly consistent (system used; occasional drift)
- 4 = fully consistent (system enforced everywhere)

**Bands**: 36-40 Excellent · 28-35 Good · 20-27 Acceptable · 12-19 Poor · 0-11 Critical drift.

### Findings by severity

Tag every finding with **P0-P3**:
- **P0**: Breaks the design system contract or causes user-visible inconsistency on critical surfaces (login, checkout, primary CTAs)
- **P1**: Same role rendered differently on 3+ surfaces, or token bypass in shared components
- **P2**: Localized drift, low traffic surface, or single-instance deviation
- **P3**: Micro-inconsistencies (1px difference, near-identical shades) — fix opportunistically

For each finding:
- **[P?] What's drifting** (e.g., "Card radius: 3 different values")
- **Locations**: file:line for each occurrence
- **Canon**: what the design system says (or what the majority pattern is)
- **Recommendation**: replace with `<token / component>`
- **Effort**: trivial / moderate / refactor

### Systemic patterns

Group recurring drift to expose root causes:
- "Buttons reimplemented in 8 places — extract or migrate to `<Button>`"
- "Spacing scale exists but 40% of paddings bypass it via arbitrary values"
- "No semantic color tokens — every component picks raw palette colors"

### Positive findings

What's already consistent. Reinforce what's working so it's preserved during fixes.

## Phase 4 — Remediation plan

Group fixes into waves the user can run independently:

1. **Wave 1 — Token fixes** (mechanical, low risk): replace hard-coded values with tokens, off-scale spacings with scale values
2. **Wave 2 — Component consolidation**: collapse duplicate components, migrate inline reimplementations to shared components
3. **Wave 3 — Cross-surface alignment**: align page chrome (headers, empty states, loading) so same role looks same everywhere
4. **Wave 4 — Polish**: micro-consistencies (1px borders, opacity values, transition durations)

After presenting the plan, ask:

> Want me to apply Wave 1 now, run waves sequentially with confirmation, or just deliver the report?

## Fix mode (when user requests changes)

When fixing, follow these rules:

- **Touch only what drifted** — don't refactor surrounding code
- **One pattern at a time** — don't bundle a button consolidation with a spacing fix
- **Preserve intentional variation** — if a deviation has a comment or clear reason, leave it and note it
- **Verify visual parity** — explicitly call out when a fix may shift pixels, so the user can review
- **Update the canon when needed** — if drift reveals a missing token, propose adding it rather than picking an arbitrary winner

## NEVER

- Invent a design system that isn't there — derive from what exists
- Force consistency where variation is intentional (marketing pages vs app shell often *should* differ)
- Bundle unrelated refactors with consistency fixes
- Report drift without showing the canonical alternative
- Treat all P3 findings as urgent — they're the long tail
- Score generously to be encouraging — be honest, the user wants the truth

Remember: consistency is what makes a product feel like one product. Drift accumulates silently — your job is to surface it, prioritize it, and (when asked) eliminate it without collateral damage.

---

## Appendix A — Detection patterns by stack

Use these as starting points for grep/search. They are not exhaustive — adapt to the codebase. For mixed stacks, run patterns from each profile that applies.

### Web — utility CSS (Tailwind / UnoCSS / Windi)
- Off-scale spacing: `p-\[`, `m-\[`, `gap-\[`, `space-[xy]-\[`
- Hard-coded color: `(text|bg|border|ring|fill|stroke)-\[#`, `(text|bg|border)-\[(rgb|hsl)`
- Off-scale type: `text-\[\d+px\]`, `leading-\[`, `tracking-\[`
- Radius / shadow drift: collect all `rounded-\w+` and `shadow-\w+` per role, compare counts

### Web — CSS / SCSS / Less
- Hard-coded color: `#[0-9a-fA-F]{3,8}\b`, `rgba?\(`, `hsla?\(` outside the token file
- Off-scale spacing: numeric values in `padding|margin|gap|inset|top|left|right|bottom` not matching the scale
- Off-scale type: `font-size:\s*\d+(px|rem|em)` outside type-scale mixins
- Mixed units: `px` vs `rem` vs `em` for the same property family

### Web — CSS-in-JS
- styled-components / emotion: `` styled\.\w+`...` `` blocks; check for inline literals not pulled from `theme`
- vanilla-extract / panda / stitches: arbitrary values inside `style({...})`, `css({...})`, `sva({...})`, `cva({...})` not coming from token recipes
- Inline `style={{...}}` props (any framework) — almost always a drift signal

### Web — components (React / Vue / Svelte / Angular / Solid / Astro / Qwik)
- Component duplication: multiple files exporting the same role name (`Button`, `Modal`, etc.); use `git ls-files` + grep `export (default )?(function|const) (Button|Card|Modal|Input|Avatar|Badge|Tooltip|Dialog|Dropdown|Menu|Tabs|Toast|Toggle|Switch|Spinner|Skeleton)`
- Inline reimplementation: `<div role="button"`, `<div onClick`, `<a class="btn"` outside the shared component layer
- Vue: `<v-btn>` vs `<el-button>` vs `<a-button>` (multiple component libraries coexisting)
- Angular: scan `*.component.ts` selectors and `*.component.html` for duplicate role implementations
- Svelte: `.svelte` files exporting the same component name in multiple locations

### Server-rendered templates
- Repeated markup that should be a partial: same `<button class="...">` markup in many `.erb` / `.blade.php` / `.twig` / `.cshtml` / `.jsp` / `.pug` / `.liquid` / `.hbs` / `.html.heex` / `.djhtml` files
- Inline `style="..."` attributes
- Hard-coded color and font literals inside templates rather than CSS classes

### Native iOS — SwiftUI / UIKit
- Hard-coded color: `Color\(red:`, `UIColor\(red:`, `Color\(0x`, `#colorLiteral`, hex strings parsed at runtime — flag any not coming from a `Color` extension or asset catalog
- Off-scale spacing: `\.padding\(\d+\)`, `Spacer\(minLength: \d+\)`, raw `CGFloat` literals in layout
- Off-scale type: `\.font\(\.system\(size:\s*\d+`, `UIFont\.systemFont\(ofSize: \d+`
- Component duplication: multiple `struct \w+Button: View`, `class \w+Button: UIButton` definitions
- Asset catalog vs hex literals: prefer named colors in `Assets.xcassets`; flag hex literals in code

### Native Android — Jetpack Compose / Views
- Hard-coded color: `Color\(0x`, `Color\.\w+` outside theme, hex in XML `android:textColor`/`background` outside `colors.xml`
- Off-scale spacing: `\.padding\(\d+\.dp\)`, `Modifier\.size\(\d+\.dp\)`, `dp` literals not from `Dimens`
- Off-scale type: `fontSize\s*=\s*\d+\.sp`, `android:textSize="\d+sp"` outside `MaterialTheme.typography`
- Component duplication: multiple `@Composable fun \w+Button`, multiple `class \w+Button : Button`
- XML resources: `<color>`, `<dimen>`, `<style>` defined inconsistently across modules

### Flutter
- Hard-coded color: `Color\(0x`, `Color\.fromARGB`, `Colors\.\w+` outside theme
- Off-scale spacing: `EdgeInsets\.(all|symmetric|only|fromLTRB)\(\d+`, `SizedBox\(width:\s*\d+`
- Off-scale type: inline `TextStyle\(fontSize: \d+` rather than `Theme.of(context).textTheme.*`
- Component duplication: multiple `class \w+Button extends StatelessWidget`
- Theme bypass: widgets ignoring `Theme.of(context)` and inlining values

### React Native
- Off-scale spacing: numeric literals in `StyleSheet.create({ padding: \d+, margin: \d+ })`
- Hard-coded color: hex/rgb literals in styles; flag any not coming from a theme module
- Component duplication: multiple `Button` exports across screens
- Inline styles in JSX (`style={{ ... }}`) with raw values

### Localization files
- Compare keysets across `*.strings` (iOS), `strings.xml` (Android), `*.arb` (Flutter), `i18n/*.json`, `*.po` (gettext), `*.resx` (.NET) — missing keys in one locale = translation gap
- Search for hard-coded UI strings in code that are NOT wrapped in the project's i18n function (e.g., `t(`, `i18n.t(`, `NSLocalizedString`, `getString(R.string.`, `AppLocalizations.of(context)`, `gettext(`)

### General (any stack)
- **Frequency table technique**: for each property of interest (radius, shadow, font-size, padding step), produce a histogram across the codebase. The mode is the de-facto canon; outliers are drift candidates.
- **Cluster by role, not by file**: group occurrences by what the element *does* (primary action button, list row, page header) rather than where it lives. Drift is "same role, different look", which only surfaces after grouping.
