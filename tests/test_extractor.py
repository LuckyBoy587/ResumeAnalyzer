import pytest
from unittest import mock
from src.extractor.extractor import clean_and_normalize_text, extract_text_from_pdf

def test_clean_and_normalize_text():
    raw = "Hello \u201cworld\u201d!\r\nThis is a bullet \u2022 and non-breaking\u00a0space.   Multiple spaces   \n\n\nNew line."
    expected = "Hello \"world\"!\nThis is a bullet * and non-breaking space. Multiple spaces\n\nNew line."
    assert clean_and_normalize_text(raw) == expected

@mock.patch("src.extractor.extractor.fitz.open")
def test_extract_text_from_pdf_mocked(mock_fitz_open):
    # Mocking fitz page and blocks
    mock_doc = mock.MagicMock()
    mock_fitz_open.return_value.__enter__.return_value = mock_doc
    
    mock_page = mock.MagicMock()
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.__len__.return_value = 1
    
    mock_page.rect.width = 600
    # blocks: x0, y0, x1, y1, text, block_no, block_type
    mock_page.get_text.return_value = [
        (50, 100, 250, 150, "Left column text", 0, 0),
        (350, 100, 550, 150, "Right column text", 1, 0),
        (50, 50, 550, 80, "Spanning header text", 2, 0)
    ]
    
    # We pass a fake path
    with mock.patch("src.extractor.extractor.os.path.exists", return_value=True):
        text = extract_text_from_pdf(r"D:\College Theory Stuff\ResumeAnalyzer\data\Resume.pdf")

    assert "Spanning header text" in text
    assert "Left column text" in text
    assert "Right column text" in text
