import os
import sys
import json
import re
import pdfplumber
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

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

def extract_structured_syllabus(text_content):
    """
    Sends the syllabus text to Groq API using Llama 3 and returns structured JSON.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please create a '.env' file with your key.")
        
    client = Groq(api_key=api_key)
    
    # Default model: llama-3.3-70b-versatile
    model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(f"Sending text to Groq LLM (Model: {model_name})...")
    
    system_prompt = (
        "You are a structured data extractor. You must return ONLY valid, clean JSON with no markdown wrapping or backticks. "
        "Do not include any chat prefix, suffix, explanation, or conversational text. "
        "The schema contract must match this format perfectly:\n"
        "[\n"
        "  {\n"
        "    \"subject\": \"string\",\n"
        "    \"unit\": \"string\",\n"
        "    \"chapters\": [\"string\"],\n"
        "    \"exam_date\": \"YYYY-MM-DD\",\n"
        "    \"weightage\": \"string\"\n"
        "  }\n"
        "]"
    )
    
    user_prompt = f"Extract structured data from the following syllabus text:\n\n{text_content}"
    
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            model=model_name,
            temperature=0.1,  # Strict temperature for deterministic extraction
            max_tokens=3000,
        )
        
        raw_output = response.choices[0].message.content.strip()
        return raw_output
        
    except Exception as e:
        print(f"Error communicating with Groq API: {e}", file=sys.stderr)
        raise RuntimeError(f"Error communicating with Groq API: {e}")

def clean_and_parse_json(raw_json_str):
    """
    Cleans markdown formatting/backticks if present, and parses the JSON to ensure it is valid.
    Uses regex to extract the JSON array or object if conversational wrappers exist.
    """
    cleaned = raw_json_str.strip()
    
    # Try to find JSON content enclosed in markdown code blocks
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If no markdown block is found, locate the first [ or { and last ] or }
        start_list = cleaned.find('[')
        start_obj = cleaned.find('{')
        
        # Determine which comes first (if both exist)
        if start_list != -1 and (start_obj == -1 or start_list < start_obj):
            start = start_list
            end = cleaned.rfind(']')
        elif start_obj != -1:
            start = start_obj
            end = cleaned.rfind('}')
        else:
            start = -1
            end = -1
            
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end+1]
            
    try:
        parsed_json = json.loads(cleaned)
        return parsed_json
    except json.JSONDecodeError as e:
        print("Error: The output from the LLM could not be parsed as valid JSON.", file=sys.stderr)
        print(f"Parsing error: {e}", file=sys.stderr)
        print(f"Raw output was:\n{raw_json_str}", file=sys.stderr)
        raise ValueError(f"The LLM response could not be parsed as valid JSON: {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_filename = os.path.join(script_dir, "syllabus.pdf")
    
    try:
        # 1. Extract text from syllabus.pdf
        syllabus_text = extract_text_from_pdf(pdf_filename)
        if not syllabus_text.strip():
            print("Error: Extracted syllabus text is empty.", file=sys.stderr)
            sys.exit(1)
            
        print(f"Extracted {len(syllabus_text)} characters of text from PDF.")
        
        # 2. Extract structured data using Groq Llama 3
        raw_json_response = extract_structured_syllabus(syllabus_text)
        
        # 3. Clean and validate JSON structure
        structured_data = clean_and_parse_json(raw_json_response)
        
        # 4. Save the final structured JSON to a file
        output_filename = "syllabus.json"
        output_path = os.path.join(script_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=2)
        print(f"\nExtraction Successful! Output saved to '{output_path}'")
        
        # 5. Print the final structured JSON to console
        print("\nJSON Output:\n")
        print(json.dumps(structured_data, indent=2))
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
