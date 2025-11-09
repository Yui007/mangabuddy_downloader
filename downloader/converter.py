import os
from PIL import Image
import zipfile
from rich.console import Console
from .metadata import create_comic_info_xml

console = Console()

def convert_images_to_pdf(image_paths: list, output_path: str):
    """
    Converts a list of image paths to a single PDF file.
    """
    if not image_paths:
        console.print("[bold red]No images to convert to PDF.[/bold red]")
        return False

    images = []
    for img_path in image_paths:
        try:
            img = Image.open(img_path).convert("RGB")
            images.append(img)
        except Exception as e:
            console.print(f"[bold red]Error opening image {img_path}:[/bold red] {e}")
            return False

    try:
        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:])
            console.print(f"[bold green]Successfully converted to PDF:[/bold green] {output_path}")
            return True
        return False
    except Exception as e:
        console.print(f"[bold red]Error converting to PDF:[/bold red] {e}")
        return False

def convert_images_to_cbz(image_paths: list, output_path: str, metadata: dict | None = None):
    """
    Converts a list of image paths to a CBZ (Comic Book Zip) file
    and includes a ComicInfo.xml file if metadata is provided.
    """
    if not image_paths:
        console.print("[bold red]No images to convert to CBZ.[/bold red]")
        return False

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
            for img_path in image_paths:
                cbz_file.write(img_path, os.path.basename(img_path))
            
            if metadata:
                xml_content = create_comic_info_xml(metadata)
                cbz_file.writestr("ComicInfo.xml", xml_content)

        console.print(f"[bold green]Successfully converted to CBZ:[/bold green] {output_path}")
        return True
    except Exception as e:
        console.print(f"[bold red]Error converting to CBZ:[/bold red] {e}")
        return False

if __name__ == "__main__":
    # Example usage for testing
    # Create dummy images for testing
    test_dir = "test_images"
    os.makedirs(test_dir, exist_ok=True)
    img1_path = os.path.join(test_dir, "test_image_1.png")
    img2_path = os.path.join(test_dir, "test_image_2.png")

    # PIL type hint issue, color tuple is correct for 'RGB' mode
    Image.new('RGB', (100, 100), color=(255, 0, 0)).save(img1_path)  # type: ignore[arg-type]
    Image.new('RGB', (100, 100), color=(0, 0, 255)).save(img2_path)  # type: ignore[arg-type]

    image_list = [img1_path, img2_path]

    # Test PDF conversion
    pdf_output = "test_manga.pdf"
    convert_images_to_pdf(image_list, pdf_output)

    # Test CBZ conversion
    cbz_output = "test_manga.cbz"
    convert_images_to_cbz(image_list, cbz_output)

    # Clean up dummy images
    os.remove(img1_path)
    os.remove(img2_path)
    os.rmdir(test_dir)