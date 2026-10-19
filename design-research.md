# DaleelAI design benchmark

Observed in a browser on 15 Oct 2026, logged out. Marketing copy is marked as documented, not as a working product flow. Mobbin showed a library homepage only. Dribbble was not opened.

## What was actually opened

| Product | Page | What was visible |
| --- | --- | --- |
| ChatGPT | chatgpt.com | Logged-out app. Sidebar: New chat, Images, Plugins, Deep research. Headline "Where should we begin?". Composer placeholder "Ask ChatGPT". A login panel sits in the sidebar. |
| Perplexity | perplexity.ai | Logged-out app after declining cookies. Sidebar: New, Computer, Automations, Artifacts, Projects, Recents. Center line "What do you want to know?". Search box with Search / Work / Model. A sign-in sheet offers Google, Apple, email. |
| Claude | claude.ai | Redirected to the sign-in page. No conversation was visible. The page sells Free and Pro plans. |
| TurboTax | turbotax.intuit.com | Marketing plus a sign-in form. Documented paths: do it yourself by answering questions, or hand the return to an expert. The interview itself was behind sign-in. |
| H&R Block | hrblock.com | Marketing. Three paths: work with a pro, do your own taxes, free Second Look. A small "AI Chat" prompt was on the page. The chat was not opened. |
| Keeper | keepertax.com and the self-employment calculator | Homepage is marketing for freelancers. The calculator is public: heading, one-line explanation, a "Your details" group (filing status, state, W-2 income, 1099 income), then an explanation of the tax. The result was not submitted. |
| TaxGPT | taxgpt.com and /ai-tax-research | Marketing for accountants. The research page documents three steps: ask in plain language, receive a cited answer, verify. No live research box was available without an account. |
| Mercury | mercury.com | Marketing. One email field, Open account, Launch demo, and a disclaimer that Mercury is not a bank. The bank app was not opened. |
| Stripe | stripe.com | Marketing. Products, Developers, Pricing. No dashboard. |
| Linear | linear.app | Marketing with an embedded issue demo: a narrow sidebar (Inbox, My issues, Projects) and one issue as the page. The real workspace was not opened. |
| Vercel | vercel.com | Marketing. Deploy now, product sections. No dashboard. |
| Mobbin | mobbin.com | Library marketing. Individual screens were not opened. |

## Patterns worth using

- ChatGPT and Perplexity put the first question and the composer in one column. The sidebar is only navigation and history.
- Perplexity and TaxGPT's research page treat the citation as part of the answer, not a stamp.
- Keeper's calculator groups inputs under one heading and explains the figure next to the form. DaleelAI already calculates federal salary, freelancer, and property tax. It should keep that grouping and must not copy US fields such as filing status or state income tax.
- TurboTax and H&R Block split "answer a question", "calculate", and "talk to a person". DaleelAI already has those as chat, calculator, and experts. They should stay separate tools.
- Mercury and Linear earn trust with short type, one action, and a plain disclaimer. DaleelAI already says it is not FBR advice.

## Patterns to avoid

- Glassmorphism. A design search suggested frosted glass and navy. It fights contrast and the brief.
- Copying ChatGPT's purple mark, Perplexity's wordmark, or TurboTax's green.
- A sign-in wall. DaleelAI has no accounts.
- US return-prep steps, Boolean tax research, or invented FBR rates.
- Dribbble-style concept shots as if they were working features.

## Direction

Keep the warm paper canvas, ink text, and emerald only on the primary action and verified state. The change from research is structural:

1. On an empty chat, the welcome sits directly above the composer, the way ChatGPT and Perplexity place the first question.
2. Tool forms use one panel and a grouped fieldset, the way Keeper groups "Your details", with DaleelAI's existing fields only.
3. An answer's confidence, verification, and tax year read as one fact row. Sources stay as cards built from the API.

## Tokens already in the app

Paper `#F6F5F1`, field `#FFFFFF`, ink `#17211D`, muted `#3F514A`, rule `#E3E6E1`, seal `#065C43`, mint `#E7F3EC`. Inter for UI, Newsreader for titles. Motion stays under 240ms and respects reduced motion.

## Screen specification

- Chat empty: headline, six questions, composer immediately under them. After the first answer, the composer docks at the bottom.
- Answer: prose, source badge, fact row, source cards, feedback. No fabricated links.
- Calculator and filer: fieldset of existing inputs, result panel beside or below. Notes from the API stay visible.
- Notice, checklists, experts, updates, evaluation, privacy: same page title and panel, no new workflows.

## Implementation order

1. Pull the empty-state composer up against the welcome.
2. Panel and fieldset on calculator and filer.
3. Fact row on answers.
4. Panel on the remaining tools.
5. Playwright check of chat, calculator, and one tool page.

## Second pass, 15 Oct 2026

Mobbin's connection is ready, but `search_screens` and `search_flows` both returned "Mobbin MCP requires a paid plan." No shipped screens were retrieved. The public Mobbin homepage from the first pass is still the only Mobbin page seen.

### FBR, https://www.fbr.gov.pk/

Opened the homepage. It is a portal, not a guided product. Visible without an account:

- A search box, a news strip, and a carousel.
- Online services: IRIS income tax, TaxRay, sales tax, WeBOC customs, ATL for income tax and sales tax, e-payment, and an online verification portal.
- Income-tax tasks: become a filer, register, file a return, ATL, withholding rates, pay tax.
- Document shelves: Acts, Ordinance, Rules, SROs, orders, publications.
- Helpline 051-111-772-772 and helpline@fbr.gov.pk.
- A linked Finance Act 2026 PDF and overseas guidance for sections 236C and 236K.

DaleelAI should explain these tasks. It should not reproduce the portal's link walls, icon fonts, or carousel.

### IRIS, https://iris.fbr.gov.pk/

Opened IRIS 2.0. The public page is a login plus verifications. Visible labels include ATL (income tax, AJK, sales tax), taxpayer profile inquiry, notices and orders verification, CPR, POS invoice, PSID, and e-payments for income tax, sales tax, immovable property, federal excise, and CVT. Filing itself is behind login. DaleelAI can point a person toward these checks. It does not perform them.

### What changed in the interface

The first pass still read as a chatbot: a large headline, rounded prompt cards, a pill composer, and a green avatar. This pass turns the workspace into a docket.

- Empty chat is a numbered question index plus a record of what an answer can actually show: an Ordinance section, an official link, or a calculator figure.
- The composer is a ruled field across the desk, not a pill.
- On a wide screen, sources sit in a column beside the answer.
- The calculator result leads with the tax year and a large figure.
- Corners are tighter. Emerald stays on the primary action and the verified state.
