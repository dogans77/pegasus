import csv
import hashlib
import io
from datetime import date
import requests

class TjkCsvError(RuntimeError):
    pass

def build_url(city: str, race_date: date) -> str:
    filename = f"{race_date.strftime('%d.%m.%Y')}-{city}-GunlukYarisProgrami-TR.csv"
    return f"https://medya-cdn.tjk.org/raporftp/TJKPDF/{race_date.year}/{race_date.strftime('%Y-%m-%d')}/CSV/GunlukYarisProgrami/{filename}"

def fetch_csv(city: str, race_date: date) -> tuple[str, str, list[str], list[dict[str, str]], str]:
    url = build_url(city, race_date)
    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "PegasusAI/0.1"})
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TjkCsvError(str(exc)) from exc
    raw = response.content
    text = raw.decode("utf-8-sig", errors="replace")
    if text.count("ï¿½") > 5:
        text = raw.decode("cp1254", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,|\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    raw_rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    rows = [
        {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}
        for row in raw_rows
    ]
    headers = list(rows[0].keys()) if rows else []
    return url, hashlib.sha256(raw).hexdigest(), headers, rows, text
