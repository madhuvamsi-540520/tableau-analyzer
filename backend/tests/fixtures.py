"""Helpers to synthesize .twb / .twbx byte payloads for tests."""
from __future__ import annotations

import io
import zipfile


def make_twb(caption: str = "Sales") -> bytes:
    return (
        "<?xml version='1.0' encoding='utf-8' ?>\n\n"
        "<workbook version='2021.4'>\n"
        "  <datasources>\n"
        f"    <datasource caption='{caption}' name='federated.1'>\n"
        "      <connection class='excel-direct' />\n"
        "    </datasource>\n"
        "  </datasources>\n"
        "  <worksheets />\n"
        "</workbook>\n"
    ).encode("utf-8")


def make_twbx(with_csv: bool = True, with_extract: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("MyWorkbook.twb", make_twb())
        if with_csv:
            z.writestr("Data/orders.csv", "id,amount\n1,10\n2,20\n")
        if with_extract:
            z.writestr("Data/Extracts/data.hyper", b"\x00\x01fake-hyper-bytes")
    return buf.getvalue()


def make_twbx_no_twb() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("readme.txt", "no workbook here")
    return buf.getvalue()


def make_twbx_traversal() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("MyWorkbook.twb", make_twb())
        z.writestr("../evil.txt", "escape attempt")
    return buf.getvalue()
