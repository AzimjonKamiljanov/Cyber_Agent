"""Uzbek orthography normalizer and Cyrillic-to-Latin transliterator.

Ensures all speech-to-text outputs conform strictly to Latin script.
"""

from __future__ import annotations

import re

# Word-start or post-vowel special rules:
# Е/е at the beginning of a word or after a vowel is transcribed as "Ye" / "ye".
# Elsewhere it is "E" / "e".
VOWELS = set("аеёиоуэюяАЕЁИОУЭЮЯaeiouo'g'AEIOUO'G'")

CYRILLIC_TO_LATIN_PAIRS: list[tuple[str, str]] = [
    ("Ў", "Oʻ"),
    ("ў", "oʻ"),
    ("Ғ", "Gʻ"),
    ("ғ", "gʻ"),
    ("Ш", "Sh"),
    ("ш", "sh"),
    ("Ч", "Ch"),
    ("ч", "ch"),
    ("Ё", "Yo"),
    ("ё", "yo"),
    ("Ю", "Yu"),
    ("ю", "yu"),
    ("Я", "Ya"),
    ("я", "ya"),
    ("Ц", "Ts"),
    ("ц", "ts"),
    ("Щ", "Sh"),
    ("щ", "sh"),
    ("А", "A"),
    ("а", "a"),
    ("Б", "B"),
    ("б", "b"),
    ("В", "V"),
    ("в", "v"),
    ("Г", "G"),
    ("г", "g"),
    ("Д", "D"),
    ("д", "d"),
    ("Ж", "J"),
    ("ж", "j"),
    ("З", "Z"),
    ("з", "z"),
    ("И", "I"),
    ("и", "i"),
    ("Й", "Y"),
    ("й", "y"),
    ("К", "K"),
    ("к", "k"),
    ("Л", "L"),
    ("л", "l"),
    ("М", "M"),
    ("м", "m"),
    ("Н", "N"),
    ("н", "n"),
    ("О", "O"),
    ("о", "o"),
    ("П", "P"),
    ("п", "p"),
    ("Р", "R"),
    ("р", "r"),
    ("С", "S"),
    ("с", "s"),
    ("Т", "T"),
    ("т", "t"),
    ("У", "U"),
    ("у", "u"),
    ("Ф", "F"),
    ("ф", "f"),
    ("Х", "X"),
    ("х", "x"),
    ("Ҳ", "H"),
    ("ҳ", "h"),
    ("Қ", "Q"),
    ("қ", "q"),
    ("Э", "E"),
    ("э", "e"),
    ("ъ", "'"),
    ("Ъ", "'"),
    ("ь", ""),
    ("Ь", ""),
]


def cyrillic_to_latin(text: str) -> str:
    """Convert Uzbek Cyrillic text to standardized Latin script."""
    if not text:
        return ""

    result: list[str] = []
    length = len(text)

    i = 0
    while i < length:
        ch = text[i]

        # Handle 'е' and 'Е' depending on position (beginning of word or after vowel)
        if ch in ("Е", "е"):
            is_word_start = i == 0 or not text[i - 1].isalpha()
            prev_is_vowel = i > 0 and text[i - 1] in VOWELS
            if is_word_start or prev_is_vowel:
                result.append("Ye" if ch == "Е" else "ye")
            else:
                result.append("E" if ch == "Е" else "e")
            i += 1
            continue

        matched = False
        for cyr, lat in CYRILLIC_TO_LATIN_PAIRS:
            if text.startswith(cyr, i):
                result.append(lat)
                i += len(cyr)
                matched = True
                break

        if not matched:
            result.append(ch)
            i += 1

    normalized = "".join(result)
    # Standardize curly apostrophes or backticks to regular apostrophe
    normalized = normalized.replace("ʻ", "'").replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", normalized).strip()
