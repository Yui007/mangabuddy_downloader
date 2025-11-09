import sys
import os
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QProgressBar,
    QTextEdit, QGroupBox, QButtonGroup, QRadioButton, QListWidget,
    QListWidgetItem, QSpinBox, QFileDialog, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QLinearGradient, QBrush

# Import our existing modules
from downloader.scraper import get_manga_details
from downloader.download import download_chapter
from downloader.converter import convert_images_to_pdf, convert_images_to_cbz
from config import DELETE_IMAGES_AFTER_CONVERSION, MAX_CHAPTER_THREADS

# Import Rich for progress tracking
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

class MangaDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MangaBuddy Downloader")
        self.setGeometry(100, 100, 900, 700)
        
        # Store selected chapters
        self.selected_chapters = []
        self.chapters = []
        self.manga_metadata = {}
        
        # Set up the dark theme
        self.setup_theme()
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)
        
        # Create UI elements
        self.create_header()
        self.create_url_input_section()
        self.create_chapter_selection_section()
        self.create_options_section()
        self.create_progress_section()
        self.create_log_section()
        self.create_action_buttons()
        
        # Apply modern styles
        self.apply_styles()
        
    def setup_theme(self):
        """Set up the dark theme with gradients"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 40))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 50))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 70))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
        
    def create_header(self):
        """Create the header with title and description"""
        header_layout = QVBoxLayout()
        
        title_label = QLabel("MangaBuddy Downloader")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("title")
        
        desc_label = QLabel("Download your favorite manga with ease")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setObjectName("description")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        
        self.main_layout.addLayout(header_layout)
        
    def create_url_input_section(self):
        """Create the URL input section"""
        url_group = QGroupBox("Manga URL")
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://mangabuddy.com/manga-title")
        self.url_input.setObjectName("urlInput")
        
        self.scrape_button = QPushButton("Scrape Manga")
        self.scrape_button.setObjectName("scrapeButton")
        self.scrape_button.clicked.connect(self.scrape_manga)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.scrape_button)
        
        url_group.setLayout(url_layout)
        self.main_layout.addWidget(url_group)
        
    def create_chapter_selection_section(self):
        """Create the chapter selection section"""
        chapter_group = QGroupBox("Chapter Selection")
        chapter_layout = QVBoxLayout()
        
        # Chapter selection controls
        selection_layout = QHBoxLayout()
        
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        
        self.select_range_button = QPushButton("Select Range")
        self.select_range_button.clicked.connect(self.select_chapter_range)
        
        selection_layout.addWidget(self.select_all_checkbox)
        selection_layout.addWidget(self.select_range_button)
        selection_layout.addStretch()
        
        # Chapter list
        self.chapter_list = QListWidget()
        self.chapter_list.setObjectName("chapterList")
        self.chapter_list.itemChanged.connect(self.on_chapter_selection_changed)
        
        chapter_layout.addLayout(selection_layout)
        chapter_layout.addWidget(self.chapter_list)
        
        chapter_group.setLayout(chapter_layout)
        self.main_layout.addWidget(chapter_group)
        
    def create_options_section(self):
        """Create the options section"""
        options_group = QGroupBox("Download Options")
        options_layout = QVBoxLayout()
        
        # Conversion format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Conversion Format:")
        format_layout.addWidget(format_label)
        
        self.format_group = QButtonGroup()
        
        self.pdf_radio = QRadioButton("PDF")
        self.cbz_radio = QRadioButton("CBZ")
        self.none_radio = QRadioButton("None (Images Only)")
        self.none_radio.setChecked(True)
        
        self.format_group.addButton(self.pdf_radio)
        self.format_group.addButton(self.cbz_radio)
        self.format_group.addButton(self.none_radio)
        
        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.cbz_radio)
        format_layout.addWidget(self.none_radio)
        format_layout.addStretch()
        
        # Delete images option
        self.delete_images_checkbox = QCheckBox("Delete images after conversion")
        self.delete_images_checkbox.setChecked(DELETE_IMAGES_AFTER_CONVERSION)
        
        options_layout.addLayout(format_layout)
        options_layout.addWidget(self.delete_images_checkbox)
        
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)
        
    def create_progress_section(self):
        """Create the progress section"""
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout()
        
        # Overall progress
        overall_layout = QHBoxLayout()
        overall_label = QLabel("Overall Progress:")
        self.overall_progress = QProgressBar()
        self.overall_progress.setObjectName("overallProgress")
        self.overall_progress.setValue(0)
        
        overall_layout.addWidget(overall_label)
        overall_layout.addWidget(self.overall_progress)
        
        progress_layout.addLayout(overall_layout)
        
        progress_group.setLayout(progress_layout)
        self.main_layout.addWidget(progress_group)
        
    def create_log_section(self):
        """Create the log section"""
        log_group = QGroupBox("Download Log")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("logOutput")
        
        log_layout.addWidget(self.log_output)
        
        log_group.setLayout(log_layout)
        self.main_layout.addWidget(log_group)
        
    def create_action_buttons(self):
        """Create the action buttons"""
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Download Selected Chapters")
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.clicked.connect(self.reset_gui)
        
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.reset_button)
        
        self.main_layout.addLayout(button_layout)
        
    def apply_styles(self):
        """Apply modern styles with gradients and animations"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e28;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a5a;
                border-radius: 15px;
                margin-top: 1em;
                padding-top: 10px;
                background-color: rgba(40, 40, 55, 150);
            }
            
            QGroupBox::title {
                subline-offset: -10px;
                padding: 0 10px;
                color: #a0a0d0;
            }
            
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8A2BE2, stop:1 #1E90FF);
                margin: 10px;
            }
            
            QLabel#description {
                font-size: 14px;
                color: #b0b0c0;
                margin-bottom: 20px;
            }
            
            QLineEdit#urlInput {
                padding: 10px;
                border: 2px solid #3a3a5a;
                border-radius: 10px;
                background-color: #252535;
                color: white;
                font-size: 14px;
            }
            
            QLineEdit#urlInput:focus {
                border-color: #8A2BE2;
                border-width: 2px;
            }
            
            QPushButton {
                padding: 10px 20px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            
            QPushButton#scrapeButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8A2BE2, stop:1 #4B0082);
                color: white;
            }
            
            QPushButton#scrapeButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9A3BF2, stop:1 #5B1092);
            }
            
            QPushButton#downloadButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00C9FF, stop:1 #92FE9D);
                color: black;
            }
            
            QPushButton#downloadButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00D9FF, stop:1 #A2FEAD);
            }
            
            QPushButton#downloadButton:disabled {
                background-color: #555566;
                color: #888888;
            }
            
            QPushButton#resetButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF416C, stop:1 #FF4B2B);
                color: white;
            }
            
            QPushButton#resetButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF517C, stop:1 #FF5B3B);
            }
            
            QListWidget#chapterList {
                background-color: #252535;
                border: 2px solid #3a3a5a;
                border-radius: 10px;
                padding: 5px;
                color: white;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a5a;
            }
            
            QListWidget::item:selected {
                background-color: #3a3a5a;
            }
            
            QProgressBar#overallProgress, QProgressBar#chapterProgress {
                border: 2px solid #3a3a5a;
                border-radius: 10px;
                text-align: center;
                color: white;
                background-color: #252535;
            }
            
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8A2BE2, stop:1 #1E90FF);
                border-radius: 8px;
            }
            
            QTextEdit#logOutput {
                background-color: #252535;
                border: 2px solid #3a3a5a;
                border-radius: 10px;
                color: #d0d0e0;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
            
            QCheckBox, QRadioButton {
                color: #d0d0e0;
                spacing: 5px;
            }
            
            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
                border: 2px solid #3a3a5a;
                border-radius: 4px;
                background-color: #252535;
            }
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #8A2BE2;
                border: 2px solid #8A2BE2;
                border-radius: 4px;
            }
            
            QRadioButton::indicator:checked {
                border-radius: 9px;
            }
        """)
        
    def log_message(self, message):
        """Add a message to the log output"""
        self.log_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())
        
    def scrape_manga(self):
        """Scrape manga details from the provided URL"""
        url = self.url_input.text().strip()
        
        if not url.startswith("https://mangabuddy.com/"):
            self.log_message("Invalid MangaBuddy URL. Please enter a URL starting with 'https://mangabuddy.com/'.")
            return
            
        self.log_message(f"Scraping manga details from: {url}")
        
        # Disable UI during scraping
        self.scrape_button.setEnabled(False)
        self.url_input.setEnabled(False)
        
        # Run scraping in a separate thread to prevent UI freezing
        self.scraping_thread = ScrapingThread(url)
        self.scraping_thread.result_signal.connect(self.on_scraping_finished)
        self.scraping_thread.start()
        
    def on_scraping_finished(self, metadata, chapters):
        """Handle the result of the scraping operation"""
        self.scrape_button.setEnabled(True)
        self.url_input.setEnabled(True)
        
        if metadata and chapters:
            self.manga_metadata = metadata
            manga_title = self.manga_metadata.get("Title", "Unknown Title")
            self.log_message(f"Successfully scraped manga: {manga_title}")
            self.log_message(f"Found {len(chapters)} chapters")
            
            # Store chapters
            self.chapters = chapters
            
            # Populate chapter list
            self.chapter_list.clear()
            for i, chapter in enumerate(chapters, 1):
                item = QListWidgetItem(f"{i}. {chapter['name']}")
                item.setCheckState(Qt.CheckState.Unchecked)
                self.chapter_list.addItem(item)
                
            # Enable download button
            self.download_button.setEnabled(True)
        else:
            self.log_message("Failed to scrape manga details. Please check the URL or your internet connection.")
            
    def toggle_select_all(self, state):
        """Toggle selection of all chapters"""
        # Disconnect the signal temporarily to avoid infinite loop
        self.chapter_list.itemChanged.disconnect(self.on_chapter_selection_changed)
        
        check_state = Qt.CheckState(state)
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item:
                item.setCheckState(check_state)
                
        # Reconnect the signal
        self.chapter_list.itemChanged.connect(self.on_chapter_selection_changed)
            
    def select_chapter_range(self):
        """Open a dialog to select a range of chapters"""
        if not self.chapters:
            return
            
        # Create a simple range selection dialog
        range_dialog = RangeSelectionDialog(len(self.chapters), self)
        if range_dialog.exec() == QDialog.DialogCode.Accepted.value:
            start, end = range_dialog.get_range()
            if start and end:
                # Disconnect the signal temporarily to avoid infinite loop
                self.chapter_list.itemChanged.disconnect(self.on_chapter_selection_changed)
                
                # Select the range
                for i in range(start-1, end):
                    item = self.chapter_list.item(i)
                    if item:
                        item.setCheckState(Qt.CheckState.Checked)
                        
                # Reconnect the signal
                self.chapter_list.itemChanged.connect(self.on_chapter_selection_changed)
                
                # Update the select all checkbox
                self.on_chapter_selection_changed()
                    
    def on_chapter_selection_changed(self):
        """Handle chapter selection changes"""
        # Disconnect the signal temporarily to avoid infinite loop
        self.select_all_checkbox.stateChanged.disconnect(self.toggle_select_all)
        
        # Update select all checkbox state
        all_checked = True
        none_checked = True
        
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                none_checked = False
            elif item:
                all_checked = False
                
        if all_checked and self.chapter_list.count() > 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        elif none_checked:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
            
        # Reconnect the signal
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
            
    def get_selected_chapters(self):
        """Get the list of selected chapters"""
        selected = []
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(self.chapters[i])
        return selected
        
    def start_download(self):
        """Start the download process"""
        # Get selected chapters
        self.selected_chapters = self.get_selected_chapters()
        
        if not self.selected_chapters:
            self.log_message("Please select at least one chapter to download.")
            return
            
        # Get conversion format
        if self.pdf_radio.isChecked():
            conversion_format = "pdf"
        elif self.cbz_radio.isChecked():
            conversion_format = "cbz"
        else:
            conversion_format = "none"
            
        # Get delete images option
        delete_images = self.delete_images_checkbox.isChecked()
        
        # Get manga title from URL or scraping result
        manga_url = self.url_input.text().strip()
        manga_title = manga_url.split("/")[-1].replace("-", " ").title()
        
        # Disable UI during download
        self.download_button.setEnabled(False)
        self.scrape_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        self.select_range_button.setEnabled(False)
        self.chapter_list.setEnabled(False)
        self.pdf_radio.setEnabled(False)
        self.cbz_radio.setEnabled(False)
        self.none_radio.setEnabled(False)
        self.delete_images_checkbox.setEnabled(False)
        
        # Reset progress bars
        self.overall_progress.setValue(0)
        
        self.log_message(f"Starting download of {len(self.selected_chapters)} chapters...")
        
        # Start download in a separate thread
        self.download_thread = DownloadThread(
            self.selected_chapters,
            manga_title,
            conversion_format,
            delete_images,
            MAX_CHAPTER_THREADS,
            self.manga_metadata
        )
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.log_signal.connect(self.log_message)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()
        
    def update_progress(self, overall_value, chapter_value):
        """Update progress bars"""
        self.overall_progress.setValue(overall_value)
        
    def on_download_finished(self):
        """Handle download completion"""
        # Re-enable UI
        self.download_button.setEnabled(True)
        self.scrape_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.select_all_checkbox.setEnabled(True)
        self.select_range_button.setEnabled(True)
        self.chapter_list.setEnabled(True)
        self.pdf_radio.setEnabled(True)
        self.cbz_radio.setEnabled(True)
        self.none_radio.setEnabled(True)
        self.delete_images_checkbox.setEnabled(True)
        
        self.log_message("Download process completed!")
        QMessageBox.information(self, "Download Complete", "All selected chapters have been downloaded successfully!")
        
    def reset_gui(self):
        """Reset the GUI to initial state"""
        self.url_input.clear()
        self.chapter_list.clear()
        self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.none_radio.setChecked(True)
        self.delete_images_checkbox.setChecked(DELETE_IMAGES_AFTER_CONVERSION)
        self.log_output.clear()
        self.overall_progress.setValue(0)
        self.download_button.setEnabled(False)
        self.chapters = []
        self.selected_chapters = []

class ScrapingThread(QThread):
    """Thread for scraping manga details"""
    result_signal = pyqtSignal(dict, list)  # metadata, chapters
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        """Run the scraping operation"""
        try:
            metadata, chapters = get_manga_details(self.url)
            self.result_signal.emit(metadata, chapters)
        except Exception as e:
            print(f"Error in scraping thread: {e}")
            self.result_signal.emit({}, [])

class DownloadThread(QThread):
    """Thread for downloading chapters"""
    progress_signal = pyqtSignal(int, int)  # overall_progress, chapter_progress
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, selected_chapters, manga_title, conversion_format, delete_images, max_chapter_threads, manga_metadata=None):
        super().__init__()
        self.selected_chapters = selected_chapters
        self.manga_title = manga_title
        self.conversion_format = conversion_format
        self.delete_images = delete_images
        self.max_chapter_threads = max_chapter_threads
        self.manga_metadata = manga_metadata if manga_metadata else {}
        
    def run(self):
        """Run the download operation"""
        try:
            # Use asyncio to run the async download functions
            asyncio.run(self.download_chapters_async())
        except Exception as e:
            self.log_signal.emit(f"Error in download thread: {e}")
        finally:
            self.finished_signal.emit()
            
    async def download_chapters_async(self):
        """Async function to download chapters concurrently with thread limit"""
        total_chapters = len(self.selected_chapters)
        
        # Create a custom progress tracker
        class ProgressTracker:
            def __init__(self, total, progress_callback, log_callback):
                self.total = total
                self.current = 0
                self.progress_callback = progress_callback
                self.log_callback = log_callback
                
            def update(self, value=None):
                if value is not None:
                    self.current = value
                else:
                    self.current += 1
                overall_progress = int((self.current / self.total) * 100)
                self.progress_callback(overall_progress, 0)  # Chapter progress will be updated separately
                
        progress_tracker = ProgressTracker(total_chapters, self.progress_signal.emit, self.log_signal.emit)
        
        # Create a semaphore to limit concurrent chapter downloads
        semaphore = asyncio.Semaphore(self.max_chapter_threads)
        
        # Create a Rich Progress object for concurrent downloads
        console = Console()
        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TimeRemainingColumn(),
            console=console,
        ) as overall_progress:
            overall_task = overall_progress.add_task("[green]Overall Chapter Progress[/green]", total=len(self.selected_chapters))
            
            # Create download tasks for concurrent execution
            download_tasks = []
            
            # Define a wrapper function to limit concurrent downloads
            async def download_with_semaphore(chapter):
                async with semaphore:
                    return await download_chapter(
                        chapter['url'],
                        self.manga_title,
                        chapter['name'],
                        overall_progress  # Pass the overall_progress to avoid "Only one live display" error
                    )
            
            # Create tasks for each chapter
            for chapter in self.selected_chapters:
                # Create a task for each chapter download
                task = download_with_semaphore(chapter)
                download_tasks.append(task)
                
            # Download all chapters concurrently using asyncio.gather
            self.log_signal.emit(f"Starting concurrent download of {len(self.selected_chapters)} chapters (max {self.max_chapter_threads} at a time)...")
            chapter_dirs = await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # Process downloaded chapters (convert, delete images, etc.)
            for i, (chapter, chapter_dir) in enumerate(zip(self.selected_chapters, chapter_dirs)):
                chapter_name = chapter['name']
                
                # Update progress
                progress_tracker.update(i)
                overall_progress.update(overall_task, advance=1)
                
                # Check if download was successful
                if isinstance(chapter_dir, Exception):
                    self.log_signal.emit(f"Error downloading chapter {chapter_name}: {chapter_dir}")
                    continue
                    
                try:
                    # Convert if needed
                    if chapter_dir and isinstance(chapter_dir, str) and self.conversion_format != "none":
                        # Get list of downloaded images
                        try:
                            image_paths = [os.path.join(chapter_dir, f) for f in os.listdir(chapter_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
                            image_paths.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0])) # Sort numerically
                            
                            # Create output path
                            output_filename = f"{chapter_name.replace(' ', '_')}.{self.conversion_format}"
                            output_path = os.path.join(chapter_dir, output_filename)
                            
                            # Convert based on selected format
                            success = False
                            if self.conversion_format == "pdf":
                                success = convert_images_to_pdf(image_paths, output_path)
                                if success:
                                    self.log_signal.emit(f"Converted to PDF: {output_path}")
                            elif self.conversion_format == "cbz":
                                success = convert_images_to_cbz(image_paths, output_path, self.manga_metadata)
                                if success:
                                    self.log_signal.emit(f"Converted to CBZ: {output_path}")
                            
                            # Delete images if selected
                            if self.delete_images and success:
                                for img_path in image_paths:
                                    os.remove(img_path)
                                self.log_signal.emit(f"Deleted images for {chapter_name}")
                        except Exception as e:
                            self.log_signal.emit(f"Error processing chapter {chapter_name}: {e}")
                            
                except Exception as e:
                    self.log_signal.emit(f"Error processing chapter {chapter_name}: {e}")
                    
            # Final update
            progress_tracker.update(total_chapters)

class RangeSelectionDialog(QDialog):
    """Dialog for selecting a range of chapters"""
    
    def __init__(self, max_chapters, parent=None):
        super().__init__(parent)
        self.max_chapters = max_chapters
        self.selected_start = None
        self.selected_end = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Select Chapter Range")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # Start chapter selection
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Chapter:")
        self.start_spinbox = QSpinBox()
        self.start_spinbox.setRange(1, self.max_chapters)
        self.start_spinbox.setValue(1)
        
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_spinbox)
        
        # End chapter selection
        end_layout = QHBoxLayout()
        end_label = QLabel("End Chapter:")
        self.end_spinbox = QSpinBox()
        self.end_spinbox.setRange(1, self.max_chapters)
        self.end_spinbox.setValue(self.max_chapters)
        
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_spinbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(start_layout)
        layout.addLayout(end_layout)
        layout.addLayout(button_layout)
        
    def accept(self):
        """Accept the dialog and store selected range"""
        self.selected_start = self.start_spinbox.value()
        self.selected_end = self.end_spinbox.value()
        
        # Validate range
        if self.selected_start > self.selected_end:
            QMessageBox.warning(self, "Invalid Range", "Start chapter must be less than or equal to end chapter.")
            return
            
        super().accept()
        
    def get_range(self):
        """Get the selected range"""
        return self.selected_start, self.selected_end

def main():
    """Main function to run the GUI application"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = MangaDownloaderGUI()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()