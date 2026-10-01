def collect(item, bucket=[]):
    bucket.append(item)  # BUG: shared default
    return bucket
