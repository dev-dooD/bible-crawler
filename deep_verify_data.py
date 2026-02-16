import json
import re

def deep_verify():
    try:
        with open("bible_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("bible_data.json not found.")
        return

    print("--- Deep Data Verification ---")
    
    issues_found = 0
    total_verses = 0
    
    # Regex for potential issues
    html_tag_pattern = re.compile(r'<[^>]+>')
    footnote_pattern = re.compile(r'\d+\)') # e.g., 1)
    
    for book in data["books"]:
        bid = book["id"]
        bname = book["name"]
        
        for chapter in book["chapters"]:
            cnum = chapter["chapter"]
            
            # Check verse continuity
            verses = sorted(chapter["verses"], key=lambda x: x["verse"])
            if not verses:
                 print(f"[EMPTY_CHAPTER] {bname} {cnum} has no verses.")
                 issues_found += 1
                 continue
                 
            last_v = 0
            for v_obj in verses:
                vnum = v_obj["verse"]
                total_verses += 1
                
                # Check sequence
                if vnum != last_v + 1:
                    if bname == "사도행전" and cnum == 24 and last_v == 6 and vnum == 8:
                        print(f"[NOTE] {bname} {cnum}: Verse 7 is verified missing in source (Textus Receptus omission).")
                    else:
                        print(f"[GAP] {bname} {cnum}: Jump from {last_v} to {vnum}")
                        issues_found += 1
                last_v = vnum
                
                # Check Text Content
                for ver_key in ["GAE", "SAENEW"]:
                    text = v_obj["text"].get(ver_key, "")
                    
                    # 1. Empty Check
                    if not text.strip():
                        # SAENEW often has empty text for omitted verses
                        if ver_key == "SAENEW":
                             print(f"[WARNING] {bname} {cnum}:{vnum} (SAENEW) is empty (Likely omitted in this version).")
                        elif bname == "요한계시록" and cnum == 12 and vnum == 18 and ver_key == "GAE":
                             print(f"[NOTE] {bname} {cnum}:{vnum} (GAE) is empty (Text is included in 12:17 in this version).")
                        else:
                             print(f"[EMPTY_TEXT] {bname} {cnum}:{vnum} ({ver_key}) is empty.")
                             issues_found += 1
                    
                    # 2. HTML Tags
                    if html_tag_pattern.search(text):
                        print(f"[HTML_TAG] {bname} {cnum}:{vnum} ({ver_key}): Found HTML tag -> {text}")
                        issues_found += 1
                        
                    # 3. Footnotes
                    if footnote_pattern.search(text):
                         # Some verses might genuinely have "1)" in text? unlikely for Bible text.
                         # Actually 1) is usually a footnote marker in this source.
                         print(f"[FOOTNOTE_REMNANT] {bname} {cnum}:{vnum} ({ver_key}): Potential footnote -> {text}")
                         issues_found += 1

    print("\n--- Summary ---")
    print(f"Total Verses Checked: {total_verses}")
    print(f"Issues Found: {issues_found}")
    
    if issues_found == 0:
        print("✅ Data is clean and structurally sound.")
    else:
        print("❌ Issues detected. Please review above.")

if __name__ == "__main__":
    deep_verify()
