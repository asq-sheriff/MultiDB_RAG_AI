"""Enhanced Document Processor for Advanced Ingestion Pipeline"""

import asyncio
import logging
import mimetypes
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Enhanced file format support with better error handling
try:
    import PyPDF2

    PDF_PYPDF2_SUPPORT = True
except ImportError:
    PDF_PYPDF2_SUPPORT = False

try:
    import fitz  # PyMuPDF

    PDF_PYMUPDF_SUPPORT = True
except ImportError:
    PDF_PYMUPDF_SUPPORT = False

PDF_SUPPORT = PDF_PYPDF2_SUPPORT or PDF_PYMUPDF_SUPPORT

try:
    import docx2txt

    DOCX2TXT_SUPPORT = True
except ImportError:
    DOCX2TXT_SUPPORT = False

try:
    import mammoth

    MAMMOTH_SUPPORT = True
except ImportError:
    MAMMOTH_SUPPORT = False

DOCX_SUPPORT = DOCX2TXT_SUPPORT or MAMMOTH_SUPPORT

try:
    import pandas as pd

    CSV_SUPPORT = True
except ImportError:
    CSV_SUPPORT = False

try:
    from bs4 import BeautifulSoup

    HTML_SUPPORT = True
except ImportError:
    HTML_SUPPORT = False

pass


@dataclass
class DocumentMetadata:
    """Enhanced document metadata with comprehensive information"""

    file_path: str
    title: str
    file_type: str
    file_size: int
    mime_type: str
    encoding: str
    language: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    content_hash: Optional[str] = None
    extraction_method: Optional[str] = None
    processing_errors: List[str] = field(default_factory=list)


@dataclass
class DocumentChunk:
    """Enhanced document chunk with metadata"""

    chunk_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: DocumentMetadata
    embedding_text: str  # Text optimized for embedding generation
    chunk_type: str = "content"  # content, title, header, footer
    confidence: float = 1.0


@dataclass
class ProcessingConfig:
    """Configuration for document processing"""

    # File format support - dynamically determined
    supported_extensions: List[str] = field(
        default_factory=lambda: _get_supported_extensions()
    )

    # Chunking configuration - optimized for sentence-transformers/all-mpnet-base-v2
    chunk_size: int = 1500
    chunk_overlap: int = 180
    min_chunk_size: int = 100
    max_chunk_size: int = 3000

    # Processing configuration
    max_workers: int = 4
    use_parallel_processing: bool = True
    max_file_size_mb: int = 50

    # Content extraction
    preserve_formatting: bool = True
    extract_metadata: bool = True
    detect_language: bool = False

    # Error handling
    skip_corrupted_files: bool = True
    max_processing_errors: int = 5


def _get_supported_extensions() -> List[str]:
    """Dynamically determine supported file extensions based on available libraries"""
    extensions = [".txt", ".md", ".rst", ".json"]

    if PDF_SUPPORT:
        extensions.append(".pdf")
    if DOCX_SUPPORT:
        extensions.extend([".docx", ".doc"])
    if CSV_SUPPORT:
        extensions.append(".csv")
    if HTML_SUPPORT:
        extensions.extend([".html", ".htm"])

    return extensions


