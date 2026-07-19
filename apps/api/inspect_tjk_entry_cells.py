import json
from sqlalchemy import select
from bs4 import BeautifulSoup
from app.core.database import SessionLocal
from app.models.source_document import SourceDocument


def clean(value):
    return " ".join(value.split())


output = []
with SessionLocal() as db:
    docs = list(
        db.scalars(
            select(SourceDocument).where(
                SourceDocument.document_type == "daily_program_html"
            )
        )
    )
    for doc in docs:
        soup = BeautifulSoup(doc.content, "html.parser")
        table_data = []
        for table_index, table in enumerate(soup.find_all("table"), start=1):
            rows = []
            for row in table.find_all("tr")[:15]:
                direct_cells = row.find_all(["td", "th"], recursive=False)
                all_cells = row.find_all(["td", "th"])
                rows.append(
                    {
                        "row_text": clean(row.get_text(" ", strip=True))[:500],
                        "direct_cell_count": len(direct_cells),
                        "all_cell_count": len(all_cells),
                        "direct_cells": [
                            {"tag": cell.name, "text": clean(cell.get_text(" ", strip=True))[:250]}
                            for cell in direct_cells
                        ],
                        "first_anchors": [
                            clean(anchor.get_text(" ", strip=True))[:150]
                            for anchor in row.find_all("a")[:6]
                        ],
                    }
                )
            table_data.append({"table_number": table_index, "rows": rows})
        output.append({"city": doc.city, "tables": table_data})

with open("tjk-entry-cell-structure.json", "w", encoding="utf-8") as handle:
    json.dump(output, handle, ensure_ascii=False, indent=2)
print("Saved TJK cell structure to tjk-entry-cell-structure.json")