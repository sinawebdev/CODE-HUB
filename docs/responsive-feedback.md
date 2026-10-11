# Responsive interface and action feedback

Implemented and verified locally on 11 October 2026. Public hosting remains pending; these checks do not establish a live deployment.

## Changes

- Routine feedback appears in a dismissible card at the top centre. Each card has an icon, heading, readable message and accessible status/alert role. Notifications pause while hovered or focused. Errors remain until dismissed. Duplicate messages are combined.
- Post/comment/story/workplace/profile-entry deletion and connection changes use centred confirmation dialogs. The wording describes the effect. Cancel receives initial focus; Escape cancels without sending the action. Focus stays in the dialog and returns to the opener.
- Successful job applications and verification requests have a dedicated completion dialog. The application dialog links to the user's applications. Password changes explain the need to sign in again.
- Likes and saved posts have a short icon pulse and four small particles. Job saves and connection requests also get a short pulse. Animations run after API success, and repeated likes/saves/connection requests are guarded while pending. Failed actions preserve the prior state.
- GSAP 3.14.2 is served locally. The explicitly requested HyperFrames skill's GSAP motion principles inform timing and easing; its video-composition runtime is not used for interactive controls. Reduced-motion preferences skip the effects and stop effects already running.
- Dialog forms stack into one column on small screens and use 16px input text to avoid mobile input zoom. The existing light/dark colour tokens and overall visual direction are retained.
- Share-link fallback and profile-verification notes use labelled application dialogs instead of browser prompts.

## Verification

The local FastAPI/PostgreSQL preview at port 8051 was exercised in Edge:

- **157 responsive scenarios**, including 19 authenticated list/detail routes at 320, 375, 768, 1024, 1440 and 1920 pixels; public landing/login/registration; composer, confirmation, completion and alert states; landscape chat; dark mode and reduced motion. No page or dialog overflow was found.
- **18/18 real API workflows**, including registration/email verification, posting/upload, liking/commenting, profile editing, connections, notifications, messaging, CV/application submission, companies/workplaces, events, search, staff tools and password reset. No server errors or uncaught browser errors were recorded.
- Additional real-action checks established that two immediate like clicks send one request, the like persists, particles are removed, simulated failure preserves the like and leaves a dismissible error, cancelled deletion sends no DELETE, and confirmed deletion sends one DELETE. Keyboard containment/restoration and reduced-motion behavior passed.
- ES-module syntax/import coverage, API mapping, existing client behavior checks and architecture boundaries passed. There are no remaining native `confirm()` or `prompt()` calls in application modules.

Local evidence is ignored by Git: `.validation/responsive-motion/review.json`, `feedback-check.json`, and desktop/mobile/light/dark screenshots. These are local development results, not hosted acceptance or a guarantee for every possible content/device combination.

## Deployment

The alwaysdata account has the free website `koforlink.alwaysdata.net`, PostgreSQL 17 at `postgresql-koforlink.alwaysdata.net`, an existing `koforlink` database user, SSH user and `koforlink@alwaysdata.net` mailbox. The empty `koforlink_app` database has now been created. Its migrations still need to run. Readiness checks must configure persistent media, prove email delivery, switch the default PHP site to the Python app, and verify the public site before reporting deployment complete.
