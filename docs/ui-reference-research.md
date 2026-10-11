# KoforLink UI reference research

Reviewed on 9 October 2026. Scope: improve the existing HTML/CSS/JavaScript product for professional networking in Koforidua, Ghana. These references inform original design decisions; they are not downloaded templates or code dependencies.

## Recommended direction

Use a calm editorial identity: warm off-white canvas, deep forest green actions, readable ink text, thin neutral dividers, and a restrained warm accent. Make the landing page feel like a local professional publication, then make the signed-in application behave like a clear networking tool. Real content, specific place names, and considered typography should carry the identity.

Suggested palette: canvas `#F6F5F0`, surface `#FFFFFF`, text `#172C25`, muted text `#57665F`, green `#145B43`, quiet green surface `#EAF0E9`, border `#D9DED7`, warm accent `#BB8F53`. These are proposed design tokens, not sampled source colors; validate actual text/background pairs during implementation.

Use one expressive heading treatment on the public landing page, with a simple sans-serif for navigation, forms, metadata, and application text. Prefer consistent 4/8px spacing, 8–16px component radii, and rules over large ambient shadows. Reserve photography for a single intentional composition, with text beside it rather than over a busy image. Mobile should preserve the content order and usable controls.

## Shortlist and evidence

The web reader verified the text and structure of the live primary sites below. It did not provide complete screenshots or prove their responsive behavior. Visual suggestions are design interpretations of the inspected hierarchy. Pinterest coverage is explicitly more limited.

