"""Extract objects must be flagged so diagrams/lineage can exclude them."""
from __future__ import annotations

from app.parser import parse_workbook

# A relation literally named 'Extract' (the reported symptom) + a real table.
EXTRACT_NAME_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='DS' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='x.1'><connection class='excel-direct' filename='C:/d.xlsx'/></named-connection>
        </named-connections>
        <relation name='Extract' table='[Extract]' type='table'>
          <columns><column datatype='integer' name='id' ordinal='0'/></columns>
        </relation>
        <relation name='Orders' table='[Orders$]' type='table'>
          <columns><column datatype='integer' name='id' ordinal='0'/></columns>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""

# An extract-class (hyper) connection backing the table.
HYPER_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='DS' name='federated.2'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='h.1'><connection class='hyper' dbname='extract'/></named-connection>
        </named-connections>
        <relation connection='h.1' name='TableauData' table='[Extract].[TableauData]' type='table'>
          <columns><column datatype='integer' name='id' ordinal='0'/></columns>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""


def test_extract_named_table_flagged():
    wb = parse_workbook(EXTRACT_NAME_TWB.encode("utf-8"), "X")
    by = {t.name: t for t in wb.data_sources[0].tables}
    assert by["Extract"].is_extract is True
    assert by["Orders"].is_extract is False


def test_hyper_connection_table_flagged():
    wb = parse_workbook(HYPER_TWB.encode("utf-8"), "H")
    t = wb.data_sources[0].tables[0]
    assert t.is_extract is True


def test_real_workbook_has_no_extract_tables():
    # The Superstore-based sample is live (bundled .xls), so nothing is an extract.
    import pathlib
    p = pathlib.Path(__file__).resolve().parent / "fixtures" / "twb" / "All Visual Sample.twb"
    wb = parse_workbook(p.read_bytes(), "S")
    assert all(not t.is_extract for ds in wb.data_sources for t in ds.tables)
