"""Labeled questions for the domain classifier.

Synthetic rows are slot-filled from the templates below. The human rows are a
separate held-out set and are never used for training. Scores for the two
sets are reported separately.
"""

import json
import random
from pathlib import Path

DOMAINS = (
    "income_tax",
    "sales_tax",
    "customs",
    "corporate_secp",
    "audit_notice",
    "property",
)
DATA_DIR = Path(__file__).resolve().parent / "data"

_ROLES = {
    "en": ("salaried person", "freelancer", "private company", "AOP"),
    "roman_urdu": ("salaried shakhs", "freelancer", "private company", "AOP"),
}
_AMOUNTS = ("600000", "1200000", "2500000", "8000000")
_YEARS = ("TY2026", "TY2027")
_CITIES = ("Karachi", "Lahore", "Islamabad")

# question, domain, complexity, language, tax_year
HUMAN: list[tuple[str, str, str, str, str]] = [
    ("What salary tax applies to Rs 1200000 in TY2027?", "income_tax", "simple", "en", "TY2027"),
    ("Is profit on a bank deposit withheld at the filer rate?", "income_tax", "simple", "en", ""),
    ("How does an individual file an income tax return on IRIS?", "income_tax", "simple", "en", ""),
    (
        "I have salary and freelance export receipts in TY2027. Which rules apply to each?",
        "income_tax",
        "complex",
        "en",
        "TY2027",
    ),
    (
        "The commissioner already amended the order under section 122. Can the return still be revised?",
        "income_tax",
        "complex",
        "en",
        "",
    ),
    (
        "What changed in the salary surcharge under section 4AB between TY2026 and TY2027?",
        "income_tax",
        "complex",
        "en",
        "",
    ),
    (
        "TY2027 mein Rs 1200000 salary pe kitna tax banta hai?",
        "income_tax",
        "simple",
        "roman_urdu",
        "TY2027",
    ),
    (
        "Bank deposit ke profit pe filer withholding kya hota hai?",
        "income_tax",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "IRIS par individual income tax return kaise file karein?",
        "income_tax",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Salary bhi hai aur freelance export bhi, TY2027 mein dono alag kaise nikalte hain?",
        "income_tax",
        "complex",
        "roman_urdu",
        "TY2027",
    ),
    (
        "Commissioner section 122 ke tehat order badal chuka hai. Return revise ho sakti hai?",
        "income_tax",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Section 4AB salary surcharge TY2026 aur TY2027 mein kya farq hai?",
        "income_tax",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Do I need a sales tax invoice for a taxable supply of goods?",
        "sales_tax",
        "simple",
        "en",
        "",
    ),
    ("How do I register for federal sales tax on goods?", "sales_tax", "simple", "en", ""),
    (
        "What is further tax when the buyer of goods is not a registered person?",
        "sales_tax",
        "simple",
        "en",
        "",
    ),
    (
        "We supply goods and services in Punjab. Which part is FBR and which is PRA?",
        "sales_tax",
        "complex",
        "en",
        "",
    ),
    (
        "A buyer in Sindh is unregistered and the supply is services. Is that FBR or SRB?",
        "sales_tax",
        "complex",
        "en",
        "",
    ),
    (
        "The invoice was issued without a serial number. Can the input be refused?",
        "sales_tax",
        "complex",
        "en",
        "",
    ),
    ("Goods ki supply pe sales tax invoice zaroori hai?", "sales_tax", "simple", "roman_urdu", ""),
    (
        "Goods ka federal sales tax registration kaise hota hai?",
        "sales_tax",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Buyer registered nahi to goods pe further tax kab lagta hai?",
        "sales_tax",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Punjab mein goods bhi hain aur services bhi. FBR aur PRA ka hissa alag kaise hai?",
        "sales_tax",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Sindh mein services hain aur buyer registered nahi. Yeh FBR hai ya SRB?",
        "sales_tax",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Invoice pe serial number nahi. Input tax rukk sakta hai?",
        "sales_tax",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Which schedule shows the customs duty on an import goods declaration?",
        "customs",
        "simple",
        "en",
        "",
    ),
    (
        "What papers does a goods declaration for imported goods need?",
        "customs",
        "simple",
        "en",
        "",
    ),
    (
        "Where is the customs tariff published for an imported machine?",
        "customs",
        "simple",
        "en",
        "",
    ),
    (
        "Customs enhanced the assessed value. How is the duty recomputed, and where do I object?",
        "customs",
        "complex",
        "en",
        "",
    ),
    (
        "Machinery was imported under a concession and the end use later changed. What is the exposure?",
        "customs",
        "complex",
        "en",
        "",
    ),
    (
        "Two import GDs were clubbed in one assessment. How do I separate the duty?",
        "customs",
        "complex",
        "en",
        "",
    ),
    (
        "Import GD par customs duty kis schedule mein dekhein?",
        "customs",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Imported goods ke goods declaration ke liye kaun se papers chahiye?",
        "customs",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Imported machine ka customs tariff kahan chhapta hai?",
        "customs",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Customs ne value barha di. Duty dobara kaise banti hai aur objection kahan den?",
        "customs",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Concession pe machinery import hui aur baad mein end use badal gaya. Ab kya exposure hai?",
        "customs",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Do import GDs ek assessment mein jor diye. Duty alag kaise karein?",
        "customs",
        "complex",
        "roman_urdu",
        "",
    ),
    ("How do I incorporate a private company with SECP?", "corporate_secp", "simple", "en", ""),
    (
        "When is the first SECP annual return due after incorporation?",
        "corporate_secp",
        "simple",
        "en",
        "",
    ),
    (
        "How does a single member company reserve a name with SECP?",
        "corporate_secp",
        "simple",
        "en",
        "",
    ),
    (
        "A director wants to transfer shares and change the registered office. Which SECP filings are separate?",
        "corporate_secp",
        "complex",
        "en",
        "",
    ),
    (
        "Can a single member company add a second shareholder without incorporating again?",
        "corporate_secp",
        "complex",
        "en",
        "",
    ),
    (
        "The company missed two SECP annual returns. What filings catch it up?",
        "corporate_secp",
        "complex",
        "en",
        "",
    ),
    (
        "SECP par private company kaise incorporate karein?",
        "corporate_secp",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Incorporation ke baad pehli SECP annual return kab hoti hai?",
        "corporate_secp",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Single member company SECP par naam kaise reserve kare?",
        "corporate_secp",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Director shares transfer bhi karna chahta hai aur registered office bhi badalna hai. SECP filings alag hain?",
        "corporate_secp",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Single member company mein doosra shareholder kaise aaye baghair nayi incorporation ke?",
        "corporate_secp",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Do SECP annual returns reh gayi hain. Kaun si filings se poori hoti hain?",
        "corporate_secp",
        "complex",
        "roman_urdu",
        "",
    ),
    ("What is a show cause notice under section 122(9)?", "audit_notice", "simple", "en", ""),
    (
        "The notice says reply within 7 days. How do I count the days left?",
        "audit_notice",
        "simple",
        "en",
        "",
    ),
    (
        "What records does a section 177 audit notice usually ask for?",
        "audit_notice",
        "simple",
        "en",
        "",
    ),
    (
        "An audit notice and a recovery notice arrived the same week. Which deadline comes first?",
        "audit_notice",
        "complex",
        "en",
        "",
    ),
    (
        "The demand is under section 182 and only 4 days are left. What should the reply include?",
        "audit_notice",
        "complex",
        "en",
        "",
    ),
    (
        "They selected us for audit and also asked for third-party confirmations. How do I sequence the reply?",
        "audit_notice",
        "complex",
        "en",
        "",
    ),
    (
        "Section 122(9) ka show cause notice kya maangta hai?",
        "audit_notice",
        "simple",
        "roman_urdu",
        "",
    ),
    ("Notice mein 7 din likhe hain. Din kaise ginen?", "audit_notice", "simple", "roman_urdu", ""),
    (
        "Section 177 ke audit notice mein aam tor par kaun se records mangte hain?",
        "audit_notice",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Audit notice aur recovery notice ek hi haftay mein aaye. Pehli deadline kaun si hai?",
        "audit_notice",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Section 182 ki demand hai aur 4 din baqi hain. Jawab mein kya hona chahiye?",
        "audit_notice",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Audit select hua aur third party confirmation bhi mangi. Jawab kis order mein dein?",
        "audit_notice",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "What is the filer withholding on a plot purchase of Rs 8000000 under section 236K?",
        "property",
        "simple",
        "en",
        "",
    ),
    (
        "What is the section 236C rate when a filer sells immovable property?",
        "property",
        "simple",
        "en",
        "",
    ),
    (
        "Does buying a built house use the same federal withholding section as buying a plot?",
        "property",
        "simple",
        "en",
        "",
    ),
    (
        "We are selling a plot to a non-filer. Who withholds, and does the holding period change the federal rate?",
        "property",
        "complex",
        "en",
        "",
    ),
    (
        "A plot is gifted to a child. Is section 236K still collected on the transfer?",
        "property",
        "complex",
        "en",
        "",
    ),
    (
        "One agreement covers two plots in different cities. Is the withholding computed once or twice?",
        "property",
        "complex",
        "en",
        "",
    ),
    (
        "Rs 8000000 ke plot ki khareed pe filer ka section 236K kitna hota hai?",
        "property",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Filer property farokht kare to section 236C ki rate kya hai?",
        "property",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Bani hui house ki khareed bhi plot jaisi federal withholding section mein aati hai?",
        "property",
        "simple",
        "roman_urdu",
        "",
    ),
    (
        "Plot non-filer ko bech rahe hain. Kaun withhold kare, aur holding period se federal rate badalti hai?",
        "property",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Plot bachay ko gift ho to transfer pe section 236K lagta hai?",
        "property",
        "complex",
        "roman_urdu",
        "",
    ),
    (
        "Ek agreement mein do shehron ke plots hain. Withholding ek dafa bane ya do dafa?",
        "property",
        "complex",
        "roman_urdu",
        "",
    ),
]

