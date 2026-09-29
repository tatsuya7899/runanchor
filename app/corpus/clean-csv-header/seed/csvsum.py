def column_sum(text, col):
    lines = text.strip().splitlines()
    header = lines[0].split(",")
    idx = header.index(col)
    total = 0
    for row in lines:          # BUG: header included
        total += int(row.split(",")[idx])
    return total
