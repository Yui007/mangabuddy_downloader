import typer
import os
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table # Import Table
import asyncio # Import asyncio

from downloader.scraper import get_manga_details
from downloader.download import download_chapter
from downloader.converter import convert_images_to_pdf, convert_images_to_cbz
from config import MAX_CHAPTER_THREADS, DELETE_IMAGES_AFTER_CONVERSION

app = typer.Typer()
console = Console()

@app.command()
def main_sync(): # Renamed to main_sync for clarity, as the actual main will be async
    asyncio.run(main_async())

async def main_async(): # New async main function
    """
    MangaBuddy Downloader CLI.
    """
    console.print("[bold green]Welcome to MangaBuddy Downloader![/bold green]")
    while True:
        manga_url = console.input("[bold cyan]Enter MangaBuddy URL:[/bold cyan] ")
        if not manga_url.startswith("https://mangabuddy.com/"):
            console.print("[bold red]Invalid MangaBuddy URL. Please enter a URL starting with 'https://mangabuddy.com/'.[/bold red]")
            continue

        with console.status("[bold yellow]Scraping manga details...[/bold yellow]", spinner="dots"):
            manga_metadata, chapters = await get_manga_details(manga_url)

        if not manga_metadata or not chapters:
            console.print("[bold red]Could not retrieve manga details. Please check the URL or your internet connection.[/bold red]")
            # Allow user to try again with a different URL
            if not Confirm.ask("[bold yellow]Do you want to try another URL?[/bold yellow]", default=True):
                return
        else:
            break

    manga_title = manga_metadata.get("Title", "Unknown Title")
    console.print(f"\n[bold green]Manga Title:[/bold green] {manga_title}")
    console.print(f"[bold green]Found {len(chapters)} chapters.[/bold green]")
    
    # Display chapters in a table
    table = Table(title="Chapters")
    table.add_column("Index", style="cyan", no_wrap=True)
    table.add_column("Chapter Name", style="magenta")
    
    for i, chapter in enumerate(chapters, 1):
        table.add_row(str(i), chapter['name'])
        
    console.print(table)

    # Chapter selection logic
    selected_chapters = []
    while True:
        console.print("\n[bold yellow]Choose chapter download option:[/bold yellow]")
        console.print("  [cyan]1.[/cyan] Download [bold white]single[/bold white] chapter")
        console.print("  [cyan]2.[/cyan] Download [bold white]range[/bold white] of chapters")
        console.print("  [cyan]3.[/cyan] Download [bold white]all[/bold white] chapters")
        
        choice = console.input("[bold cyan]Enter your choice (1/2/3):[/bold cyan] ").strip()

        if choice == '1':
            while True:
                try:
                    chapter_num = int(console.input(f"[bold cyan]Enter chapter number (1-{len(chapters)}):[/bold cyan] "))
                    if 1 <= chapter_num <= len(chapters):
                        selected_chapters = [chapters[chapter_num - 1]]
                        break
                    else:
                        console.print("[bold red]Invalid chapter number. Please try again.[/bold red]")
                except ValueError:
                    console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
            break
        elif choice == '2':
            while True:
                try:
                    range_input = console.input(f"[bold cyan]Enter chapter range (e.g., 5-10):[/bold cyan] ")
                    start, end = map(int, range_input.split('-'))
                    if 1 <= start <= end <= len(chapters):
                        selected_chapters = chapters[start - 1:end]
                        break
                    else:
                        console.print("[bold red]Invalid range. Please try again.[/bold red]")
                except ValueError:
                    console.print("[bold red]Invalid input. Please enter a range like 5-10.[/bold red]")
            break
        elif choice == '3':
            selected_chapters = chapters
            break
        else:
            console.print("[bold red]Invalid choice. Please enter 1, 2, or 3.[/bold red]")

    console.print(f"\n[bold green]Selected {len(selected_chapters)} chapters for download.[/bold green]")

    # Ask for conversion format
    conversion_format = None
    delete_images_after_conversion = None
    while True:
        console.print("\n[bold yellow]Choose conversion format:[/bold yellow]")
        console.print("  [cyan]1.[/cyan] PDF")
        console.print("  [cyan]2.[/cyan] CBZ")
        console.print("  [cyan]3.[/cyan] None (Keep images only)")
        
        convert_choice = console.input("[bold cyan]Enter your choice (1/2/3):[/bold cyan] ").strip()

        if convert_choice == '1':
            conversion_format = "pdf"
            delete_images_after_conversion = Confirm.ask(f"[bold yellow]Delete images after conversion?[/bold yellow]", default=DELETE_IMAGES_AFTER_CONVERSION)
            break
        elif convert_choice == '2':
            conversion_format = "cbz"
            delete_images_after_conversion = Confirm.ask(f"[bold yellow]Delete images after conversion?[/bold yellow]", default=DELETE_IMAGES_AFTER_CONVERSION)
            break
        elif convert_choice == '3':
            conversion_format = "none"
            break
        else:
            console.print("[bold red]Invalid choice. Please enter 1, 2, or 3.[/bold red]")

    with Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TimeRemainingColumn(),
        console=console,
    ) as overall_progress:
        overall_task = overall_progress.add_task("[green]Overall Chapter Progress[/green]", total=len(selected_chapters))

        # Create a semaphore to limit concurrent chapter downloads
        semaphore = asyncio.Semaphore(MAX_CHAPTER_THREADS)
        
        # Define a wrapper function to limit concurrent downloads
        async def download_with_semaphore(chapter):
            async with semaphore:
                return await download_chapter(chapter['url'], manga_title, chapter['name'], overall_progress)
        
        # Create download tasks for concurrent execution
        download_tasks = []
        for chapter in selected_chapters:
            download_tasks.append(download_with_semaphore(chapter))
        
        # Await all download tasks
        chapter_dirs = await asyncio.gather(*download_tasks)

        for i, chapter_dir in enumerate(chapter_dirs):
            chapter = selected_chapters[i] # Re-bind chapter for use in this scope

            if chapter_dir and conversion_format != "none":
                # Get list of downloaded images
                image_paths = [os.path.join(chapter_dir, f) for f in os.listdir(chapter_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
                image_paths.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0])) # Sort numerically based on page_xx.png

                # Change output_path to be inside the chapter_dir
                output_filename = f"{chapter['name'].replace(' ', '_')}.{conversion_format}"
                output_path = os.path.join(chapter_dir, output_filename)

                if conversion_format == "pdf":
                    convert_images_to_pdf(image_paths, output_path)
                elif conversion_format == "cbz":
                    convert_images_to_cbz(image_paths, output_path, manga_metadata)
                
                # Use the pre-determined delete choice
                if delete_images_after_conversion:
                    for img_path in image_paths:
                        os.remove(img_path)
                    console.print(f"[bold green]Deleted images for {chapter['name']}.[/bold green]")
            
            overall_progress.update(overall_task, advance=1)

if __name__ == "__main__":
    app() # Run the Typer application
