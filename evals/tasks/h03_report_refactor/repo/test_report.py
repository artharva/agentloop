import report


def test_sales_report():
    text = report.sales_report([("Widget", 3, 29.97)])
    assert text.splitlines() == [
        "Product      |  Units |    Revenue",
        "Widget       |      3 |      29.97",
    ]


def test_inventory_report_sorted():
    text = report.inventory_report({"pear": 2, "apple": 10})
    assert text.splitlines()[1:] == ["apple        |     10", "pear         |      2"]


def test_staff_report():
    assert report.staff_report([("Ada", "Research", 36)]).splitlines()[1] == "Ada        |     Research |   36"


def test_format_row():
    assert report.format_row(["a", "1"], [3, 4]) == "a   |    1"
