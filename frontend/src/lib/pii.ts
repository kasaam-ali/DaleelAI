const CNIC = /\b\d{5}-?\d{7}-?\d\b/g
const PHONE = /(?<![A-Za-z0-9])(?:(?:\+92|0092)[\s-]?|0)3\d{2}[- ]?\d{7}\b/g
const EMAIL = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g
const IBAN = /\bPK\d{2}[A-Z]{4}\d{16}\b/gi
const NTN_LABELED =
  /\b(?:NTN(?:\s*No\.?)?|Registration\s*No\.?)\s*[:#-]?\s*(?:\d{7}-\d|\d{7,8})\b/gi
const NTN_HYPHEN = /\b\d{7}-\d\b/g
const ACCOUNT = /\b(?:account(?:\s*(?:no\.?|number))?|a\/c)\s*[:#-]?\s*\d{10,18}\b/gi
const NAME = /\b(?:Name|Taxpayer)\s*:\s*[^,\n]{2,80}/gi
const ADDRESS = /\bAddress\s*:\s*[^\n]{2,120}/gi

function apply(text: string, pattern: RegExp, placeholder: string): string {
  pattern.lastIndex = 0
  return text.replace(pattern, placeholder)
}

/** Replace personal numbers with placeholders. Rupee amounts without a label stay. */
export function redactPii(text: string): string {
  let out = text
  out = apply(out, EMAIL, "[EMAIL]")
  out = apply(out, IBAN, "[ACCOUNT]")
  out = apply(out, CNIC, "[CNIC]")
  out = apply(out, PHONE, "[PHONE]")
  out = apply(out, NTN_LABELED, "[NTN]")
  out = apply(out, NTN_HYPHEN, "[NTN]")
  out = apply(out, ACCOUNT, "[ACCOUNT]")
  out = apply(out, NAME, "[NAME]")
  out = apply(out, ADDRESS, "[ADDRESS]")
  return out
}
