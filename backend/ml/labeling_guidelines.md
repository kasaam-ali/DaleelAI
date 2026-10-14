# Classifier labeling guidelines

Use these rules when labeling questions for the domain classifier. Labeling can run while the tax tools are being built. The served model is trained later. Do not invent a label to force a question into a class.

## What you label

Each row is one user question, in English or Roman Urdu. Store the question only after personal details are replaced with the placeholders in `contracts/pii_cases.json` (CNIC, NTN, phone, email, name, address). An unlabeled amount such as `25000000` stays. It is rupees, not an NTN.

Give each question one domain and one complexity:

| Field | Allowed values |
|---|---|
| domain | `income_tax`, `sales_tax`, `customs`, `corporate_secp`, `audit_notice`, `property` |
| complexity | `simple`, `complex` |
| language | `en`, `roman_urdu` |
| tax_year | `TY2026`, `TY2027`, or empty when the question does not depend on a year |

Do not label the answer, the section, or a confidence score. Those belong to the eval set, not this classifier.

## How to choose a domain

Pick the domain a retrieval boost should prefer. One domain only. If two domains are real, choose the one the user needs a document from.

- `income_tax`: salary, freelancer, withholding, return filing, NTN for an individual, penalties under the Income Tax Ordinance, rates, filer status.
- `sales_tax`: sales tax registration, invoices, further tax, federal sales tax. Provincial sales tax (SRB, PRA, KPRA, BRA) is still `sales_tax`, and the question should be marked provincial in a note, not given a new domain.
- `customs`: import, export of goods, GD, customs duty, FBR customs. Export of services under section 154A is `income_tax`, not customs.
- `corporate_secp`: company incorporation, SECP returns, directors, shares. Tax on a company's profit stays `income_tax`.
- `audit_notice`: the user has a notice, an audit, a demand, or a deadline from FBR. If they only ask what a section means, use the tax domain, not `audit_notice`.
- `property`: buying, selling, or transferring immovable property, including sections 236C and 236K. Rental income of a person is `income_tax`.

Skip the row when the question is a greeting, a jailbreak, or not about Pakistan tax or SECP. Write `skip` in the note. Do not invent a domain for it.

## Complexity

`simple`: one rate, one section, or a yes or no that a calculator or a short citation can answer.

`complex`: more than one law, a notice with a deadline, a dispute, or a question that needs the user's facts before a number is safe. "How do I appeal?" is `complex`. "What is the filer rate on a bank deposit?" is `simple`.

## Checks before a row is accepted

1. The question has no raw CNIC, NTN, phone, or email.
2. The domain is one of the six values.
3. A second person can reach the same domain from these rules. If you and the second person disagree, keep the note and leave the domain blank for review. Do not average the two labels.
4. Roman Urdu and English questions with the same meaning get the same domain.

## Examples

| Question | Domain | Complexity |
|---|---|---|
| Salary 2,200,000 pe kitna tax hai TY2027? | income_tax | simple |
| Plot 6 crore ka filer aur non-filer withholding? | property | simple |
| Audit notice aya hai, 7 din mein jawab dena hai | audit_notice | complex |
| SECP par private company kaise register karein? | corporate_secp | simple |
| Import GD par customs duty kaun si schedule? | customs | simple |
| Sales tax invoice ke baghair supply? | sales_tax | simple |
| Hi, kaise ho? | skip | |
