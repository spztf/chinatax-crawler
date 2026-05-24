"""Quick connectivity test."""
import requests, time

url = "https://www.chinatax.gov.cn/chinatax/manuscriptList/c102025"
params = {
    "_channelName": "税案通报",
    "_isAgg": "0",
    "_pageSize": "20",
    "_template": "index",
    "_pageIndex": "1",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

t0 = time.time()
try:
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}, Length: {len(r.text)}, Time: {time.time()-t0:.1f}s")
    # Check if we can parse it
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "lxml")
    ul = soup.find("ul", class_="list")
    if ul:
        items = ul.find_all("li")
        print(f"Found {len(items)} items")
        for li in items[:3]:
            a = li.find("a")
            span = li.find("span")
            print(f"  - {a.get_text(strip=True)[:60] if a else 'N/A'} | {span.get_text(strip=True) if span else 'N/A'}")
    # Check pagination
    text = soup.get_text()
    import re
    m = re.search(r"共(\d+)页", text)
    if m:
        print(f"Total pages: {m.group(1)}")
except Exception as e:
    print(f"Error: {e}")
