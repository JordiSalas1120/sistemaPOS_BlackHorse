"""
Adapter de exportación a Excel usando pandas + openpyxl.
Recibe una lista de dicts (columnas flexibles) y devuelve bytes .xlsx.
"""
import io

import pandas as pd

from src.application.ports.exporter_port import ExporterPort


class ExcelExporter(ExporterPort):
    def export(self, data: list[dict], filename: str = "export") -> bytes:
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")
            # Autoajustar anchos de columna
            worksheet = writer.sheets["Datos"]
            for col_idx, col in enumerate(df.columns, start=1):
                max_len = max(
                    len(str(col)),
                    df[col].astype(str).str.len().max() if not df.empty else 0,
                )
                worksheet.column_dimensions[
                    worksheet.cell(1, col_idx).column_letter
                ].width = min(max_len + 4, 60)
        return buffer.getvalue()
