"""Reproduce this course's text-only token evidence; no model/API call."""
from pathlib import Path
import json, importlib.metadata
import tiktoken
encoding = tiktoken.get_encoding("cl100k_base")
examples = []
for text in ["Hello world!", "人工智能很有趣", "unhappiness"]:
    ids = encoding.encode(text)
    examples.append({"text": text, "ids": ids, "count": len(ids), "tokenBytesHex": [encoding.decode_single_token_bytes(i).hex() for i in ids], "roundTrip": encoding.decode(ids) == text})
result = {"encoding": encoding.name, "libraryVersion": importlib.metadata.version("tiktoken"), "model": None, "examples": examples}
Path(__file__).with_name("tokenizer-evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Measured 3 text examples using", encoding.name)
