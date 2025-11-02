# ops.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://gesund.bund.de/ops-code-suche/"

def normalize_code_for_url(code: str) -> str:
    code = (code or "").strip()
    return code.replace(".", "-").lower()

def fetch_ops_page(code: str) -> str:
    slug = normalize_code_for_url(code)
    url = urljoin(BASE_URL, slug)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OPSWeb/1.0)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text

def parse_ops_page(html: str):
    """
    Returns (code_as_written, official_description, zusatz_list)
    """
    soup = BeautifulSoup(html, "html.parser")
    h1 = None
    for tag in soup.find_all(["h1", "h2"]):
        if "ops-code" in tag.get_text(strip=True).lower():
            h1 = tag
            break

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
            t_norm = (t or "").strip()
            low = t_norm.lower()
            if t_norm:
                if low.startswith("ops-code"):
                    pass
                elif low.startswith("aus ") or low.startswith("hinweis") or low.startswith("bei ihnen"):
                    pass
                elif low.startswith("zusatzkennzeichen"):
                    break
                else:
                    desc = t_norm
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

def extract_single(code: str):
    try:
        html = fetch_ops_page(code)
        code_written, desc, zusatz = parse_ops_page(html)
        link = urljoin(BASE_URL, normalize_code_for_url(code))
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