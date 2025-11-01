import pdfplumber
from pypdf import PdfReader
from typing import List, Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobustPDFProcessor:
    """
    Multi-strategy PDF processor with fallback mechanisms
    Uses pdfplumber as primary and pypdf as fallback
    """
    
    @staticmethod
    def extract_with_pdfplumber(pdf_path: str) -> Optional[str]:
        """Primary method using pdfplumber - best for complex PDFs"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n"
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue
            
            return text if text.strip() else None
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_with_pdfplumber_layout(pdf_path: str) -> Optional[str]:
        """Alternative pdfplumber method preserving layout"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Use layout mode for better structure preservation
                        page_text = page.extract_text(layout=True)
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n"
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1} with layout: {e}")
                        continue
            
            return text if text.strip() else None
        except Exception as e:
            logger.warning(f"pdfplumber layout extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_with_pypdf(pdf_path: str) -> Optional[str]:
        """Fallback method using pypdf - works with damaged PDFs"""
        try:
            # Non-strict mode handles EOF and other errors
            reader = PdfReader(pdf_path, strict=False)
            text = ""
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                    continue
            
            return text if text.strip() else None
        except Exception as e:
            logger.warning(f"pypdf extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_with_pypdf_recovery(pdf_path: str) -> Optional[str]:
        """Last resort - pypdf with maximum error recovery"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file, strict=False)
                text = ""
                
                # Try to read metadata
                try:
                    if reader.metadata:
                        text += "--- Document Metadata ---\n"
                        for key, value in reader.metadata.items():
                            text += f"{key}: {value}\n"
                        text += "\n"
                except:
                    pass
                
                # Extract text from pages
                for page_num in range(len(reader.pages)):
                    try:
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n"
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Recovery mode failed on page {page_num + 1}: {e}")
                        text += f"\n--- Page {page_num + 1} (Recovery Failed) ---\n"
                        continue
                
                return text if text.strip() else None
        except Exception as e:
            logger.warning(f"pypdf recovery extraction failed: {e}")
            return None
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text with multiple fallback strategies
        Tries 4 different methods in order
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Starting PDF extraction for: {pdf_path}")
        
        # Try methods in order of reliability for complex PDFs
        methods = [
            ("pdfplumber (default)", self.extract_with_pdfplumber),
            ("pdfplumber (layout)", self.extract_with_pdfplumber_layout),
            ("pypdf (non-strict)", self.extract_with_pypdf),
            ("pypdf (recovery)", self.extract_with_pypdf_recovery),
        ]
        
        for method_name, method in methods:
            logger.info(f"Trying extraction with {method_name}...")
            try:
                text = method(pdf_path)
                if text and len(text.strip()) > 50:  # Minimum content threshold
                    logger.info(f"✅ Successfully extracted with {method_name}")
                    logger.info(f"   Extracted {len(text)} characters")
                    return text
                else:
                    logger.warning(f"   Insufficient content extracted")
            except Exception as e:
                logger.error(f"   Exception in {method_name}: {e}")
                continue
        
        raise ValueError(
            "Failed to extract text from PDF with all methods. "
            "The PDF might be image-based, encrypted, or severely corrupted."
        )
    
    def chunk_text(self, text: str, chunk_size: int = 1000, 
                   overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks with smart boundary detection
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at natural boundaries
            if end < text_length:
                # Look for paragraph breaks first
                last_double_newline = chunk.rfind('\n\n')
                # Then sentence breaks
                last_period = chunk.rfind('. ')
                last_question = chunk.rfind('? ')
                last_exclamation = chunk.rfind('! ')
                # Then any newline
                last_newline = chunk.rfind('\n')
                
                # Choose the best break point
                break_points = [
                    last_double_newline,
                    max(last_period, last_question, last_exclamation),
                    last_newline
                ]
                
                for break_point in break_points:
                    if break_point > chunk_size * 0.5:  # At least 50% of chunk
                        chunk = chunk[:break_point + 1]
                        end = start + break_point + 1
                        break
            
            chunk_stripped = chunk.strip()
            if chunk_stripped:
                chunks.append(chunk_stripped)
            
            start = end - overlap
        
        logger.info(f"Created {len(chunks)} chunks from {text_length} characters")
        return chunks
    
    def extract_tables(self, pdf_path: str) -> List[dict]:
        """
        Extract tables from PDF using pdfplumber
        Returns list of tables as dictionaries
        """
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table_num, table in enumerate(page_tables):
                        tables.append({
                            "page": page_num + 1,
                            "table_number": table_num + 1,
                            "data": table
                        })
            logger.info(f"Extracted {len(tables)} tables from PDF")
        except Exception as e:
            logger.error(f"Failed to extract tables: {e}")
        
        return tables
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get PDF metadata and information
        """
        info = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                info['pages'] = len(pdf.pages)
                info['metadata'] = pdf.metadata
                
                # Get first page dimensions
                if pdf.pages:
                    first_page = pdf.pages[0]
                    info['page_width'] = first_page.width
                    info['page_height'] = first_page.height
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            info['error'] = str(e)
        
        return info