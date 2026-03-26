import re


def parse_price_from_caption(caption: str) -> int | None:
    """
    Caption ichidan narxni ajratib oladi.
    Misollar:
        "savdo 100000 so'm" → 100000
        "savdo 100 000 so'm" → 100000
        "50 000 som"         → 50000
        "1 500 000"          → 1500000
        "200000"             → 200000
    """
    if not caption:
        return None

    caption = caption.lower().strip()

    # "savdo", "sotish", "olish" kabi kalit so'zlar bo'lsa yaxshi
    # Raqamlarni topish: 100 000, 100000, 1 500 000
    # Bo'shliqlar bilan ajratilgan raqamlar guruhini topamiz
    matches = re.findall(r'\d[\d\s]*\d|\d+', caption)

    if not matches:
        return None

    # Eng uzun raqamni tanlaymiz (narx odatda eng katta son)
    best = None
    for m in matches:
        cleaned = m.replace(' ', '').replace('\xa0', '')
        if cleaned.isdigit():
            val = int(cleaned)
            if val >= 1000 and (best is None or val > best):
                best = val

    return best