| Reference | Evidence and source attribution | Useful pattern for KoforLink | Limit / avoid copying |
| --- | --- | --- | --- |
| [Wellfound jobs](https://wellfound.com/jobs) | Original production job platform. Inspected live title/location search, company summaries, role metadata, and separate Save/Apply actions. | A structured opportunity list: role first, company second, location/type/date as subdued metadata. Clear search intent and distinct secondary action. | Its global counts, companies, salaries, and tech startup audience are not KoforLink content. Avoid the older floating-keyword hero found in third-party screenshots. |
| [If You Could Jobs](https://www.ifyoucouldjobs.com/) | Original creative jobs product linked from It's Nice That. Inspected search, discipline/location/level/contract filters, and structured listings with closing dates. | A disciplined opportunity hierarchy and honest missing-data labels. Keep title/company readable before compact filters and chips. | Do not reuse UK roles, salaries, or the source's editorial identity. Keep only filters supported by KoforLink's real API. |
| [It's Nice That](https://www.itsnicethat.com/) | Original editorial publication. Inspected category navigation, featured stories, section labels, story dates, and editorial bylines. | Give community content an editorial rhythm: one clear lead message, smaller supporting sections, restrained category labels, and distinct metadata. | Do not copy its articles, images, or publishing categories. Do not turn the networking app into a magazine with oversized headings everywhere. |
| [Are.na about and features](https://www.are.na/about) | Original community software. Inspected explanation of capture/arrange/search/connect/network, differentiated editorial content, and straightforward account navigation. | Explain networking with useful verbs and an understandable sequence. Let actual content and connections convey the community. | Its member totals, business model, proprietary typeface, and collections functionality are not product requirements for KoforLink. |
| [Kukun, Accra](https://www.kukun.co/) | Original Ghana workspace site. Inspected its Ghana location, specific workspace/community offerings, and first-party photographs exposed as image links. | Ground the public page in a named place and clear professional activities. A real place has stronger character than generic growth language. | Accra is not Koforidua. Do not use its venue photographs as KoforLink assets or imply partnership. No screenshot-level visual assessment was available. |
| [Jambo Spaces, Ghana](https://www.jambospaces.com/) | Original Ghana creator/community hub. Inspected distinct spaces, programmes, events, news, and direct action labels. | Name what people can do: meet people, find an opportunity, discover a business, share work. Distinguish people, opportunities, and organisations in content and navigation. | Avoid importing creator-hub programmes or an unsupported events feature. Its photos and branding require separate permission. |
| [Pinterest: green organic website theme](https://www.pinterest.com/pin/844002786453380158/) | Pin metadata was accessible and attributed the theme to Studio Zash. The pin describes a green/organic Shopify theme. The linked pin image returned 403. | A discovery lead for restrained green and neutral material references; useful only as a mood search, not an inspected layout specification. | Ecommerce structure is a poor fit for networking. No template, assets, or image were copied. Do not claim the pin image was visually reviewed. |
| [Pinterest: community website design](https://in.pinterest.com/pin/community-website-design--1011410028812407505/) | Indexed title was found; direct page retrieval failed. Original creator and image could not be verified. | A saved discovery lead for a future visual board, not a source of accepted interface requirements. | Reject it as implementation evidence until the pin and original creator can be inspected. It cannot prove functionality, originality, or accessibility. |

The Dots returned 403 during this pass. Nextdoor's home page exposed too little content to support useful page-level analysis. Neither is counted as an accepted reference. Browser inspection was also attempted, but the computer-use runtime failed during sandbox initialization; no Pinterest screenshots are claimed.

## Adaptable layouts

1. **Public landing:** a clear brand header; concise Koforidua positioning; two real account actions; a composed image beside the hero; three direct explanations of people, opportunities, and businesses; a final join action. Avoid fake live activity and member counts.
2. **Application shell:** a stable header and deliberate navigation. On desktop, use side navigation and a readable main column; on mobile, keep navigation reachable without overlapping content. The visible active state must match the actual page.
3. **Feed:** compact author block, legible post text, consistent attachment bounds, and quiet action rows. Keep data-driven counts and real empty states; avoid decorative dashboard charts.
4. **Opportunities:** role/company/location/type first, compact description second, then primary action. If data is absent, omit the chip or explain what is missing instead of generating details.
5. **People and companies:** align identity, location, and relevant details across cards. Use initial avatars when photos are absent. Clearly separate profile navigation from connect/follow actions.
6. **Authentication:** shared brand treatment, explicit field labels, a single primary action, clear verification/reset states, and adequate field spacing. Form errors should identify the field and explain the next step.

## Skill research applied

Read the full `C:/Users/HP LAPTOP/.codex/skills/ui-ux-pro-max/SKILL.md` and ran its required design-system generator:

```powershell
python 'C:\Users\HP LAPTOP\.codex\skills\ui-ux-pro-max\scripts\search.py' 'community professional networking jobs local directory calm green neutral content first' --design-system -p 'KoforLink' -f markdown
```

The result recommended a community/forum landing pattern with clear onboarding, topic/category discovery, member content, and a warm neutral base. Its vibrant block style, wellness font pair, and suggested activity statistics were mismatched to this professional/local brief. Retain the useful hierarchy and UX principles; use the reference-led palette and original product content above. The skill's stack-specific guidance is primarily React Native/JavaFX and should not dictate a frontend framework migration.

Also ran the required UX validation query:

```powershell
python 'C:\Users\HP LAPTOP\.codex\skills\ui-ux-pro-max\scripts\search.py' 'animation accessibility z-index loading' --domain ux
```

Applicable output: visible async loading feedback, deliberate stacking contexts, and no continuous decorative animation. During implementation, also verify keyboard focus, labelled inputs, reduced motion, text contrast, meaningful image alternatives, usable small-screen controls, and 375px/768px/1024px/1440px layouts. These are required checks, not claims that they have already passed.

## Photography candidates with verified reuse terms

Use an original photograph, rather than AI imagery, as an illustration of professional work. These images have no verified connection to Koforidua and must not be presented as named members or a real KoforLink event.

- **Christina Morillo / Pexels, photo 1181727:** [asset page](https://www.pexels.com/photo/photography-of-woman-using-laptop-1181727/). The inspected page identifies the photographer and a 5760 × 3840 photograph of a professional Black woman using a laptop. [Direct resized image](https://images.pexels.com/photos/1181727/pexels-photo-1181727.jpeg?auto=compress&cs=tinysrgb&w=1600). Suitable landscape candidate; inspect the actual crop before choosing it.
- **PNW Production / Pexels, photo 8276198:** [asset page](https://www.pexels.com/photo/two-men-talking-to-each-other-about-business-8276198/). The inspected page identifies the photographer and a 4000 × 6000 photograph of two Black men discussing work in an office. [Direct resized image](https://images.pexels.com/photos/8276198/pexels-photo-8276198.jpeg?auto=compress&cs=tinysrgb&w=1600). Suitable portrait candidate for a side-by-side composition; inspect before adoption.

The [official Pexels license](https://www.pexels.com/license/) was inspected. It permits free website/app use and modification; credit is optional but appreciated. It prohibits implying endorsement by the depicted people or brands. Keep the source and creator credit in project documentation if adopted, use neutral descriptive alt text, and serve a local compressed asset instead of depending on a third-party hotlink. Final image selection and crop inspection belong to the implementation pass.
