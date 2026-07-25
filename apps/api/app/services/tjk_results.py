import re
from dataclasses import dataclass
from datetime import date

import requests
from bs4 import BeautifulSoup

from app.services.tjk_daily_program import TjkFetchError, best_decoded_html


@dataclass(frozen=True)
class ParsedResultRace:
    race_number: int
    finisher_names: list[str]
    official_time: str | None


class TjkResultsClient:
    base_url = "https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisSonuclari"
    headers = {"User-Agent": "Mozilla/5.0 PegasusAI/0.1", "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

    def build_url(self, *, city: str, city_id: int, race_date: date) -> str:
        return requests.Request("GET", self.base_url, params={
            "Era": "today",
            "QueryParameter_Tarih": race_date.strftime("%d/%m/%Y"),
            "SehirAdi": city,
            "SehirId": city_id,
        }).prepare().url

    def fetch_and_parse(self, *, city: str, city_id: int, race_date: date) -> tuple[str, str, list[ParsedResultRace]]:
        url = self.build_url(city=city, city_id=city_id, race_date=race_date)
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TjkFetchError(f"TJK results could not be fetched: {exc}") from exc
        raw_html = best_decoded_html(response.content)
        return url, raw_html, self._parse_result_tables(raw_html)

    @classmethod
    def _parse_result_tables(cls, html: str) -> list[ParsedResultRace]:
        soup = BeautifulSoup(html, "html.parser")
        parsed: list[ParsedResultRace] = []
        for table in soup.find_all("table"):
            finisher_names: list[str] = []
            official_time = None
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"], recursive=False)
                if len(cells) < 14:
                    continue
                # The TJK results table places finish position in the numeric
                # column that was previously interpreted as a horse number.
                # Preserve table order, then map the horse name to the official
                # program card in the importer.
                horse_name = cells[2].get_text(" ", strip=True)
                if len(horse_name) < 2:
                    continue
                if horse_name not in finisher_names:
                    finisher_names.append(horse_name)
                if official_time is None:
                    value = cells[9].get_text(" ", strip=True)
                    time_match = re.search(r"\b\d{1,2}\.\d{2}\.\d{2}\b", value)
                    official_time = time_match.group(0) if time_match else None
            if len(finisher_names) >= 2:
                parsed.append(ParsedResultRace(
                    race_number=len(parsed) + 1,
                    finisher_names=finisher_names,
                    official_time=official_time,
                ))
        return parsed