_TEMPLATES: dict[tuple[str, str, str], list[str]] = {
    ("income_tax", "simple", "en"): [
        "Salary tax on Rs {amount} for {year}",
        "Filer withholding on a bank deposit of Rs {amount}",
        "How to file the individual return for {year} on IRIS",
        "What does section {section} withhold from salary",
        "NTN registration for a salaried person in {city}",
        "Dividend withholding for a filer in {year}",
        "Is freelance export under section 154A income tax",
    ],
    ("income_tax", "complex", "en"): [
        "Salary plus freelance export in {year}: which computation applies to each",
        "Return revision after a section 122 amendment for {year}",
        "Section 4AB on salary in TY2026 compared with TY2027 for Rs {amount}",
        "A company profit and the owner's salary are both in {year}. Which return covers which",
        "Withholding was short on a {city} payroll of Rs {amount}. How is the default worked out",
    ],
    ("income_tax", "simple", "roman_urdu"): [
        "{year} mein Rs {amount} salary pe tax kitna hai",
        "Bank deposit Rs {amount} pe filer withholding kya hai",
        "{year} ki individual return IRIS par kaise file karein",
        "Section {section} salary se kya kaatta hai",
        "{city} mein salaried shakhs ka NTN kaise banta hai",
        "{year} mein filer ke dividend pe withholding kya hai",
        "Freelance export section 154A income tax hai ya nahi",
    ],
    ("income_tax", "complex", "roman_urdu"): [
        "{year} mein salary aur freelance export dono hain, alag hisaab kaise",
        "Section 122 amendment ke baad {year} ki return revise ho sakti hai",
        "Rs {amount} salary pe section 4AB TY2026 aur TY2027 mein farq",
        "Company ka profit aur owner ki salary {year} mein hain, return kaun si",
        "{city} ki payroll Rs {amount} pe withholding kam hui, default kaise nikle",
    ],
    ("sales_tax", "simple", "en"): [
        "Sales tax invoice for a goods supply of Rs {amount}",
        "Register for sales tax on goods in {city}",
        "Further tax on goods when the buyer is unregistered",
        "What is an annex for output tax on goods",
        "Sales tax registration threshold talk for a {city} trader",
    ],
    ("sales_tax", "complex", "en"): [
        "Goods and Punjab services from the same {city} shop. Split FBR and PRA",
        "Sindh services and an unregistered buyer. Is further tax federal or SRB",
        "Invoice for Rs {amount} has no serial. Can input tax be refused",
        "A {year} goods return and a services credit note. Which return takes which",
    ],
    ("sales_tax", "simple", "roman_urdu"): [
        "Rs {amount} ke goods pe sales tax invoice chahiye",
        "{city} mein goods ka sales tax registration kaise karein",
        "Buyer registered na ho to goods pe further tax",
        "Goods ke output tax ka annex kya hota hai",
        "{city} ke tajir ke liye sales tax registration ki baat",
    ],
    ("sales_tax", "complex", "roman_urdu"): [
        "{city} ki dukaan pe goods bhi hain aur Punjab services bhi. FBR aur PRA alag karein",
        "Sindh services hain aur buyer registered nahi. Further tax federal hai ya SRB",
        "Rs {amount} ki invoice pe serial nahi. Input ruk sakta hai",
        "{year} ki goods return aur services credit note alag kaise hon",
    ],
    ("customs", "simple", "en"): [
        "Customs duty schedule for an import GD of Rs {amount}",
        "Papers for a goods declaration at {city}",
        "Where to read the customs tariff for an imported machine",
        "What an import GD assessment slip shows",
    ],
    ("customs", "complex", "en"): [
        "Assessed value was raised on an import of Rs {amount}. Recompute the duty and the objection",
        "Concessionary import and a later change of end use in {city}",
        "Two import GDs were assessed together. Separate the duty",
        "A {year} rebate claim on exports of goods was rejected. What is reviewed",
    ],
    ("customs", "simple", "roman_urdu"): [
        "Rs {amount} ke import GD pe customs duty kis schedule mein hai",
        "{city} pe goods declaration ke papers kya hain",
        "Imported machine ka customs tariff kahan hai",
        "Import GD ke assessment slip pe kya hota hai",
    ],
    ("customs", "complex", "roman_urdu"): [
        "Rs {amount} ke import pe value barha di. Duty dobara aur objection",
        "{city} mein concession pe import ke baad end use badal gaya",
        "Do import GDs ek assessment mein hain. Duty alag karein",
        "{year} mein goods ke export rebate ko reject kiya. Review kya hai",
    ],
    ("corporate_secp", "simple", "en"): [
        "Incorporate a private company with SECP in {city}",
        "Reserve a company name with SECP",
        "First SECP annual return after incorporation",
        "SECP filing to appoint a director",
    ],
    ("corporate_secp", "complex", "en"): [
        "Transfer shares and change the registered office in {city}. Separate SECP filings",
        "Add a shareholder to a single member company without a new incorporation",
        "Two missed SECP annual returns. Which filings catch the company up",
        "A {city} company changed its objects and its directors in one month. Which forms",
    ],
    ("corporate_secp", "simple", "roman_urdu"): [
        "{city} mein SECP par private company incorporate karein",
        "SECP par company ka naam reserve karein",
        "Incorporation ke baad pehli SECP annual return",
        "SECP pe director appoint karne ki filing",
    ],
    ("corporate_secp", "complex", "roman_urdu"): [
        "{city} mein shares transfer aur registered office dono badalne hain. SECP filings alag",
        "Single member company mein shareholder barhana hai, nayi incorporation nahi",
        "Do SECP annual returns reh gayi hain. Kaun si filings poori karein",
        "{city} ki company ne objects aur directors ek mahine mein badle. Forms kaun se",
    ],
    ("audit_notice", "simple", "en"): [
        "What does a section 122(9) show cause notice ask",
        "Count the days on a notice that says reply in 7 days",
        "Records a section 177 audit notice usually lists",
        "A section 182 penalty notice of Rs {amount}",
    ],
    ("audit_notice", "complex", "en"): [
        "Audit notice and recovery notice in the same week. Which deadline first",
        "Section 182 demand of Rs {amount} with 4 days left. What the reply needs",
        "Audit selection plus third party confirmations. Sequence the reply",
        "A {city} notice gives two deadlines. Which response goes out first",
    ],
    ("audit_notice", "simple", "roman_urdu"): [
        "Section 122(9) ka show cause notice kya maangta hai",
        "Notice 7 din ka hai, din kaise ginen",
        "Section 177 ke audit notice mein kaun se records hote hain",
        "Section 182 ki Rs {amount} penalty notice",
    ],
    ("audit_notice", "complex", "roman_urdu"): [
        "Ek haftay mein audit notice aur recovery notice. Pehli deadline kaun si",
        "Section 182 ki Rs {amount} demand aur 4 din baqi. Jawab mein kya ho",
        "Audit selection aur third party confirmation. Jawab kis order mein",
        "{city} ke notice mein do deadlines hain. Pehle kaun sa jawab jaye",
    ],
    ("property", "simple", "en"): [
        "Filer section 236K on a plot purchase of Rs {amount}",
        "Section 236C when a filer sells immovable property for Rs {amount}",
        "Is a built house in {city} under the same federal withholding as a plot",
        "Non-filer withholding on a property purchase of Rs {amount}",
    ],
    ("property", "complex", "en"): [
        "Selling a plot of Rs {amount} to a non-filer. Who withholds, and does holding period change the federal rate",
        "Gift of a {city} plot to a child. Is section 236K collected",
        "One agreement, two plots. Is withholding once or twice",
        "A {year} sale and a later adjustment of the property value. Which withholding is revised",
    ],
    ("property", "simple", "roman_urdu"): [
        "Rs {amount} ke plot pe filer ka section 236K",
        "Rs {amount} ki property farokht pe filer ka section 236C",
        "{city} ki bani hui house bhi plot wali federal withholding mein hai",
        "Rs {amount} ki property khareed pe non-filer withholding",
    ],
    ("property", "complex", "roman_urdu"): [
        "Rs {amount} ka plot non-filer ko bechna hai. Kaun withhold kare aur holding period se federal rate badle",
        "{city} ka plot bachay ko gift ho to section 236K lage",
        "Ek agreement do plots. Withholding ek dafa ya do dafa",
        "{year} ki farokht ke baad property value adjust hui. Kaun si withholding revise ho",
    ],
}


