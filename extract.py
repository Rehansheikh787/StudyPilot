import os
import sys
import re
import json
import pdfplumber
from dotenv import load_dotenv

from ai_provider import generate_structured, SyllabusList, SyllabusEntry

load_dotenv()

SYSTEM_PROMPT = (
    "You are a structured data extractor. You must return ONLY valid, clean JSON "
    "with no markdown wrapping or backticks, no chat prefix, suffix, or explanation.\n"
    "Return a JSON array matching this schema exactly:\n"
    "[\n"
    "  {\n"
    '    "subject": "string",\n'
    '    "unit": "string",\n'
    '    "chapters": ["string"],\n'
    '    "exam_date": "YYYY-MM-DD",\n'
    '    "weightage": "string"\n'
    "  }\n"
    "]"
)


def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from the given PDF file path using pdfplumber.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The syllabus file '{os.path.basename(pdf_path)}' was not found.")

    print(f"Reading '{pdf_path}' with pdfplumber...")
    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
            else:
                print(f"Warning: No text extracted from page {i}.", file=sys.stderr)

    return "\n".join(text_content)


def _local_heuristic_extraction(text_content: str) -> SyllabusList:
    """
    Deterministic, no-AI fallback used only if both Gemini and Groq are
    unavailable. Scans for lines that look like subject headers (short,
    title-cased or ALL-CAPS lines) and groups subsequent lines under them
    as chapters. Deliberately conservative — it's meant to keep the app
    usable, not to match AI-quality extraction. The UI flags results from
    this path as "degraded mode" so the user knows to double-check them.
    """
    lines = [l.strip() for l in text_content.splitlines() if l.strip()]
    entries = []
    current = None

    # Only genuine ALL-CAPS, letters-only-ish short lines count as a new
    # subject header (e.g. "PHYSICS", "CHEMISTRY"). Everything else —
    # including "Unit 1: Mechanics" style lines, which are title-case and
    # would otherwise be mistaken for a new header — is treated as a
    # chapter under the current subject.
    def looks_like_subject_header(line: str) -> bool:
        letters = [c for c in line if c.isalpha()]
        return (
            len(line) <= 30
            and len(letters) >= 3
            and line == line.upper()
            and not line[0].isdigit()
        )

    for line in lines:
        if looks_like_subject_header(line):
            if current:
                entries.append(current)
            current = SyllabusEntry(subject=line.title(), chapters=[])
        elif current is not None and len(line) > 3:
            current.chapters.append(line[:80])

    if current:
        entries.append(current)

    cleaned = []
    for e in entries:
        if e.chapters:
            e.chapters = e.chapters[:15]
            cleaned.append(e)

    if not cleaned:
        cleaned = [SyllabusEntry(
            subject="Unidentified Subject (edit me)",
            chapters=["Could not auto-detect chapters — please edit manually."],
            weightage="medium",
        )]

    return SyllabusList(entries=cleaned)


def extract_structured_syllabus(text_content: str):
    """
    Extracts structured syllabus data via Gemini -> Groq -> local heuristic
    fallback. Returns (list_of_dicts, provider_used).
    """
    def local_fallback():
        return _local_heuristic_extraction(text_content)

    user_prompt = f"Extract structured data from the following syllabus text:\n\n{text_content}"

    result, provider = generate_structured(
        prompt=user_prompt,
        schema=SyllabusList,
        system_prompt=SYSTEM_PROMPT,
        local_fallback_fn=local_fallback,
    )

    entries_as_dicts = [e.model_dump() for e in result.entries]
    return entries_as_dicts, provider


def clean_and_parse_json(raw_json_str):
    """
    Retained for backwards compatibility. New code should prefer
    extract_structured_syllabus(), which already returns validated,
    parsed data.
    """
    if isinstance(raw_json_str, list):
        return raw_json_str
    cleaned = raw_json_str.strip()
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    else:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("No JSON found in LLM response.")
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_filename = os.path.join(script_dir, "syllabus.pdf")

    try:
        syllabus_text = extract_text_from_pdf(pdf_filename)
        if not syllabus_text.strip():
            print("Error: Extracted syllabus text is empty.", file=sys.stderr)
            sys.exit(1)

        print(f"Extracted {len(syllabus_text)} characters of text from PDF.")

        structured_data, provider = extract_structured_syllabus(syllabus_text)
        print(f"Extraction provider used: {provider}")

        output_filename = "syllabus.json"
        output_path = os.path.join(script_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=2)
        print(f"\nExtraction Successful! Output saved to '{output_path}'")

        print("\nJSON Output:\n")
        print(json.dumps(structured_data, indent=2))
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
