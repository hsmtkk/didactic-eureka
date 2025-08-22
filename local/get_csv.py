import urllib.request

import bs4

with urllib.request.urlopen(
    "https://www.jpx.co.jp/markets/derivatives/settlement-price/index.html"
) as f:
    html_content = f.read()

# print(html_content)

soup = bs4.BeautifulSoup(html_content, "html.parser")
a_tags = soup.find_all("a", href=True)
for a_tag in a_tags:
    href = a_tag["href"]
    if ".csv" in href:
        print(href)
