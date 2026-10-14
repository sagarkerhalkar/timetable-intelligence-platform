from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, time
from typing import Any, Iterable

URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]+")

_DEVANAGARI_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ऋ": "ri", "ॠ": "ri", "ऌ": "li", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
}
_DEVANAGARI_VOWEL_SIGNS = {
    "ा": "aa", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "ॄ": "ri",
    "ॅ": "e", "े": "e", "ै": "ai", "ॉ": "o", "ो": "o", "ौ": "au", "ॆ": "e", "ॊ": "o",
}
_DEVANAGARI_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f", "य़": "y",
}
_DEVANAGARI_MARKS = {"ं": "n", "ँ": "n", "ः": "h", "ऽ": ""}
_DEVANAGARI_HALANT = "्"
_DEVANAGARI_NUKTA = "़"


def stable_hash(*parts: object, length: int = 24) -> str:
    encoded = "|".join(normalize_text(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).replace("\u00a0", " ").split()).strip()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def find_urls(value: object) -> list[str]:
    return [match.rstrip(".,;)") for match in URL_RE.findall(normalize_text(value))]


def first_non_empty(values: Iterable[object]) -> str | None:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return None


def devanagari_to_latin(value: object) -> str:
    """Return a simple search-oriented Roman spelling for Hindi/Sanskrit text.

    This is intentionally not a scholarly transliteration. It creates familiar
    spellings such as ``कबीर -> kabir``, ``हिंदी -> hindi`` and
    ``संस्कृत -> sanskrit`` so a normal English-keyboard query can find the
    original Devanagari source text without an online translation service.
    """

    text = normalize_text(value)
    if not DEVANAGARI_RE.search(text):
        return text

    def transliterate_word(match: re.Match[str]) -> str:
        word = match.group(0)
        output: list[str] = []
        index = 0
        while index < len(word):
            char = word[index]
            if char in _DEVANAGARI_CONSONANTS:
                output.append(_DEVANAGARI_CONSONANTS[char])
                next_char = word[index + 1] if index + 1 < len(word) else ""
                # A nukta may follow a consonant; it does not change the search
                # spelling for our practical matching purposes.
                if next_char == _DEVANAGARI_NUKTA:
                    index += 1
                    next_char = word[index + 1] if index + 1 < len(word) else ""
                if next_char in _DEVANAGARI_VOWEL_SIGNS:
                    output.append(_DEVANAGARI_VOWEL_SIGNS[next_char])
                    index += 1
                elif next_char == _DEVANAGARI_HALANT:
                    index += 1
                else:
                    output.append("a")
            elif char in _DEVANAGARI_VOWELS:
                output.append(_DEVANAGARI_VOWELS[char])
            elif char in _DEVANAGARI_VOWEL_SIGNS:
                output.append(_DEVANAGARI_VOWEL_SIGNS[char])
            elif char in _DEVANAGARI_MARKS:
                output.append(_DEVANAGARI_MARKS[char])
            elif char in {_DEVANAGARI_HALANT, _DEVANAGARI_NUKTA}:
                pass
            elif char.isdigit():
                output.append(char)
            index += 1
        roman = "".join(output)
        # Hindi/Sanskrit words normally suppress the final inherent schwa in
        # everyday Roman spelling: कबीर -> kabir, भारत -> bharat.
        if len(roman) > 2 and roman.endswith("a"):
            roman = roman[:-1]
        return roman

    return DEVANAGARI_RE.sub(transliterate_word, text)


def normalize_search_text(value: object) -> str:
    """Normalize search text and append a Roman form of Devanagari content."""

    original = unicodedata.normalize("NFKC", normalize_text(value)).casefold()
    original = original.replace("&", " and ")
    original = re.sub(r"[\u200c\u200d]", "", original)
    roman = unicodedata.normalize("NFKC", devanagari_to_latin(original)).casefold()
    # Strip accents only from the Roman form. Devanagari vowel signs are also
    # combining marks, so removing marks from the full string would damage the
    # original Hindi/Sanskrit word.
    roman = "".join(
        char for char in unicodedata.normalize("NFKD", roman)
        if not unicodedata.combining(char)
    )
    combined = f"{original} {roman}" if roman != original else original
    return " ".join(
        "".join(
            char if (char.isalnum() or "\u0900" <= char <= "\u097f") else " "
            for char in combined
        ).split()
    )
