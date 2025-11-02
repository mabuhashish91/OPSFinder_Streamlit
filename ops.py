# ops.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://gesund.bund.de/ops-code-suche/"

def normalize_code_for_url(code: str) -> str:
    code = (code or "").strip()
    return code.replace(".", "-").lower()

def fetch_ops_page(code: str, headers=None, timeout=20):
    slug = normalize_code_for_url(code)
    url = urljoin(BASE_URL, slug)
    default_headers = {"User-Agent": "Mozilla/5.0 (compatible; OPSStreamlit/1.0)"}
    if headers:
        default_headers.update(headers)
    resp = requests.get(url, headers=default_headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text, url

def parse_ops_page(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # find "OPS-Code ..." heading
    h1 = next((t for t in soup.find_all(["h1", "h2"])
               if "ops-code" in t.get_text(strip=True).lower()), None)

    code_written = ""
    desc = ""
    zusatz = []

    if h1:
        text = " ".join(h1.get_text(" ", strip=True).split())
        code_written = text.replace("OPS-Code", "").strip().rstrip(":").strip()
        if ":" in code_written:
            code_written = code_written.split(":")[0].strip()

        nxt = h1.find_next()
        while nxt:
            t = nxt.get_text(" ", strip=True) if hasattr(nxt, "get_text") else ""
            low = (t or "").lower()
            if t:
                if low.startswith("ops-code"):
                    pass
                elif low.startswith("aus ") or low.startswith("hinweis") or low.startswith("bei ihnen"):
                    pass
                elif low.startswith("zusatzkennzeichen"):
                    break
                else:
                    desc = t
                    break
            nxt = nxt.find_next()

    for header in soup.find_all(["h2", "h3"]):
        if header.get_text(strip=True).lower().startswith("zusatzkennzeichen"):
            ul = header.find_next(["ul", "ol"])
            if ul:
                for li in ul.find_all("li"):
                    t = " ".join(li.get_text(" ", strip=True).split())
                    if t:
                        zusatz.append(t)
            break

    return code_written, desc, zusatz

def extract_single(code: str, headers=None, timeout=20):
    try:
        html, link = fetch_ops_page(code, headers=headers, timeout=timeout)
        code_written, desc, zusatz = parse_ops_page(html)
        return {
            "Code": code_written or (code or "").strip(),
            "Description": desc,
            "Zusatzkennzeichen": "; ".join(zusatz) if zusatz else "",
            "DirectLink": link,
            "error": None
        }
    except requests.HTTPError as e:
        return {"Code": code, "Description": "", "Zusatzkennzeichen": "", "DirectLink": "", "error": f"HTTP {e.response.status_code}"}
    except requests.RequestException as e:
        return {"Code": code, "Description": "", "Zusatzkennzeichen": "", "DirectLink": "", "error": f"Network error: {e}"}
    except Exception as e:
        return {"Code": code, "Description": "", "Zusatzkennzeichen": "", "DirectLink": "", "error": str(e)}