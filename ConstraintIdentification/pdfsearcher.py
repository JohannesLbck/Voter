#!/usr/bin/env python3
import sys
import pdfplumber
import re
import textwrap
import csv

TIME_KEYWORDS = [
    # Basic time units
    "seconds",
    "minute", "minutes",
    "hour", "hours",
    "day", "days",
    "week", "weeks",
    "month", "months",
    "year", "years",

    # special terms in the document
    " date ", " expiry ",

    # Relative/temporal terms
    "period",
    "time limit",
    "no later than",
    "not more than",
    "as soon as",
    "every",
]

def extract(path: str):
    """Extracts rules from a blood guide style PDF file."""
    try:
        with pdfplumber.open(path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        # Clean up line breaks and hyphens
        full_text = re.sub(r'-\n', '', full_text)
        full_text = re.sub(r'\n+', ' ', full_text)

        pattern = re.compile(
            r'(\d+(?:\.\d+)*\.)\s*(.*?)(?=\s*\d+(?:\.\d+)*\.|\Z)',
            re.DOTALL
        )

        matches = [(num.strip(), body.strip()) for num, body in pattern.findall(full_text)]
        print(f'There are a total of {len(matches)} Rules in the Document')
    except Exception as e:
        print(f"Error reading {path}: {e}")

    return matches 

def match(rules):
    """Matches if a rule contains time-related keywords to identify temporal constraints."""
    matched_rules = []

    for rule_num, text in rules:
        # Check case-insensitive presence of any keyword
        if any(re.search(rf'\b{re.escape(kw)}\b', text, re.IGNORECASE) for kw in TIME_KEYWORDS):
            matched_rules.append((rule_num, text))

    return matched_rules

def main():
    if len(sys.argv) < 2:
        print("Usage: ./check_pdfs.py file1.pdf [file2.pdf ...]")
        sys.exit(1)

    for pdf_file in sys.argv[1:]:
        rules = extract(pdf_file)
        matched_rules = match(rules)

        if matched_rules:
            with open('output.csv', 'w') as f:
                writer = csv.writer(f)
                writer.writerows(matched_rules)
            print("\n=== 🕒 Matched Temporal Rules ===\n")
            for i, (num, text) in enumerate(matched_rules, start=1):
                print(f"{i:02d}. Rule {num}")
                print(f"    {text[0:900]}\n")
        else:
            print("No time-related rules found.")

if __name__ == "__main__":
    main()

