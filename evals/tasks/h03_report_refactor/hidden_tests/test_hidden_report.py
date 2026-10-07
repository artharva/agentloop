import report


def test_reports_use_format_row(monkeypatch):
    calls = []
    original = report.format_row

    def spy(values, widths):
        calls.append(list(values))
        return original(values, widths)

    monkeypatch.setattr(report, "format_row", spy)
    report.sales_report([("A", 1, 1.0)])
    report.inventory_report({"x": 1})
    report.staff_report([("B", "T", 2)])
    assert ["A", "1", "1.00"] in calls
    assert ["x", "1"] in calls
    assert ["B", "T", "2"] in calls
    assert ["Product", "Units", "Revenue"] in calls


def test_format_row_strips_trailing_space():
    assert report.format_row(["only"], [8]) == "only"
