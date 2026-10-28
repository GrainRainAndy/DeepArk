"""Narrow output guard for the observed image-selection draft leak, not an English filter."""
import re

def has_draft_leak(text):
    if not re.search(r'\bkeep\s+(?:it\s+)?text\s+only\b',text,re.I):return False
    signals=[r'\bnot\s+fitting\b',r'\balready\s+used\b.{0,60}\brecently\b',r'\bmaybe\s+no\s+image\b']
    return sum(bool(re.search(pattern,text,re.I)) for pattern in signals)>=2
