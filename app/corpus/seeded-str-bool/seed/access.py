def can_write(user):
    return "true" if user.get("admin") else "false"
