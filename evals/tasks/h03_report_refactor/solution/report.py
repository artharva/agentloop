"""Plain-text reports."""


def format_row(values: list[str], widths: list[int]) -> str:
    """First column left-aligned, the rest right-aligned, joined with ' | '."""
    cells = [
        str(value).ljust(width) if i == 0 else str(value).rjust(width)
        for i, (value, width) in enumerate(zip(values, widths))
    ]
    return " | ".join(cells).rstrip()


def sales_report(rows: list[tuple[str, int, float]]) -> str:
    widths = [12, 6, 10]
    lines = [format_row(["Product", "Units", "Revenue"], widths)]
    for product, units, revenue in rows:
        lines.append(format_row([product, str(units), f"{revenue:.2f}"], widths))
    return "\n".join(lines)


def inventory_report(stock: dict[str, int]) -> str:
    widths = [12, 6]
    lines = [format_row(["Item", "Qty"], widths)]
    for item in sorted(stock):
        lines.append(format_row([item, str(stock[item])], widths))
    return "\n".join(lines)


def staff_report(people: list[tuple[str, str, int]]) -> str:
    widths = [10, 12, 4]
    lines = [format_row(["Name", "Team", "Age"], widths)]
    for name, team, age in people:
        lines.append(format_row([name, team, str(age)], widths))
    return "\n".join(lines)
