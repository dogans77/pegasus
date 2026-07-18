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


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold()).replace("Ä±", "i")
    return "".join(char for char in normalized if not unicodedata.combining(char))


class TjkDailyProgramClient:
    base_url = "https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
    headers = {
        "User-Agent": "Mozilla/5.0 PegasusAI/0.1",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }

    def build_url(self, *, city: str, city_id: int, race_date: date) -> str:
        return requests.Request(
            "GET",
            self.base_url,
            params={
                "Era": "today",
                "QueryParameter_Tarih": race_date.strftime("%d/%m/%Y"),
                "SehirAdi": city,
                "SehirId": city_id,
            },
        ).prepare().url

    def fetch_and_parse(self, *, city: str, city_id: int, race_date: date) -> tuple[str, str, list[ParsedRace]]:
        url = self.build_url(city=city, city_id=city_id, race_date=race_date)
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TjkFetchError(f"TJK daily program could not be fetched: {exc}") from exc

        raw_html = response.content.decode("utf-8", errors="replace")
        if raw_html.count("replacement") > 10:
            raw_html = response.content.decode("windows-1254", errors="replace")
        races = self._parse_races(raw_html)
        if not races:
            raise TjkParseError("TJK page was downloaded but no race rows could be identified")
        return url, raw_html, races

    @staticmethod
    def _parse_races(html: str) -> list[ParsedRace]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        folded = re.sub(r"\s+", " ", _fold(text))
        boundary = re.compile(r"(?P<number>\d{1,2})\.\s*kosu\b(?P<body>.*?)(?=\s+\d{1,2}\.\s*kosu\b|$)", re.DOTALL)
        parsed: list[ParsedRace] = []
        seen: set[int] = set()
        for match in boundary.finditer(folded):
            number = int(match.group("number"))
            if number in seen:
                continue
            body = match.group("body")
            time_match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", body)
            details = re.search(r"\b(\d{3,4})\s*(?:m|metre)?\s*(cim|kum|sentetik)\b", body)
            if details is None:
                details = re.search(r"\b(cim|kum|sentetik)\s*(\d{3,4})\b", body)
                if details is None:
                    continue
                surface, distance = details.group(1), int(details.group(2))
            else:
                distance, surface = int(details.group(1)), details.group(2)
            scheduled_time = None
            if time_match is not None:
                scheduled_time = time(int(time_match.group(1)), int(time_match.group(2)))
            class_text = body[: max(0, details.start())].strip(" -,:;") or None
            parsed.append(ParsedRace(number, scheduled_time, distance, surface.title(), class_text[:64] if class_text else None))
            seen.add(number)
        return sorted(parsed, key=lambda item: item.race_number)