def human_rows() -> list[dict[str, str]]:
    rows = []
    for question, domain, complexity, language, tax_year in HUMAN:
        rows.append(_row(question, domain, complexity, language, tax_year, "human", "human_test"))
    return rows


def synthetic_rows(seed: int = 20261014) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """1608 synthetic rows, stratified. About four fifths train, the rest a synthetic test."""
    blocked = {question.casefold() for question, *_rest in HUMAN}
    train: list[dict[str, str]] = []
    test: list[dict[str, str]] = []
    rng = random.Random(seed)
    for key, templates in _TEMPLATES.items():
        domain, complexity, language = key
        made: list[str] = []
        index = 0
        while len(made) < 67 and index < 4000:
            template = templates[index % len(templates)]
            amount = _AMOUNTS[index % len(_AMOUNTS)]
            year = _YEARS[(index // 4) % len(_YEARS)]
            city = _CITIES[(index // 8) % len(_CITIES)]
            role = _ROLES[language][(index // 24) % len(_ROLES[language])]
            question = template.format(
                amount=amount,
                year=year,
                city=city,
                section=("149", "151", "114", "116")[index % 4],
            )
            if language == "en":
                question = f"{question}. Asked for a {role} in {city} for {year}."
            else:
                question = f"{question}. Yeh {role} ke liye hai, {city}, {year}."
            index += 1
            if question.casefold() in blocked or question in made:
                continue
            made.append(question)
        rng.shuffle(made)
        for offset, question in enumerate(made):
            split = "synthetic_test" if offset < 14 else "train"
            row = _row(question, domain, complexity, language, "", "synthetic", split)
            (test if split == "synthetic_test" else train).append(row)
    return train, test


def write_datasets() -> dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train, synthetic_test = synthetic_rows()
    human = human_rows()
    _dump(DATA_DIR / "synthetic_train.jsonl", train)
    _dump(DATA_DIR / "synthetic_test.jsonl", synthetic_test)
    _dump(DATA_DIR / "human_test.jsonl", human)
    return {
        "train": len(train),
        "synthetic_test": len(synthetic_test),
        "human_test": len(human),
    }


def _row(
    question: str,
    domain: str,
    complexity: str,
    language: str,
    tax_year: str,
    provenance: str,
    split: str,
) -> dict[str, str]:
    return {
        "question": question,
        "domain": domain,
        "complexity": complexity,
        "language": language,
        "tax_year": tax_year,
        "provenance": provenance,
        "split": split,
    }


def _dump(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    print(write_datasets())
