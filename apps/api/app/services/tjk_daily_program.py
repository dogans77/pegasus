import re
from dataclasses import dataclass
from datetime import date, time

import requests
from bs4 import BeautifulSoup


class TjkFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedRace:
    race_number: int
    scheduled_time: time | None
    distance_meters: int
    surface: str
    race_class: str | None


class TjkDailyProgramClient:
    base_url = "https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
    headers = {"User-Agent": "PegasusAI/0.1 (data import; contact: admin@localhost)"}

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

    def fetch_and_parse(self, *, city: str, city_id: int, race_date: date) -> tuple[str, list[ParsedRace]]:
        url = self.build_url(city=city, city_id=city_id, race_date=race_date)
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TjkFetchError(f"TJK daily program could not be fetched: {exc}") from exc

        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
        return url, self._parse_races(text)

    @staticmethod
    def _parse_races(text: str) -> list[ParsedRace]:
        # TJK's rendered page repeats navigation links. Keeping only the first
        # occurrence of each race number avoids duplicate program rows.
        pattern = re.compile(r"(\d{1,2})\.\s*Koşu\s*(\d{1,2}[.:]\d{2})", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        parsed: list[ParsedRace] = []
        seen: set[int] = set()
        for index, match in enumerate(matches):
            number = int(match.group(1))
            if number in seen:
                continue
            seen.add(number)
            chunk_end = matches[index + 1].start() if index + 1 < len(matches) else match.end() + 600
            chunk = text[match.end():chunk_end]
            details = re.search(r"(.{0,180}?)(\d{3,4})\s+(Çim|Kum|Sentetik)", chunk, re.IGNORECASE)
            if not details:
                continue
            hour, minute = re.split(r"[.:]", match.group(2))
            parsed.append(
                ParsedRace(
                    race_number=number,
                    scheduled_time=time(int(hour), int(minute)),
                    distance_meters=int(details.group(2)),
                    surface=details.group(3).title(),
                    race_class=details.group(1).strip(" ,:-") or None,
                )
            )
        return sorted(parsed, key=lambda item: item.race_number)
