import re
import asyncio
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from config import HTTP_TIMEOUT

console = Console()

BASE_URL = "https://mangabuddy.com"
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def _build_headers(referer: str | None = None, extra_headers: dict | None = None) -> dict:
    headers = BASE_HEADERS.copy()
    headers["Referer"] = referer or BASE_URL
    if extra_headers:
        headers.update(extra_headers)
    return headers


async def _fetch_text(
    client: httpx.AsyncClient,
    url: str,
    referer: str | None = None,
    extra_headers: dict | None = None,
) -> str:
    response = await client.get(url, headers=_build_headers(referer, extra_headers))
    response.raise_for_status()
    return response.text


def _extract_manga_slug(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.strip("/")
    if not path:
        return ""
    return path.split("/")[0]


def _extract_metadata(soup: BeautifulSoup, page_url: str) -> dict:
    name_box = soup.find("div", class_="name box")
    manga_title = name_box.find("h1").get_text(strip=True) if name_box else "Unknown Title"

    metadata = {
        "Title": manga_title,
        "Web": page_url,
        "Series": manga_title,
        "Manga": "Yes",
    }

    detail_box = soup.find("div", class_="detail-box")
    if detail_box:
        summary_div = detail_box.find("div", class_="summary")
        if summary_div:
            metadata["Summary"] = summary_div.get_text(" ", strip=True)

        for p_tag in detail_box.find_all("p"):
            strong_tag = p_tag.find("strong")
            if not strong_tag:
                continue

            key = strong_tag.get_text(strip=True).replace(":", "")
            full_text = p_tag.get_text(" ", strip=True)
            key_text = strong_tag.get_text(" ", strip=True)
            value = full_text.replace(key_text, "", 1).strip(" :")

            if key == "Author(s)":
                metadata["Writer"] = value
            elif key == "Genre(s)":
                metadata["Genre"] = value

    return metadata


def _extract_book_id(html: str) -> str | None:
    match = re.search(r"var\s+bookId\s*=\s*(\d+);", html)
    return match.group(1) if match else None


def _chapter_number_from_title(title: str) -> float:
    match = re.search(r"Chapter\s+([\d.]+)", title, re.IGNORECASE)
    if not match:
        return float("inf")
    try:
        return float(match.group(1))
    except ValueError:
        return float("inf")


async def _fetch_chapters(client: httpx.AsyncClient, book_id: str) -> list[dict]:
    api_url = f"{BASE_URL}/api/manga/{book_id}/chapters?source=detail"
    html = await _fetch_text(
        client,
        api_url,
        referer=BASE_URL,
        extra_headers={"X-Requested-With": "XMLHttpRequest"},
    )

    soup = BeautifulSoup(html, "html.parser")
    chapter_rows = []

    for idx, li in enumerate(soup.find_all("li")):
        a_tag = li.find("a")
        strong = li.find("strong", class_="chapter-title")
        if not a_tag or not strong:
            continue

        href = a_tag.get("href", "").strip()
        if not href:
            continue

        if href.startswith("http"):
            chapter_url = href
        else:
            chapter_url = f"{BASE_URL}{href if href.startswith('/') else '/' + href}"

        title = strong.get_text(strip=True)
        chapter_rows.append(
            {
                "name": title,
                "url": chapter_url,
                "_number": _chapter_number_from_title(title),
                "_idx": idx,
            }
        )

    chapter_rows.sort(key=lambda item: (item["_number"], item["_idx"]))
    return [{"name": row["name"], "url": row["url"]} for row in chapter_rows]


async def get_manga_details(url: str):
    """
    Scrapes manga title, metadata, and chapter URLs from a MangaBuddy series URL.
    """
    try:
        manga_slug = _extract_manga_slug(url)
        if not manga_slug:
            return None, None

        series_url = f"{BASE_URL}/{manga_slug}"

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            detail_html = await _fetch_text(client, series_url, referer=BASE_URL)
            soup = BeautifulSoup(detail_html, "html.parser")
            metadata = _extract_metadata(soup, series_url)

            book_id = _extract_book_id(detail_html)
            if not book_id:
                console.print("[bold red]Could not find bookId on manga page.[/bold red]")
                return metadata, []

            chapters = await _fetch_chapters(client, book_id)
            return metadata, chapters

    except httpx.HTTPError as e:
        console.print(f"[bold red]Error fetching URL:[/bold red] {e}")
        return None, None
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during scraping manga details:[/bold red] {e}")
        return None, None


async def get_image_urls(chapter_url: str, client: httpx.AsyncClient | None = None) -> list[str]:
    """
    Scrapes image URLs from a MangaBuddy chapter URL by parsing `var chapImages`.
    """
    own_client = client is None
    active_client = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True)

    try:
        html = await _fetch_text(active_client, chapter_url, referer=BASE_URL)
        match = re.search(r"var\s+chapImages\s*=\s*['\"]([^'\"]+)['\"]", html)
        if not match:
            return []

        return [
            re.sub(r"\?.*$", "", img.strip())
            for img in match.group(1).split(",")
            if img.strip()
        ]
    except httpx.HTTPError as e:
        console.print(f"[bold red]Error fetching chapter page:[/bold red] {e}")
        return []
    finally:
        if own_client:
            await active_client.aclose()


if __name__ == "__main__":
    async def test_scraper():
        test_manga_url = "https://mangabuddy.com/codename-anastasia"
        metadata, chapter_data = await get_manga_details(test_manga_url)

        if metadata and chapter_data:
            console.print(f"\n[bold green]Manga Title:[/bold green] {metadata.get('Title', 'Unknown Title')}")
            console.print("[bold green]Chapters:[/bold green]")
            for i, chapter in enumerate(chapter_data[:5]):
                console.print(f"  {i+1}. [cyan]{chapter['name']}[/cyan]: {chapter['url']}")
            if len(chapter_data) > 5:
                console.print(f"  ...and {len(chapter_data) - 5} more chapters.")

            first_chapter_url = chapter_data[0]["url"]
            console.print(f"\n[bold green]Testing image scraping for:[/bold green] {first_chapter_url}")
            image_urls = await get_image_urls(first_chapter_url)
            if image_urls:
                console.print(f"[bold green]Found {len(image_urls)} images for the first chapter.[/bold green]")
            else:
                console.print("[bold red]No image URLs found for the first chapter.[/bold red]")

    asyncio.run(test_scraper())