class EnhancedDocumentProcessor:
    """Advanced document processor with multi-format support and parallel processing"""

    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.executor = None
        self._setup_executor()

    def _setup_executor(self):
        """Setup appropriate executor based on configuration"""
        if self.config.use_parallel_processing:
            self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        else:
            self.executor = None

    async def process_directory(
        self, directory: Union[str, Path]
    ) -> List[DocumentChunk]:
        """Process all supported files in a directory with parallel processing"""
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        logger.info(f"📁 Scanning directory: {directory}")

        # Find all supported files
        files = self._find_supported_files(directory)
        logger.info(f"📄 Found {len(files)} supported files")

        if not files:
            logger.warning("No supported files found in directory")
            return []

        # Process files with progress tracking
        all_chunks = []
        processed_count = 0

        if self.config.use_parallel_processing and len(files) > 1:
            # Parallel processing for multiple files
            tasks = [self._process_file_async(file_path) for file_path in files]

            for completed_task in asyncio.as_completed(tasks):
                try:
                    chunks = await completed_task
                    all_chunks.extend(chunks)
                    processed_count += 1

                    if processed_count % 5 == 0:
                        logger.info(
                            f"📊 Processed {processed_count}/{len(files)} files"
                        )

                except Exception as e:
                    logger.error(f"❌ File processing failed: {e}")
                    if not self.config.skip_corrupted_files:
                        raise
        else:
            # Sequential processing
            for file_path in files:
                try:
                    chunks = await self._process_file_async(file_path)
                    all_chunks.extend(chunks)
                    processed_count += 1

                    if processed_count % 5 == 0:
                        logger.info(
                            f"📊 Processed {processed_count}/{len(files)} files"
                        )

                except Exception as e:
                    logger.error(f"❌ Failed to process {file_path}: {e}")
                    if not self.config.skip_corrupted_files:
                        raise

        logger.info(
            f"✅ Processing complete: {len(all_chunks)} chunks from {processed_count} files"
        )
        return all_chunks

    async def _process_file_async(self, file_path: Path) -> List[DocumentChunk]:
        """Process a single file asynchronously"""
        if self.executor:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_file_sync, file_path
            )
        else:
            return self._process_file_sync(file_path)

    def _process_file_sync(self, file_path: Path) -> List[DocumentChunk]:
        """Process a single file synchronously"""
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.config.max_file_size_mb * 1024 * 1024:
                logger.warning(
                    f"⚠️ Skipping large file: {file_path} ({file_size / 1024 / 1024:.1f}MB)"
                )
                return []

            # Extract content and metadata
            content, metadata = self._extract_content_and_metadata(file_path)

            if not content or not content.strip():
                logger.warning(f"⚠️ No content extracted from: {file_path}")
                return []

            # Create chunks with enhanced metadata
            chunks = self._create_enhanced_chunks(content, metadata)

            logger.debug(f"🔍 Created {len(chunks)} chunks from {file_path.name}")
            return chunks

        except Exception as e:
            logger.error(f"❌ Error processing {file_path}: {e}")
            if not self.config.skip_corrupted_files:
                raise
            return []

    def _find_supported_files(self, directory: Path) -> List[Path]:
        """Find all supported files in directory recursively"""
        files = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() in self.config.supported_extensions:
                files.append(file_path)

        return sorted(files)

    def _extract_content_and_metadata(
        self, file_path: Path
    ) -> Tuple[str, DocumentMetadata]:
        """Extract content and metadata from file based on type"""
        file_extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        # Initialize metadata
        stat = file_path.stat()
        metadata = DocumentMetadata(
            file_path=str(file_path),
            title=file_path.stem,
            file_type=file_extension[1:] if file_extension else "unknown",
            file_size=stat.st_size,
            mime_type=mime_type or "unknown",
            encoding="utf-8",
            modification_date=datetime.fromtimestamp(stat.st_mtime),
        )

        # Extract content based on file type
        content = ""

        try:
            if file_extension in [".txt", ".md", ".rst"]:
                content = self._extract_text_content(file_path, metadata)
            elif file_extension == ".pdf" and PDF_SUPPORT:
                content = self._extract_pdf_content(file_path, metadata)
            elif file_extension in [".docx", ".doc"] and DOCX_SUPPORT:
                content = self._extract_docx_content(file_path, metadata)
            elif file_extension == ".csv" and CSV_SUPPORT:
                content = self._extract_csv_content(file_path, metadata)
            elif file_extension in [".json"]:
                content = self._extract_json_content(file_path, metadata)
            elif file_extension in [".html", ".htm"]:
                content = self._extract_html_content(file_path, metadata)
            else:
                logger.warning(f"⚠️ Unsupported file type: {file_extension}")
                return "", metadata

            # Calculate content metrics
            metadata.char_count = len(content)
            metadata.word_count = len(content.split()) if content else 0
            metadata.content_hash = hashlib.md5(content.encode()).hexdigest()

        except Exception as e:
            metadata.processing_errors.append(str(e))
            logger.error(f"❌ Content extraction failed for {file_path}: {e}")

        return content, metadata

    def _extract_text_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from text files with encoding detection"""
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                metadata.encoding = encoding
                metadata.extraction_method = "text_direct"
                return content
            except UnicodeDecodeError:
                continue

        # If all encodings fail, read as binary and decode with errors
        with open(file_path, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        metadata.encoding = "utf-8_with_errors"
        metadata.extraction_method = "text_fallback"
        return content

    def _extract_pdf_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from PDF files using multiple methods"""
        content_parts = []

        try:
            # Try PyMuPDF first (better for complex PDFs)
            if PDF_PYMUPDF_SUPPORT:
                doc = fitz.open(str(file_path))
                metadata.page_count = doc.page_count

                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    if text.strip():
                        content_parts.append(text)

                doc.close()
                metadata.extraction_method = "pymupdf"

        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed, trying PyPDF2: {e}")

            # Fallback to PyPDF2
            if PDF_PYPDF2_SUPPORT:
                try:
                    with open(file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        metadata.page_count = len(reader.pages)

                        for page in reader.pages:
                            text = page.extract_text()
                            if text.strip():
                                content_parts.append(text)

                    metadata.extraction_method = "pypdf2"

                except Exception as e2:
                    metadata.processing_errors.append(f"PDF extraction failed: {e2}")
                    return ""
            else:
                metadata.processing_errors.append(f"No PDF library available: {e}")
                return ""

        return "\n\n".join(content_parts)

    def _extract_docx_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from DOCX files"""
        try:
            # Try mammoth for better formatting preservation
            if MAMMOTH_SUPPORT:
                with open(file_path, "rb") as f:
                    result = mammoth.extract_raw_text(f)
                    content = result.value
                    metadata.extraction_method = "mammoth"
                    return content

        except Exception as e:
            logger.warning(f"Mammoth extraction failed, trying docx2txt: {e}")

        # Fallback to docx2txt
        if DOCX2TXT_SUPPORT:
            try:
                content = docx2txt.process(str(file_path))
                metadata.extraction_method = "docx2txt"
                return content
            except Exception as e2:
                metadata.processing_errors.append(f"DOCX extraction failed: {e2}")
                return ""
        else:
            metadata.processing_errors.append("No DOCX library available")
            return ""

    def _extract_csv_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from CSV files"""
        if not CSV_SUPPORT:
            metadata.processing_errors.append("Pandas not available for CSV processing")
            return ""

        try:
            df = pd.read_csv(file_path)

            # Convert to structured text
            content_parts = [f"CSV Data from {file_path.name}"]
            content_parts.append(f"Columns: {', '.join(df.columns)}")
            content_parts.append(f"Rows: {len(df)}")
            content_parts.append("")

            # Add sample rows
            sample_size = min(10, len(df))
            for idx, row in df.head(sample_size).iterrows():
                row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
                content_parts.append(row_text)

            if len(df) > sample_size:
                content_parts.append(f"... and {len(df) - sample_size} more rows")

            metadata.extraction_method = "pandas_csv"
            return "\n".join(content_parts)

        except Exception as e:
            metadata.processing_errors.append(f"CSV extraction failed: {e}")
            return ""

    def _extract_json_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from JSON files"""
        try:
            import json

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert JSON to structured text
            def json_to_text(obj, prefix=""):
                if isinstance(obj, dict):
                    lines = []
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"{prefix}{key}:")
                            lines.extend(json_to_text(value, prefix + "  "))
                        else:
                            lines.append(f"{prefix}{key}: {value}")
                    return lines
                elif isinstance(obj, list):
                    lines = []
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            lines.append(f"{prefix}[{i}]:")
                            lines.extend(json_to_text(item, prefix + "  "))
                        else:
                            lines.append(f"{prefix}[{i}]: {item}")
                    return lines
                else:
                    return [f"{prefix}{obj}"]

            content_lines = [f"JSON Data from {file_path.name}"]
            content_lines.extend(json_to_text(data))

            metadata.extraction_method = "json_structured"
            return "\n".join(content_lines)

        except Exception as e:
            metadata.processing_errors.append(f"JSON extraction failed: {e}")
            return ""

    def _extract_html_content(self, file_path: Path, metadata: DocumentMetadata) -> str:
        """Extract content from HTML files"""
        try:
            if HTML_SUPPORT:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                soup = BeautifulSoup(html_content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extract text
                text = soup.get_text()

                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                content = " ".join(chunk for chunk in chunks if chunk)

                metadata.extraction_method = "beautifulsoup"
                return content
            else:
                # Fallback to simple HTML tag removal
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                import re

                content = re.sub(r"<[^>]+>", "", content)
                content = re.sub(r"\s+", " ", content).strip()

                metadata.extraction_method = "regex_html"
                return content

        except Exception as e:
            metadata.processing_errors.append(f"HTML extraction failed: {e}")
            return ""

    def _create_enhanced_chunks(
        self, content: str, metadata: DocumentMetadata
    ) -> List[DocumentChunk]:
        """Create enhanced chunks with intelligent boundaries and metadata"""
        if not content or not content.strip():
            return []

        chunks = []
        content = content.strip()

        # Intelligent chunking with sentence boundaries
        sentences = self._split_into_sentences(content)

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if (
                len(current_chunk) + len(sentence) + 1 > self.config.chunk_size
                and current_chunk
            ):
                # Create chunk
                chunk = self._create_chunk(
                    current_chunk.strip(),
                    chunk_index,
                    current_start,
                    current_start + len(current_chunk),
                    metadata,
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(
                    current_chunk, self.config.chunk_overlap
                )
                current_chunk = (
                    overlap_text + " " + sentence if overlap_text else sentence
                )
                current_start = (
                    current_start
                    + len(current_chunk)
                    - len(overlap_text)
                    - len(sentence)
                    - 1
                )
                chunk_index += 1
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk.strip(),
                chunk_index,
                current_start,
                current_start + len(current_chunk),
                metadata,
            )
            chunks.append(chunk)

        # Filter out chunks that are too small
        chunks = [
            chunk
            for chunk in chunks
            if len(chunk.content) >= self.config.min_chunk_size
        ]

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using multiple methods"""
        import re

        # Simple sentence splitting with multiple delimiters
        sentences = re.split(r"[.!?]+\s+", text)

        # Clean and filter sentences
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Minimum sentence length
                clean_sentences.append(sentence)

        return clean_sentences

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from the end of current chunk"""
        if len(text) <= overlap_size:
            return text

        # Try to end at a word boundary
        overlap_text = text[-overlap_size:]
        space_index = overlap_text.find(" ")

        if space_index > 0:
            return overlap_text[space_index:].strip()

        return overlap_text

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        metadata: DocumentMetadata,
    ) -> DocumentChunk:
        """Create a DocumentChunk with enhanced metadata"""

        # Generate chunk ID
        chunk_id = f"{metadata.content_hash}_{chunk_index}"

        # Create embedding text (title + content for better embeddings)
        embedding_text = f"{metadata.title}\n\n{content}" if metadata.title else content

        return DocumentChunk(
            chunk_id=chunk_id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata,
            embedding_text=embedding_text,
            chunk_type="content",
            confidence=1.0,
        )

    def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)


async def process_documents_for_seeding(
    docs_path: str, config: ProcessingConfig = None
) -> List[DocumentChunk]:
    """Process documents for seeding pipeline integration."""
    processor = EnhancedDocumentProcessor(config)

    try:
        chunks = await processor.process_directory(docs_path)
        return chunks
    finally:
        processor.cleanup()
