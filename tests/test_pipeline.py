import pytest
from unittest import mock
from src.pipeline.resume_parser import parse_resume

@mock.patch("src.pipeline.resume_parser.detect_file_type")
@mock.patch("src.pipeline.resume_parser.download_file_from_url")
@mock.patch("src.pipeline.resume_parser.extract_text_from_pdf")
@mock.patch("src.pipeline.resume_parser.parse_resume_to_entities")
def test_parse_resume_pipeline_url(
    mock_parse_entities,
    mock_extract_text,
    mock_download,
    mock_detect_type,
    tmp_path
):
    # Mock return values
    mock_detect_type.return_value = "pdf"
    mock_download.return_value = str(tmp_path / "temp_downloaded.pdf")
    mock_extract_text.return_value = "Extracted text content"
    mock_parse_entities.return_value = {"skills": ["Python"]}
    
    # We call with a URL
    result = parse_resume("https://example.com/resume.pdf")
    
    assert result == {"skills": ["Python"]}
    mock_download.assert_called_once()
    mock_extract_text.assert_called_once_with(mock_download.return_value)
    mock_parse_entities.assert_called_once_with(mock_download.return_value, clean_text="Extracted text content")

@mock.patch("src.pipeline.resume_parser.detect_file_type")
@mock.patch("src.pipeline.resume_parser.extract_text_from_pdf")
@mock.patch("src.pipeline.resume_parser.parse_resume_to_entities")
def test_parse_resume_pipeline_local(
    mock_parse_entities,
    mock_extract_text,
    mock_detect_type,
    tmp_path
):
    # Mock return values
    mock_detect_type.return_value = "pdf"
    mock_extract_text.return_value = "Extracted local text content"
    mock_parse_entities.return_value = {"skills": ["Java"]}
    
    local_file = str(tmp_path / "local_resume.pdf")
    
    # Mock download shouldn't be called for local files
    with mock.patch("src.pipeline.resume_parser.download_file_from_url") as mock_download:
        result = parse_resume(local_file)
        mock_download.assert_not_called()
        
    assert result == {"skills": ["Java"]}
    mock_extract_text.assert_called_once_with(local_file)
    mock_parse_entities.assert_called_once_with(local_file, clean_text="Extracted local text content")

@mock.patch("src.pipeline.resume_parser.detect_file_type")
def test_parse_resume_invalid_file_type(mock_detect_type):
    mock_detect_type.return_value = "docx"
    
    with pytest.raises(ValueError) as excinfo:
        parse_resume("dummy_path.docx")
    assert "Unsupported file type: DOCX" in str(excinfo.value)
