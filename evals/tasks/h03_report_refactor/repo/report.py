"""Plain-text reports."""


def sales_report(rows: list[tuple[str, int, float]]) -> str:
    widths = [12, 6, 10]
    lines = []
    header = ["Product", "Units", "Revenue"]
    cells = [str(v) for v in header]
    lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    for product, units, revenue in rows:
        cells = [product, str(units), f"{revenue:.2f}"]
        lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    return "\n".join(lines)


def inventory_report(stock: dict[str, int]) -> str:
    widths = [12, 6]
    lines = []
    cells = ["Item", "Qty"]
    lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    for item in sorted(stock):
        cells = [item, str(stock[item])]
        lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    return "\n".join(lines)


def staff_report(people: list[tuple[str, str, int]]) -> str:
    widths = [10, 12, 4]
    lines = []
    cells = ["Name", "Team", "Age"]
    lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    for name, team, age in people:
        cells = [name, team, str(age)]
        lines.append(" | ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in enumerate(zip(cells, widths))).rstrip())
    return "\n".join(lines)
