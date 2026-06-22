import os
import re
import fitz  # PyMuPDF
import logging
import uuid
from typing import Optional
from src.downloader.downloader import download_file_from_url

logger = logging.getLogger(__name__)

def extract_text_with_spatial_bounds(pdf_path: str) -> str:
    """
    Extracts raw text from a PDF file using spatial layout analysis to preserve
    multi-column reading flows and text grid alignments.

    Args:
        pdf_path (str): The local path or remote URL to the PDF.

    Returns:
        str: Extracted text with layout preserved.
    """
    is_url = pdf_path.startswith("http://") or pdf_path.startswith("https://")
    local_path = pdf_path

    if is_url:
        # Create a unique temporary filename to prevent concurrency issues
        temp_filename = f"temp_{uuid.uuid4().hex}.pdf"
        logger.info(f"Generating temporary file name for URL download: {temp_filename}")
        local_path = download_file_from_url(pdf_path, output_path=temp_filename)

    try:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Target document not found at: {local_path}")

        logger.info(f"Beginning PDF extraction for: {local_path}")
        text_parts = []
        with fitz.open(local_path) as doc:
            logger.info(f"PDF opened successfully. Pages count: {len(doc)}")
            for page_num, page in enumerate(doc, 1):
                rect = page.rect
                width = rect.width

                # Get text blocks
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0]

                # Find split_x dynamically by minimizing the number of blocks that straddle it
                mid_x = width / 2
                if text_blocks:
                    start_x = int(width * 0.25)
                    end_x = int(width * 0.75)
                    straddle_counts = {}
                    for x in range(start_x, end_x + 1, 2):
                        count = 0
                        for b in text_blocks:
                            x0, _, x1, _, _, _, _ = b
                            if x0 < x - 2 and x1 > x + 2:
                                count += 1
                        straddle_counts[x] = count

                    if straddle_counts:
                        min_count = min(straddle_counts.values())
                        best_xs = [x for x, c in straddle_counts.items() if c == min_count]
                        
                        # Group continuous sequences of X values
                        runs = []
                        current_run = []
                        for x in sorted(best_xs):
                            if not current_run or x == current_run[-1] + 2:
                                current_run.append(x)
                            else:
                                runs.append(current_run)
                                current_run = [x]
                        if current_run:
                            runs.append(current_run)

                        # Use midpoint of the widest gutter run
                        longest_run = max(runs, key=len)
                        mid_x = sum(longest_run) / len(longest_run)

                # Identify spanning blocks (horizontal dividers across the midline)
                spanning_blocks = []
                for b in text_blocks:
                    x0, y0, x1, y1, _, _, _ = b
                    if x0 < mid_x - 30 and x1 > mid_x + 30:
                        spanning_blocks.append(b)

                spanning_blocks.sort(key=lambda x: x[1])

                # Helper to assign block zones and columns
                def get_block_location(b):
                    x0, y0, x1, y1, _, _, _ = b
                    for idx, sb in enumerate(spanning_blocks):
                        if b == sb:
                            return (idx * 2 + 1, 0, y0)

                    zone_idx = 0
                    for idx, sb in enumerate(spanning_blocks):
                        if y0 >= sb[3] - 5:
                            zone_idx = (idx + 1) * 2

                    if x1 <= mid_x + 15:
                        col = 0
                    elif x0 >= mid_x - 15:
                        col = 1
                    else:
                        col = 2
                    return (zone_idx, col, y0)

                # Group text blocks into zone bins
                zone_blocks = {}
                for b in text_blocks:
                    loc = get_block_location(b)
                    z_idx = loc[0]
                    if z_idx not in zone_blocks:
                        zone_blocks[z_idx] = []
                    zone_blocks[z_idx].append(b)

                # Sort each zone dynamically based on its structural characteristics
                for z_idx in sorted(zone_blocks.keys()):
                    z_list = zone_blocks[z_idx]
                    if z_idx % 2 == 1:
                        z_list.sort(key=lambda x: (x[1], x[0]))
                    else:
                        has_two_columns = False
                        lefts = [b for b in z_list if b[2] <= mid_x + 15]
                        rights = [b for b in z_list if b[0] >= mid_x - 15]

                        if lefts and rights:
                            for l in lefts:
                                for r in rights:
                                    overlap = min(l[3], r[3]) - max(l[1], r[1])
                                    h_l = l[3] - l[1]
                                    h_r = r[3] - r[1]
                                    if overlap > 0.3 * min(h_l, h_r):
                                        has_two_columns = True
                                        break
                                if has_two_columns:
                                    break

                        if has_two_columns:
                            def col_sort_key(b):
                                x0, y0, x1, _, _, _, _ = b
                                col = 0 if x1 <= mid_x + 15 else (1 if x0 >= mid_x - 15 else 2)
                                return col, y0

                            z_list.sort(key=col_sort_key)
                        else:
                            z_list.sort(key=lambda x: (x[1], x[0]))

                    for b in z_list:
                        text_parts.append(b[4].strip())
                        
            logger.info(f"Completed extraction of pages. Total blocks collected: {len(text_parts)}")

        return "\n".join(text_parts)
    finally:
        if is_url and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Cleaned up temporary downloaded PDF at: {local_path}")
            except Exception as e:
                logger.warning(f"Could not remove temporary file {local_path}: {e}")


def clean_and_normalize_text(raw_text: str) -> str:
    """
    Cleans raw layout text: strips system artifacts, filters layout noise,
    and normalizes whitespaces/unicode representations.

    Args:
        raw_text (str): The raw text extracted from PDF.

    Returns:
        str: Cleaned and normalized text.
    """
    if not raw_text:
        return ""

    replacements = {
        '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'",
        '\u2013': '-', '\u2014': '-',
        '\u2022': '*', '\u2027': '*',
        '\u00a0': ' ',
        '\r\n': '\n', '\r': '\n'
    }

    cleaned = raw_text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch in ('\n', '\t'))
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    lines = [line.strip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)

    return cleaned.strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Wrapper calling spatial layout extraction and text normalization pre-filtering.

    Args:
        pdf_path (str): The local path or remote URL to the PDF.

    Returns:
        str: Cleaned text content.
    """
    raw_text = extract_text_with_spatial_bounds(pdf_path)
    return clean_and_normalize_text(raw_text)
