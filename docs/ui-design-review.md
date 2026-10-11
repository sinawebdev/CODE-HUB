# KoforLink UI direction and independent review

Review date: 9 October 2026. This is the design brief and acceptance checklist for the frontend revamp. Findings below describe the original frontend inspected before implementation; they are not a claim that every acceptance check has passed.

## Direction

1. **Audience and purpose:** professionals, students and businesses in Koforidua and Ghana's Eastern Region; make local people, work and events easy to find.
2. **Tone:** assured, useful, human. Write concrete product copy instead of generic growth slogans or unsupported success stories.
3. **Layout:** an editorial introduction on the public page; compact navigation and readable feed/list/detail structures in the product. Align content to a consistent grid and separate groups with quiet rules.
4. **Typography:** Newsreader with a Georgia fallback for the main marketing statement; Manrope with system sans fallbacks for navigation, forms, feed content and metadata. Keep long text at a comfortable measure, with body text around 15–16px and generous line height.
5. **Color and surfaces:** warm paper, dark ink and forest green. Reserve green for the brand, current location and important actions; use real contrast in both light and dark themes. Avoid glow, gradient text and excessive elevation.
6. **Motion:** immediate repeated actions, short state feedback, no decorative entrance delays. Use explicit transition properties; remove movement when reduced motion is requested and gate hover movement to fine pointers.
7. **Signature:** a typographic local masthead, a narrow geographic label, and an asymmetric editorial grid. Identity comes from this consistent composition rather than adding decorative widgets.

Keep the existing vanilla JavaScript/CSS frontend and its backend contracts. No framework migration is needed for this design work. Preserve API requests, authentication, verified-email routing and database work. Keep source files within the repository's architecture limit.

## Cross-checked reference shortlist

Sources were independently opened with web tools. Text/structure verification is distinct from a rendered screenshot review. The gathering agent maintains the separate visual reference archive.

