from pathlib import Path
import re
prompt = Path(r'C:\Users\MystralMJ\Documents\ProjetTutore\deskOne\src\prompts.py').read_text(
    encoding='utf-8')
m = re.search(r'SYSTEM_PROMPT = """(.*)"""', prompt, re.S)
text = m.group(1) if m else prompt
print('prompt_chars=', len(text))
print('prompt_words=', len(text.split()))
print('prompt_lines=', len(text.splitlines()))
print('max_tokens=2000')
