import os
import re
import asyncio

import httpx
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn

from downloader.scraper import get_image_urls, BASE_HEADERS
from config import MAX_IMAGE_THREADS, RETRY_ATTEMPTS, DOWNLOAD_PATH, HTTP_TIMEOUT

console = Console()

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


async def download_image(
    client: httpx.AsyncClient,
    url: str,
    path: str,
    chapter_url: str,
    retries: int = RETRY_ATTEMPTS,
):
    """
    Downloads an image from a URL to a specified path with retries.
    """
    for attempt in range(retries):
        try:
            headers = BASE_HEADERS.copy()
            headers["Referer"] = chapter_url

            response = await client.get(url, headers=headers)
            response.raise_for_status()
            if not response.content:
                raise ValueError("Empty image payload")

            with open(path, "wb") as f:
                f.write(response.content)
            return True
        except Exception as e:
            console.print(f"[bold yellow]Attempt {attempt + 1}/{retries} failed for {url}:[/bold yellow] {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                console.print(f"[bold red]Failed to download image from {url} after {retries} attempts.[/bold red]")
                return False

async def download_chapter(chapter_url: str, manga_title: str, chapter_name: str, overall_progress=None):
    """
    Downloads all images for a given chapter.
    """
    local_console = overall_progress.console if overall_progress else console
    local_console.print(f"Downloading chapter: [bold blue]{chapter_name}[/bold blue]")
    
    # Create directory for the manga and chapter
    manga_dir = os.path.join(DOWNLOAD_PATH, sanitize_filename(manga_title))
    chapter_dir = os.path.join(manga_dir, sanitize_filename(chapter_name))
    os.makedirs(chapter_dir, exist_ok=True)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        image_urls = await get_image_urls(chapter_url, client=client)
        if not image_urls:
            local_console.print(f"[bold red]No images found for {chapter_name}. Skipping download.[/bold red]")
            return chapter_dir

        progress_context = None
        if overall_progress is None:
            progress_context = Progress(
                TextColumn("[bold blue]{task.description}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=local_console,
            )
            progress_context.__enter__()
            progress = progress_context
        else:
            progress = overall_progress

        task = progress.add_task(f"[cyan]Downloading {chapter_name} images...", total=len(image_urls))
        semaphore = asyncio.Semaphore(MAX_IMAGE_THREADS)

        async def download_single(index: int, img_url: str):
            ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
            img_path = os.path.join(chapter_dir, f"page_{index + 1}{ext}")
            async with semaphore:
                ok = await download_image(client, img_url, img_path, chapter_url, RETRY_ATTEMPTS)
            progress.update(task, advance=1)
            return ok

        await asyncio.gather(*(download_single(i, url) for i, url in enumerate(image_urls)))

        progress.remove_task(task)
        if progress_context is not None:
            progress_context.__exit__(None, None, None)

    local_console.print(f"[bold green]Finished downloading {chapter_name}[/bold green]")
    return chapter_dir

if __name__ == "__main__":
    # Example usage for testing
    test_manga_title = "Eleceed"
    test_chapter_name = "Chapter 1"
    test_chapter_url = "https://mangabuddy.com/eleceed-chapter-1"

    async def test_download():
        await download_chapter(test_chapter_url, test_manga_title, test_chapter_name)
    
    asyncio.run(test_download())
