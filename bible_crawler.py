import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from books_metadata import BIBLE_BOOKS

BASE_URL = "https://www.bskorea.or.kr/bible/korbibReadpage.php"
OUTPUT_FILE = "bible_data.json"
ERROR_LOG_FILE = "error_log.txt"
DELAY_SECONDS = 0.5  # Polite delay

def clean_whitespace(text):
    """Refines text by removing extra whitespace."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def get_clean_text(element):
    """
    Recursively extracts text from an element, excluding unwanted tags
    like footnotes (a.comment), hidden divs (div.D2), and verse numbers (span.number).
    """
    if isinstance(element, str):
        return element
    
    # Skip unwanted tags
    if element.name == 'a' and 'comment' in element.get('class', []):
        return ""
    if element.name == 'div' and 'D2' in element.get('class', []):
        return ""
    if element.name == 'span' and 'number' in element.get('class', []):
        return ""
    # Skip embedded subtitles
    if element.name == 'font' and 'smallTitle' in element.get('class', []):
        return ""
    
    # Recursively get text from children
    text_parts = []
    if hasattr(element, 'contents'):
        for child in element.contents:
            text_parts.append(get_clean_text(child))
            
    return "".join(text_parts)

def parse_version_content(soup, container_id):
    """
    Parses a specific version container (e.g., tdBible1 for GAE)
    Returns a dict: { verse_num: {"text": "...", "subtitle": "..."} }
    """
    container = soup.find("li", id=container_id)
    if not container:
        return {}

    # Handle wrapped content (e.g., tdBible2 has a wrapper div)
    children = [c for c in container.contents if str(c).strip()]
    if len(children) == 1 and children[0].name == 'div':
        container = children[0]

    verses = {}
    current_subtitle = None

    # Use find_all to traverse the tree in order
    tags = container.find_all(['span', 'font', 'div']) 

    for element in tags:
        # Check for Subtitle
        if element.name == 'font' and 'smallTitle' in element.get('class', []):
            current_subtitle = clean_whitespace(element.get_text())
            continue
        
        # Check for Verse (usually in a span containing a .number span)
        if element.name == 'span':
            number_span = element.find("span", class_="number", recursive=False)
            
            if number_span:
                try:
                    v_num_text = number_span.get_text().strip()
                    
                    # Handle ranges like "18-19"
                    range_match = re.search(r'(\d+)-(\d+)', v_num_text)
                    if range_match:
                        start_v = int(range_match.group(1))
                        end_v = int(range_match.group(2))
                        v_nums = list(range(start_v, end_v + 1))
                    else:
                        v_nums = [int(re.search(r'\d+', v_num_text).group())]
                    
                    # Check for embedded subtitle INSIDE the verse span
                    embedded_subtitle_tag = element.find("font", class_="smallTitle")
                    if embedded_subtitle_tag:
                        # User wants this included as the subtitle for this verse within the data
                        embedded_subtitle_text = clean_whitespace(embedded_subtitle_tag.get_text())
                        # If we already encountered a subtitle before this verse, valid question which to prioritize.
                        # Usually embedded one is more specific to this verse context.
                        # We will use the embedded one if found.
                        current_subtitle = embedded_subtitle_text

                    # Extract cleaned text (get_clean_text will SKIP the subtitle tag from text body)
                    raw_text = get_clean_text(element)
                    final_text = clean_whitespace(raw_text)
                    
                    for i, v in enumerate(v_nums):
                        if i == 0:
                            # First verse in the range gets the full text
                            verses[v] = {
                                "text": final_text,
                                "subtitle": current_subtitle
                            }
                        else:
                            # Subsequent verses get a reference string
                            # The user requested: "(18절에 포함)"
                            ref_text = f"({v_nums[0]}절에 포함)"
                            verses[v] = {
                                "text": ref_text,
                                "subtitle": "" # Usually subtitle belongs to the start of the section
                            }
                    
                    current_subtitle = None
                    
                except Exception as e:
                    # print(f"Error parsing verse in {container_id}: {e}")
                    continue
                    
    return verses

def fetch_chapter_data(book_id, chapter):
    """
    Fetches and parses a single chapter.
    Returns list of verse objects.
    """
    params = {
        "version": "GAE",
        "book": book_id,
        "chap": chapter,
        "cVersion": "SAENEW^" 
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parse GAE (Version 1)
        gae_data = parse_version_content(soup, "tdBible1")
        
        # Parse SAENEW (Version 2)
        saenew_data = parse_version_content(soup, "tdBible2")
        
        # Merge Data
        chapter_verses = []
        
        # Get all unique verse numbers
        all_verses = sorted(set(gae_data.keys()) | set(saenew_data.keys()))
        
        for v_num in all_verses:
            gae_entry = gae_data.get(v_num, {})
            saenew_entry = saenew_data.get(v_num, {})
            
            verse_obj = {
                "verse": v_num,
                "text": {
                    "GAE": gae_entry.get("text", ""),
                    "SAENEW": saenew_entry.get("text", "")
                }
            }
            
            # Store subtitles per version if present
            sub_gae = gae_entry.get("subtitle")
            sub_saenew = saenew_entry.get("subtitle")
            
            if sub_gae or sub_saenew:
                verse_obj["subtitle"] = {
                    "GAE": sub_gae if sub_gae else "",
                    "SAENEW": sub_saenew if sub_saenew else ""
                }
                
            chapter_verses.append(verse_obj)
            
        return chapter_verses

    except requests.RequestException as e:
        print(f"Error fetching {book_id} Chapter {chapter}: {e}")
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(f"{book_id} {chapter}: {e}\n")
        return None

def load_existing_data():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Existing JSON is corrupt. Starting fresh.")
    return {
        "metadata": {
            "source": BASE_URL,
            "versions": {"GAE": "개역개정", "SAENEW": "새번역"},
            "crawled_date": time.strftime("%Y-%m-%d")
        },
        "books": []
    }

def save_data(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Starting Bible Crawler...")
    print(f"Output will be saved to {OUTPUT_FILE}")
    
    full_bible_data = load_existing_data()
    
    # Create a lookup for existing books and chapters to avoid re-crawling
    existing_books = {b["id"]: b for b in full_bible_data["books"]}
    
    # Progress tracking
    total_books = len(BIBLE_BOOKS)
    
    for i, book_meta in enumerate(BIBLE_BOOKS):
        book_id = book_meta["id"]
        book_name = book_meta["name"]
        total_chapters = book_meta["chapters"]
        
        # Check if book exists in data
        if book_id not in existing_books:
            book_data = {
                "id": book_id,
                "name": book_name,
                "chapters": []
            }
            full_bible_data["books"].append(book_data)
            existing_books[book_id] = book_data # Update lookup
        else:
            book_data = existing_books[book_id]
            
        existing_chapters = {c["chapter"] for c in book_data["chapters"]}
        
        print(f"[{i+1}/{total_books}] Processing {book_name} ({book_id}) - {total_chapters} Chapters")
        
        for chap in range(1, total_chapters + 1):
            if chap in existing_chapters:
                # print(f"  Skipping Chapter {chap} (Already exists)", end="\r")
                continue

            # print(f"  Fetching Chapter {chap}...", end="\r")
            try:
                verses_list = fetch_chapter_data(book_id, chap)
                if verses_list:
                    book_data["chapters"].append({
                        "chapter": chap,
                        "verses": verses_list
                    })
                    # Save after every chapter to ensure resume capability
                    save_data(full_bible_data)
                else:
                    print(f"\n  Failed to fetch {book_name} Chapter {chap}")
                
                time.sleep(DELAY_SECONDS)
                
            except Exception as e:
                 print(f"\n  Exception processing {book_name} Chapter {chap}: {e}")

    print("\nCrawling Complete.")

if __name__ == "__main__":
    main()
