
try:
    with open(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_run_log_3.txt", "r", encoding="utf-16") as f:
        for line in f:
            if "[Word Scan]" in line:
                pass # Skip word scan spam
            if "VISUAL STOP MATCH" in line or "FINAL CUT Y" in line:
                print(line.strip())
except Exception as e:
    print(f"Error: {e}")
