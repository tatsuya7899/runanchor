import requests


def headline(url):
    html = requests.get(url, timeout=5).text
    start = html.index("<title>") + 7
    end = html.index("</title>")
    return html[start:end]
