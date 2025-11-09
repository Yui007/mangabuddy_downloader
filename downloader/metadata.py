import xml.etree.ElementTree as ET
from xml.dom import minidom

def create_comic_info_xml(metadata: dict) -> str:
    """
    Creates a ComicInfo.xml string from a metadata dictionary.
    """
    root = ET.Element("ComicInfo")
    
    # Add metadata fields
    fields = [
        "Title", "Series", "Number", "Volume", "Summary", "Writer", 
        "Penciller", "Inker", "Colorist", "Letterer", "CoverArtist", 
        "Editor", "Publisher", "Genre", "Web", "Manga"
    ]
    
    for field in fields:
        if field in metadata and metadata[field]:
            sub_element = ET.SubElement(root, field)
            sub_element.text = str(metadata[field])

    # Pretty print XML
    xml_str = ET.tostring(root, 'utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml_str = dom.toprettyxml(indent="  ")
    
    return pretty_xml_str