| Reference | Evidence and source type | Pattern approved for KoforLink | Limits |
| --- | --- | --- | --- |
| [Wellfound jobs](https://wellfound.com/jobs) | First-party live jobs product. The page exposes separate title and location inputs, a Search action, listing metadata, and Save/Apply controls. | Scannable role/company/location metadata; visible search controls; clear primary and secondary listing actions. | Do not copy their startup positioning, job inventory or headline counts. Landing content verification does not prove the signed-in experience or mobile behavior. |
| [It's Nice That](https://www.itsnicethat.com/) | First-party live editorial publication. Opened page exposes distinct categories, lead stories, dated entries and editorial sections. | A clear lead statement; secondary content organized under short section labels; typography and dividers establish hierarchy. | An editorial publication is not a professional networking application. Borrow hierarchy rather than its navigation scale, article content or exact visual identity. |
| [Are.na about](https://www.are.na/about) and [homepage](https://www.are.na/) | First-party live community software. The pages describe organizing content, channels, search and connecting people through ideas. | Understated community framing, readable content organization and honest descriptions of product behavior. | KoforLink requires career discovery and messaging; do not import Are.na's business model or assert its recommendation behavior applies here. |
| [Kukun](https://www.kukun.co/) | First-party Ghanaian coworking/creative community site. Independently opened welcome copy, workspace/café/office descriptions and image gallery. | Ground the product in concrete local professional activity and people rather than generic corporate claims. | This is an Accra physical venue, not an Eastern Region networking platform. Do not imply affiliation or use venue photographs as KoforLink members. |
| [Jambo Spaces](https://www.jambospaces.com/) | First-party African creative hub site. Independently verified space categories, programmes, events and a news section. | Separate practical local destinations from community news; use explicit categories and clear actions. | Its booking and programme flows differ from jobs, profiles and messaging. Borrow content organization only. |
| [Pinterest community website pin](https://in.pinterest.com/pin/community-website-design--1011410028812407505/) | Discovery entry found by the gathering agent; direct web open failed during this independent review. | A visual mood-board candidate only, pending accessible imagery and attribution. | Unverified provenance, responsiveness, accessibility and implementation. It cannot establish a working template. |
| [Pinterest Green Economy HR pin](https://ph.pinterest.com/pin/we-designed-a-clean-and-simple-website-for-green-economy-hr-we-used-the-colors-green-and-blue-to-showcase-the-companys-p--98305204345694932/) | Discovery entry found by the gathering agent; direct web open failed during this independent review. | Potential restrained green/neutral palette reference, pending visual inspection. | A pin title is insufficient evidence of a production product. Do not treat its mockup as an interaction specification. |
| [Pinterest green organic Shopify theme](https://www.pinterest.com/pin/844002786453380158/) | Independently opened pin metadata; creator shown as Studio Zash. The source describes a Shopify theme for small shops, skincare and beauty brands. The gathering agent reported its image URL returning 403. | Color/mood discovery only. | Reject as a functional KoforLink template: ecommerce structure is unsuitable and rendered imagery was not inspected. |

The approved direction is our synthesis, not a claim that any reference uses KoforLink's proposed exact fonts, palette or components. No third-party branded content or assets should be copied. Repeated template features such as fabricated dashboards, meaningless counters, floating mock cards and purple/green glow were rejected because they obscure this product's local purpose.

## Original UI review

The required design-engineering review format is a Before/After/Why table. “After” describes the implementation target and must be verified against the final interface.

| Before | After | Why |
| --- | --- | --- |
| Public hero: generic “Connect. Discover. Work. Grow.”, gradient lettering and floating mock cards. | Specific local-career statement, editorial typography, geographic context and one clear joining action. | A professional identity communicates purpose through composition and copy. |
| Fictional-looking testimonials, fixed engagement counts, a 2025 event and “thousands” claim in public markup. | Real product capabilities; remove unsupported numbers and testimonials, or label any retained sample content explicitly. | Trust requires a clear distinction between evidence and demonstration. |
| Eight similar rounded feature cards plus repeated mock-feed content. | A shorter narrative with distinct visual hierarchy and useful destination links. | Repetition makes the page feel assembled from a template and increases scanning work. |
| Gradients, large shadows and fully rounded controls across unrelated surfaces. | Quiet paper/ink surfaces, limited radii, thin dividers and selective elevation. | Different levels of the interface need different visual weight. |
| Uniform green emphasis on brand, accents, active controls and decorative elements. | Reserve green for identity, current location and primary actions; keep secondary controls neutral. | Users can identify the next useful action more quickly. |
| Sidebar hidden at 820px while the bottom bar omits Companies, Local, Events and Settings. | A labelled mobile overflow destination or other visible access to every route, including staff tools when applicable. | Responsive design must preserve product access. |
| Navigation active state expressed only by class/color. | `aria-current="page"` on the active route, with an obvious non-color cue. | Navigation state must be understandable visually and by assistive technology. |
| Composer opens from a clickable wrapper containing a read-only input. | A real labelled button usable by Enter/Space; retain the existing composer and upload actions. | Semantic controls make the primary feed action discoverable and keyboard-operable. |
| Auth labels appear next to fields without `for`/`id` association. | Associate visible labels to input IDs; use appropriate autocomplete and field-specific validation. | Nearby text alone does not give a form control an accessible name. |
| `openModal` uses `aria-modal` without title association, initial focus, focus containment or focus restoration. | Label the dialog, focus inside it, contain Tab/Shift+Tab, close only the top dialog with Escape, restore the trigger and prevent background interaction. | A modal's semantics must match its keyboard behavior. |
| Buttons and links rely on browser defaults while inputs override focus styling. | Consistent, contrasting `:focus-visible` indicators on all interactive controls. | Keyboard users need a reliable indication of their location. |
| Dark theme uses bright green and hardcoded white text on primary buttons. | Define a theme-aware foreground token and verify the rendered combinations, including hover and disabled states. | Brand colors do not automatically meet text contrast requirements. |
| `.chip` uses `transition: all`; modal/auth/toast entrances bounce and no reduced-motion rule exists in the original stylesheet. | Exact properties, short feedback, non-bouncing professional motion and a reduced-motion override covering inline loading/animation styles. | Frequent actions must feel fast and remain comfortable. |
| Marketing feature and gallery hover transforms also apply to touch. | Restrict movement to `(hover: hover) and (pointer: fine)`; no transformation under reduced motion. | Touch devices can retain hover state after a tap. |

## Acceptance checklist

These are release checks, not completed test claims. Record final evidence in `docs/verification.md` or the implementation report.

- [ ] Public landing communicates the Eastern Region purpose without unsupported testimonials, engagement counts or placeholder footer links.
- [ ] Login, registration, verification and password reset work with the existing API and preserve their loading/error/success states.
- [ ] Auth fields have visible associated labels; password manager/autofill semantics remain intact. See [W3C form labelling](https://www.w3.org/WAI/tutorials/forms/labels/).
- [ ] Every route remains reachable at 390px, 768px and desktop widths, including Companies, Local, Events, Settings and eligible staff tools. No page-level horizontal scroll.
- [ ] Main content is reachable from a keyboard skip link; every action has an accessible name and a visible focus indicator.
- [ ] Active navigation is announced; the home composer opens with pointer and Enter/Space.
- [ ] Modal focus enters, cycles, closes and returns correctly; stacked dialogs close in order. Background content is inert. See [W3C modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
- [ ] Normal text has at least 4.5:1 contrast and large text at least 3:1 in light/dark themes, including muted metadata and button states. See [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- [ ] Aim for 44px touch controls where practical; meet the [WCAG 2.2 minimum target-size requirements](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) and documented exceptions.
- [ ] Light, dark and system appearance modes remain functional; direct landing/auth loads respect stored appearance.
- [ ] Reduced motion prevents scale/translate entrance and hover movement; loading indicators have meaningful status text. Frequent route/list actions have no decorative delay.
- [ ] Feed posting, reactions/comments, job search/save/detail/application, people connections, event detail/RSVP and messages remain real API-backed interactions.
- [ ] Empty, loading and failed-data states stay readable and provide useful recovery; a backend outage is visibly distinct from an empty list.
- [ ] Fonts failing to download do not break layout; content remains readable at 200% zoom and with long names/titles.
- [ ] Run repository architecture and existing relevant test checks. Inspect final landing, auth and at least one populated product page at mobile/desktop in both themes; retain screenshots as actual implementation evidence.

## Review boundary

This review inspected source and independently verified reference-page content. It does not certify full WCAG conformance, a remote deployment, the live Supabase connection, or final browser behavior. Reference screenshots and implementation screenshots must be labelled separately; external mockups cannot count as product verification.

## Rendered implementation review — 11 October 2026

Actual local implementation PNGs in `.validation/ui-after` were opened with the image viewer: landing desktop/mobile; login desktop/mobile; registration mobile; feed desktop/mobile/dark; jobs desktop; messages desktop; and mobile More navigation. These are implementation evidence, separate from reference research. The root agent's browser output in `ui-checks.json` was also inspected, but the independent reviewer did not personally execute those interactions.

The composition now meets the intended identity: an asymmetric typographic public page with illustrative photographs, warm neutral surfaces, forest green and a cohesive product shell. The serif is confined to the public/auth editorial voice; the feed uses readable sans serif text. The desktop feed has clear navigation/content/discovery columns, and mobile preserves a coherent single-column hierarchy. The dark feed uses pale text and pale green actions with dark action text. No obvious clipping was visible in the inspected screenshots.

| Before | After observed in actual screenshots | Why / remaining action |
| --- | --- | --- |
| Generic gradient hero and floating demo cards. | Geographic label, large editorial headline and intentional photo composition. | Distinctive local identity is visible. Approved composition. |
| Repeated public testimonials and unsupported engagement counts. | Capability-oriented sections, practical entry actions and explicitly illustrative photo credits. | Clearer product story and evidence boundary. Approved content direction. |
| Mobile loses secondary destinations when sidebar is hidden. | More menu exposes Profile, Companies, Local, Events, Notifications, Settings and Search. | Important route access is visible in the rendered menu. Actual routing remains an interaction check. |
| Uniform rounded-card treatment throughout the page. | Rules and open editorial columns on marketing; restrained bordered cards for interactive product content. | Surface styling now supports meaning. Approved hierarchy. |
| Dark primary controls use white text on saturated green. | Pale green primary control with dark foreground in the dark feed. | Visually stronger legibility; full contrast audit remains unchecked. |
| New landing/auth punctuation was expected to be polished. | Literal question marks appear in arrows, apostrophes, separators and copyright; examples include `There?s`, `you?re` and `? Back to KoforLink`. | Blocking polish defect confirmed in rendered images and `index.html`; repair encoding/entities and recapture before final approval. |
| Planned readable editorial body text. | Several public paragraphs and controls use 10–12px; tiny footer text uses 8–9px. Auth field labels are 11px. | Increase meaningful body text to 14px or more and secondary copy to 12px; auth labels to around 13px. Preserve hierarchy through spacing and weight. |
| Planned readable product metadata. | Main post text is readable; job metadata, post actions and some rail copy are approximately 10–11px. | Increase critical metadata/actions to at least 12px. This improves practical readability without losing compact layout. |
| More dialog expected to be opaque and settled. | Initial captured menu appears translucent, with underlying feed text visible through it. | Recapture after the entrance settles; if still present, fix opacity/background. This may be a capture-timing artifact, not a lasting component defect. |
| Modal background isolation required. | Source review confirms title, initial focus, Tab wrapping and restoration, but no `inert` handling for background regions. | Implement true background isolation and restore it after the final dialog closes; do not mark modal acceptance complete from focus tests alone. |

Genuinely checked during this independent pass:

- [x] Actual public desktop/mobile composition matches the declared editorial direction.
- [x] Actual login and registration screenshots have a consistent visual hierarchy with no apparent field clipping.
- [x] Actual feed desktop/mobile screenshots preserve content hierarchy and visible navigation.
- [x] Actual dark feed uses the intended dark surfaces and theme-aware primary action foreground.
- [x] Actual mobile More screenshot contains the secondary route labels missing from the original mobile shell.
- [x] Source contains associated auth labels, dialog title association, focus wrapping/restoration, explicit chip transitions and a reduced-motion CSS rule.

Still unconfirmed by this reviewer: pointer/keyboard flows; complete contrast/target-size measurements; all routes at all breakpoints; 200% zoom; reduced-motion runtime behavior; screen-reader behavior; background inertness; authentication/network recovery and full API-backed workflows. The root browser output reports no console errors, no overflow for feed/jobs/messages at 375/768/1024/1440, auth label association, section navigation and modal focus. Those are reported test evidence rather than independently repeated checks.

Sampled color-token calculations (sRGB relative luminance, not a complete rendered audit): light `--text-3` on the page background is 5.05:1; white on the light primary green is 7.11:1; dark primary text on pale green is 8.23:1; dark muted text on a dark surface is 7.13:1. Light `--text-4: #727e73` on `#f5f4ef` is only 3.85:1 and should be darkened where used for placeholders, chat timestamps or other normal text. This sampled failure was sent to the root agent for correction.

## Final fix review — 11 October 2026

This section supersedes the outstanding findings above. Refreshed actual landing desktop/mobile, login desktop, feed desktop/mobile/dark and mobile More PNGs were opened again after fixes. Professional visual quality is approved for the inspected screens: the identity is cohesive, meaningful copy is readable, mobile content fits, and the product retains a calm practical hierarchy.

| Before | After verified | Why / evidence scope |
| --- | --- | --- |
| Literal `?` characters replacing apostrophes, directional symbols and copyright. | Public punctuation and arrows now render correctly, including copyright and the auth back link. | Resolved in refreshed screenshots and HTML entities. |
| Meaningful marketing copy at 10–12px and auth labels at 11px. | Main marketing prose raised to 14–16px, secondary copy at least 12px, auth labels/footer at 13px. | Refreshed screenshots show clearer reading hierarchy; inspected CSS confirms values. |
| Very small app metadata and post actions. | Feed metadata, post actions, navigation and rail copy enlarged while preserving layout. | Refreshed feed mobile/desktop/dark is materially easier to read with no visible clipping. |
| Mobile More screenshot showed feed text through the dialog. | Settled mobile More screenshot has an opaque white dialog, clear title and route labels. | Resolved capture-timing artifact. |
| Modal focus handling lacked background inertness. | `syncModalBackground` isolates body regions and underlying dialogs, locks scrolling, and restores original inert/overflow state when the final dialog closes. | Source inspected; root browser JSON reports focus, background-inert and nested-modal checks passing. The reviewer did not personally repeat runtime interactions. |
| Light `--text-4` contrast was 3.85:1 against paper. | `#647365` yields 4.56:1 against `#f5f4ef` and 5.02:1 against white. | Independent sRGB calculations resolve this sampled failure; they do not constitute a full contrast audit. |
| Dark verification badge had hardcoded white foreground. | Badge uses the theme-aware `--on-brand` token. | Source and refreshed dark feed show an appropriate dark check mark on pale green. |

Both capture cleanup findings are closed. The latest login desktop PNG was opened again and shows settled white input surfaces and the correct forest primary action. The latest dark feed PNG was also opened again: its label now reads `Theme: dark`, its colors are consistent, and normal seeded posts are visible. These were capture inconsistencies, not application defects. No unresolved visual blocker remains in the independently inspected screenshots.

The refreshed `ui-checks.json` reports no console errors, no horizontal overflow for public/login/register and feed/jobs/messages at 375, 768, 1024 and 1440px, associated auth labels, public section navigation, modal focus handling, nested dialogs, background inertness, reduced-motion transition duration and no overflow at a reduced viewport representing 200% zoom. These reported browser checks were inspected independently. A reduced viewport is a useful reflow check; it is not a full browser-zoom/assistive-technology evaluation.

The independent reviewer additionally read `.validation/ui-e2e/e2e-results.json`: all 18 workflow entries have `ok: true`, `badResponses` is empty, and the sole console error is the expected HTTP 400 from the deliberate wrong verification-code check. This validates the reported result artifact; the root agent executed those workflows. The complete scope and release boundary are documented in [ui-enhancement.md](ui-enhancement.md).

Final independent scope: visual/source review and sampled color math passed for the screens and fixes described here. Full WCAG conformance, all screen-reader/browser/device combinations, remote deployment and live database status are not certified by this review. API/browser workflow execution belongs to the root agent's verification report; its 18 passing result entries were independently inspected.
