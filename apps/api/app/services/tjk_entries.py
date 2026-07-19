import re
from decimal import Decimal, InvalidOperation
from bs4 import BeautifulSoup


def _clean(value: str) -> str:
    return " ".join(value.split())


def _decimal(value: str):
    match = re.search(r"\d+(?:[.,]\d+)?", value or "")
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(",", "."))
    except InvalidOperation:
        return None


def _integer(value: str):
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def entry_candidates(html: str) -> list[dict]:
    """Extract official runner data from TJK daily-program tables.

    TJK tables follow a stable 18-column order: form, program number, horse,
    age, pedigree, weight, jockey, owner, trainer, start, HP, recent form,
    KGS, s20, best time, odds, AGF and workout.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    seen: set[tuple[int, int]] = set()

    for race_number, table in enumerate(soup.find_all("table"), start=1):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 18:
                continue

            program_number = _integer(_clean(cells[1].get_text(" ", strip=True)))
            if program_number is None:
                continue

            horse_cell = cells[2]
            horse_link = next((a for a in horse_cell.find_all("a") if _clean(a.get_text(" ", strip=True))), None)
            horse_name = _clean((horse_link or horse_cell).get_text(" ", strip=True))
            horse_name = re.sub(r"\s*\(\d{1,2}\)\s*$", "", horse_name)
            if len(horse_name) < 2:
                continue

            barrier_match = re.search(r"\((\d{1,2})\)", _clean((horse_link or horse_cell).get_text(" ", strip=True)))
            agf_match = re.search(r"%(\d+(?:[.,]\d+)?)", _clean(cells[16].get_text(" ", strip=True)))
            key = (race_number, program_number)
            if key in seen:
                continue
            seen.add(key)

            results.append(
                {
                    "race_number": race_number,
                    "program_number": program_number,
                    "barrier": int(barrier_match.group(1)) if barrier_match else None,
                    "horse_name": horse_name[:150],
                    "weight_kg": _decimal(_clean(cells[5].get_text(" ", strip=True))),
                    "jockey_name": _clean(cells[6].get_text(" ", strip=True))[:120] or None,
                    "trainer_name": _clean(cells[8].get_text(" ", strip=True))[:120] or None,
                    "handicap_rating": _integer(_clean(cells[10].get_text(" ", strip=True))),
                    "agf_percent": _decimal(agf_match.group(1)) if agf_match else None,
                }
            )

    return results