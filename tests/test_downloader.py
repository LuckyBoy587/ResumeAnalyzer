import os
import pytest
from unittest import mock
from src.downloader.downloader import download_file_from_url

def test_download_file_local_exists(tmp_path):
    # If file exists locally, it should return the path directly
    local_file = tmp_path / "test_resume.pdf"
    local_file.write_text("dummy pdf content")
    
    result = download_file_from_url(str(local_file))
    assert result == str(local_file)

def test_download_file_invalid_schema():
    # Invalid local path and not a URL should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        download_file_from_url("non_existent_file.pdf")
    assert "File path does not exist locally and is not a valid URL" in str(excinfo.value)

@mock.patch("src.downloader.downloader.requests.get")
def test_download_file_direct_url(mock_get, tmp_path):
    output_path = str(tmp_path / "downloaded.pdf")
    mock_response = mock.Mock()
    mock_response.iter_content.return_value = [b"pdf_chunk1", b"pdf_chunk2"]
    mock_response.raise_for_status = mock.Mock()
    mock_get.return_value = mock_response

    result = download_file_from_url("https://example.com/resume.pdf", output_path=output_path)
    assert result == output_path
    assert os.path.exists(output_path)
    with open(output_path, "rb") as f:
        assert f.read() == b"pdf_chunk1pdf_chunk2"

@mock.patch("src.downloader.downloader.requests.Session")
def test_download_file_google_drive(mock_session_class, tmp_path):
    output_path = str(tmp_path / "downloaded_gdrive.pdf")
    mock_session = mock.Mock()
    mock_session_class.return_value = mock_session
    
    mock_response = mock.Mock()
    mock_response.cookies = {}
    mock_response.iter_content.return_value = [b"gdrive_chunk"]
    mock_response.raise_for_status = mock.Mock()
    
    mock_session.get.return_value = mock_response

    url = "https://drive.google.com/file/d/1C8svOrGqiFxDFD8IfNid2sAFG54VOdva/view"
    result = download_file_from_url(url, output_path=output_path)
    assert result == output_path
    assert os.path.exists(output_path)
    with open(output_path, "rb") as f:
        assert f.read() == b"gdrive_chunk"

@mock.patch("src.downloader.downloader.requests.get")
def test_download_file_github_rewrite(mock_get, tmp_path):
    output_path = str(tmp_path / "downloaded_github.pdf")
    mock_response = mock.Mock()
    mock_response.iter_content.return_value = [b"github_chunk"]
    mock_response.raise_for_status = mock.Mock()
    mock_get.return_value = mock_response

    url = "https://github.com/user/repo/blob/main/resume.pdf"
    result = download_file_from_url(url, output_path=output_path)
    assert result == output_path
    
    # Verify github url rewrite happened
    mock_get.assert_called_with("https://raw.githubusercontent.com/user/repo/main/resume.pdf", stream=True)

@mock.patch("src.downloader.downloader.requests.get")
def test_download_file_failure(mock_get):
    mock_get.side_effect = Exception("Connection error")
    with pytest.raises(Exception):
        download_file_from_url("https://example.com/resume.pdf")
