import re
import unicodedata
from dataclasses import dataclass
from datetime import date, time
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from app.services.text_normalization import repair_text


class TjkFetchError(RuntimeError):
    pass


class TjkParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedRace:
    race_number: int
    scheduled_time: time | None
    distance_meters: int
    surface: str
    race_class: str | None


def fold_text(value: str) -> str:
    # Unicode decomposition does not convert Turkish dotless-i by itself.
    # Canonicalize it explicitly so Elazig and Diyarbakir map correctly.
    normalized = unicodedata.normalize("NFKD", value.casefold()).replace("\u0131", "i")
    return "".join(character for character in normalized if not unicodedata.combining(character))


def best_decoded_html(raw: bytes) -> str:
    candidates = []
    for encoding in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            value = repair_text(raw.decode(encoding))
            text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
            score = len(re.findall(r"\d{1,2}\.\s*kosu\b", fold_text(text)))
            candidates.append((score, value))
        except UnicodeDecodeError:
            continue
    if not candidates:
        return raw.decode("utf-8", errors="replace")
    return max(candidates, key=lambda item: item[0])[1]


class TjkDailyProgramClient:
    city_url = "https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
    listing_url = "https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    domestic_cities = {
        "istanbul": ("Istanbul", "\u0130stanbul"),
        "izmir": ("Izmir", "\u0130zmir"),
        "bursa": ("Bursa", "Bursa"),
        "adana": ("Adana", "Adana"),
        "ankara": ("Ankara", "Ankara"),
        "kocaeli": ("Kocaeli", "Kocaeli"),
        "diyarbakir": ("Diyarbakir", "Diyarbak\u0131r"),
        "elazig": ("Elazig", "Elaz\u0131\u011f"),
    }

    def _get(self, url: str) -> bytes:
        try:
            response = requests.get(url, headers=self.headers, timeout=45)
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise TjkFetchError(f"TJK daily program could not be fetched: {exc}") from exc

    def discover_city_pages(self, race_date: date) -> list[tuple[str, str, int]]:
        listing = requests.Request("GET", self.listing_url, params={
            "QueryParameter_Tarih": race_date.strftime("%d/%m/%Y"),
            "SehirAdi": "Bursa",
        }).prepare().url
        html = best_decoded_html(self._get(listing))
        discovered: list[tuple[str, str, int]] = []
        seen: set[str] = set()
        for anchor in BeautifulSoup(html, "html.parser").select("a[href]"):
            href = urljoin(listing, anchor.get("href", ""))
            if "/Sehir/GunlukYarisProgrami" not in href:
                continue
            query = parse_qs(urlparse(href).query)
            requested = query.get("SehirAdi", [""])[0]
            raw_id = query.get("SehirId", [""])[0]
            try:
                city_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            canonical = self.domestic_cities.get(fold_text(requested))
            if canonical is None or canonical[0] in seen:
                continue
            seen.add(canonical[0])
            discovered.append((canonical[0], canonical[1], city_id))
        if not discovered:
            raise TjkParseError("TJK listing did not expose any domestic city program links")
        return discovered

    def build_url(self, *, city: str, city_id: int, race_date: date) -> str:
        return requests.Request("GET", self.city_url, params={
            "Era": "today",
            "QueryParameter_Tarih": race_date.strftime("%d/%m/%Y"),
            "SehirAdi": city,
            "SehirId": city_id,
        }).prepare().url

    def fetch_and_parse(self, *, city: str, city_id: int, race_date: date) -> tuple[str, str, list[ParsedRace]]:
        url = self.build_url(city=city, city_id=city_id, race_date=race_date)
        raw_html = best_decoded_html(self._get(url))
        races = self._parse_races(raw_html)
        if not races:
            raise TjkParseError("TJK page was downloaded but no race rows could be identified")
        return url, raw_html, races

    @staticmethod
    def _parse_races(html: str) -> list[ParsedRace]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        folded = re.sub(r"\s+", " ", fold_text(text))
        boundary = re.compile(r"(?P<number>\d{1,2})\.\s*kosu\b(?P<body>.*?)(?=\s+\d{1,2}\.\s*kosu\b|$)", re.DOTALL)
        distance_pattern = re.compile(r"\b(?P<distance>\d{3,4})\s*(?:m(?:etre)?\.?\s*)?(?P<surface>cim|kum|sentetik)\b")
        parsed: list[ParsedRace] = []
        seen: set[int] = set()
        for match in boundary.finditer(folded):
            number = int(match.group("number"))
            if number in seen:
                continue
            body = match.group("body")
            details = distance_pattern.search(body)
            if details is None:
                continue
            time_match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", body)
            scheduled_time = time(int(time_match.group(1)), int(time_match.group(2))) if time_match else None
            class_text = body[:details.start()].strip(" -,:;") or None
            parsed.append(ParsedRace(
                race_number=number,
                scheduled_time=scheduled_time,
                distance_meters=int(details.group("distance")),
                surface=details.group("surface").title(),
                race_class=class_text[:64] if class_text else None,
            ))
            seen.add(number)
        return sorted(parsed, key=lambda item: item.race_number)