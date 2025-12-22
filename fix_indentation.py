# fix_indentation.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken block has 12 spaces indentation
broken_block = 'except Exception as e:\n            import traceback\n            logger.error(traceback.format_exc())'
fixed_block = 'except Exception as e:'

if broken_block in content:
    content = content.replace(broken_block, fixed_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Reverted broken indentation")
else:
    print("WARNING: Broken block not found (maybe indentation matches differently?)")
    # Try with different indentation just in case
    broken_block_2 = 'except Exception as e:\n            import traceback'
    if broken_block_2 in content:
        print("Found partial block, fixing...")
        content = content.replace(broken_block, fixed_block)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
