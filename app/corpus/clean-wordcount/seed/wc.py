def top_word(text):
    counts = {}
    for w in text.split():
        counts[w] = counts.get(w, 0) + 1
    return min(counts, key=counts.get)   # BUG: least frequent
