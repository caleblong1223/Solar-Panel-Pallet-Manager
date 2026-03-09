from __future__ import annotations

from app.services.simulator_parser import parse_simulator_file


def test_parser_handles_sunsim_headers_with_units_and_symbols() -> None:
    csv_content = (
        "Serial Number,Date/Time,Pmax(W),Voc(V),Isc(A),Vmp(V),Imp(A),Fill Factor,Result\n"
        "CRS25WT3609001,2026-01-22 18:25:34,451.2,49.321,11.234,40.111,10.456,0.812,PASS\n"
    )

    result = parse_simulator_file("sample.csv", csv_content.encode("utf-8"))

    assert result.rows_total == 1
    assert len(result.accepted_rows) == 1
    assert len(result.rejected_rows) == 0

    row = result.accepted_rows[0]
    assert row.serial == "CRS25WT3609001"
    assert row.test_timestamp is not None
    assert row.watts == 451.2
    assert row.voc == 49.321
    assert row.isc == 11.234
    assert row.vmp == 40.111
    assert row.imp == 10.456
    assert row.ff == 0.812
    assert row.result == "PASS"


def test_parser_extracts_numeric_values_when_units_are_present() -> None:
    csv_content = (
        "Serial Number,Date/Time,Pmax [W],Voc (V),Isc (A),Vmp(V),Imp(A),FF(%),Result\n"
        "CRS25WT3609002,2026-01-22 18:30:00,451.2W,49.321V,11.234A,40.111V,10.456A,81.2%,PASS\n"
    )

    result = parse_simulator_file("sample_units.csv", csv_content.encode("utf-8"))

    assert result.rows_total == 1
    assert len(result.accepted_rows) == 1
    row = result.accepted_rows[0]
    assert row.watts == 451.2
    assert row.voc == 49.321
    assert row.isc == 11.234
    assert row.vmp == 40.111
    assert row.imp == 10.456
    assert row.ff == 81.2


def test_parser_handles_required_sunsim_columns_with_separate_date_and_time() -> None:
    csv_content = (
        "SerialNo,Date,Time,Pm,Isc,Voc(V),Ipm,Vpm(V)\n"
        "CRS25WT6009501,03/09/2026,12:46:07 PM,325.7303467,10.11288738,41.1230812,9.511628151,34.2454910\n"
    )

    result = parse_simulator_file("required_cols.csv", csv_content.encode("utf-8"))

    assert result.rows_total == 1
    assert len(result.accepted_rows) == 1
    row = result.accepted_rows[0]
    assert row.serial == "CRS25WT6009501"
    assert row.test_timestamp is not None
    assert row.watts == 325.7303467
    assert row.isc == 10.11288738
    assert row.voc == 41.1230812
    assert row.imp == 9.511628151
    assert row.vmp == 34.2454910
