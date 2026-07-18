import re
import unicodedata
from dataclasses import dataclass
from datetime import date, time

import requests
from bs4 import BeautifulSoup


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
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def best_decoded_html(raw: bytes) -> str:
    candidates = []
    for encoding in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            value = raw.decode(encoding)
            text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
            score = len(re.findall(r"\d{1,2}\.\s*kosu\b", fold_text(text)))
            candidates.append((score, value))
        except UnicodeDecodeError:
            continue
    if not candidates:
        return raw.decode("utf-8", errors="replace")
    return max(candidates, key=lambda item: item[0])[1]


class TjkDailyProgramClient:
    base_url = "https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
    headers = {"User-Agent": "Mozilla/5.0 PegasusAI/0.1", "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

    def build_url(self, *, city: str, city_id: int, race_date: date) -> str:
        return requests.Request("GET", self.base_url, params={
            "Era": "today",
            "QueryParameter_Tarih": race_date.strftime("%d/%m/%Y"),
            "SehirAdi": city,
            "SehirId": city_id,
        }).prepare().url

    def fetch_and_parse(self, *, city: str, city_id: int, race_date: date) -> tuple[str, str, list[ParsedRace]]:
        url = self.build_url(city=city, city_id=city_id, race_date=race_date)
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TjkFetchError(f"TJK daily program could not be fetched: {exc}") from exc
        raw_html = best_decoded_html(response.content)
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
