# UI and UX specification

## Navigation and layout

Use a compact workspace header with workspace name/switcher, account menu and help. Desktop has a stable left rail for Overview, Assessment, Actions, Domains and Reports. Settings is owner-only. On phones a labeled Menu button opens the same links below the header. Preserve destination and active state across layouts. Use a one-column flow on narrow screens, then a wide main column with supporting information alongside it where space permits.

```text
[Workspace ▾]                         [Help] [Account]
[Menu on phone / navigation rail on desktop]
Overview
[Continue assessment or view latest baseline]
[Your next three actions]
[Recent domain observations, if available]
[Reports]
```

## Design system

Use the working AegisOne Open wordmark as text until brand approval. Use system UI type for low transfer cost, with 1rem body / 1.5 line-height, 0.875rem minimum secondary labels and fluid 1.5–2rem main titles with modest tightening. Use rem spacing on a 4/8/16/24/32 px equivalent scale. Suggested palette is navy ink #17253A, gray-blue secondary #45566D, white cards, light canvas #F4F7FA and teal primary #075E58. Validate contrast for all state pairings. Use severity text and icons together. Use light borders and solid surfaces with a scrim for blocking dialogs. Reserve imagery for help content when it explains a task and has cleared rights.

| Surface | Essential content and states |
|---|---|
| Invite, sign-in, MFA, recovery | Identity and workspace context, expired/used links, confirmation, generic recovery response and support |
| Overview | Start, continue or view assessment. Show first-use, complete, action-empty and refresh failure states without a placeholder score |
| Assessment | Section and question progress, response controls, back/continue, saved or unsaved indicator, check before submit, inline errors, resume and stale-edit recovery |
| Actions | Priority/status filters, clear labels, empty-filter reset, next steps, accessible status controls and conflict recovery |
| Domains | Verify instructions, copy challenge, pending, verified/expiry, failed, rate capped, disabled, stale and inconclusive states. Display last observation separately from pending work |
| Reports | Explain scope, preview, save, open and print. Show empty, unavailable, revoked and initial loading states |
| Settings, legal and support | Invite/remove, export and closure request statuses, identity checks, terms/privacy and reachable support. Confirm irreversible closure with impact summary |

## Interaction and motion

Use apple-design principles for immediate response, spatial continuity and agency. Show pressed styling on pointer-down and commit on release or keyboard activation. Show “Saving” as soon as a request is issued, then “Saved” only after server confirmation. Keep focus on the active control during background work. Announce meaningful transitions through a polite live region. For errors, keep entered values visible, focus the error summary where appropriate, and give a retry path. Use indeterminate text for work of unknown duration and stop status polling when the page is hidden or the job resolves.

Anchor menus to their triggers and return focus to the opener on Escape or dismissal. Use at most a 120–160 ms fade for menus and dialogs. Reverse from current opacity without delaying input or closing the focus trap early. With reduced motion, use static transitions. Core controls work through pointer, touch and keyboard with 44 px target size for primary controls, no gesture-only actions, and no hover-only disclosure. Solid surfaces support reduced transparency by default. Increased contrast uses stronger borders, and forced-colors preserves native focus outlines and visible control boundaries.

## Acceptance and research

Target WCAG 2.2 AA. Test keyboard traversal, 320 CSS px reflow, 200% text zoom, focus visibility and restoration, contrast, screen readers on desktop and mobile, and printed layout. Pair automation with manual tests. Use plain English, localize presentation of dates from a stored workspace timezone, keep UTC in exports, and externalize copy for future translations and longer strings. Test on low-end Android and constrained mobile links. Moderated tasks are first assessment, highest-priority action, failed DNS verification and finding/printing a report. Product owns copy and security reviewers confirm guidance accuracy. [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)
