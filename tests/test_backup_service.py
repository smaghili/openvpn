import io
import os
import sys
import tarfile
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.backup_service import BackupService
from core.exceptions import RestoreError


def test_safe_extract_prevents_path_traversal(tmp_path):
    malicious_tar = tmp_path / "mal.tar.gz"
    with tarfile.open(malicious_tar, "w:gz") as tar:
        info = tarfile.TarInfo(name="../evil.txt")
        data = b"hello"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    service = BackupService([])
    with tarfile.open(malicious_tar, "r:gz") as tar:
        with pytest.raises(RestoreError):
            service._safe_extract(tar, path=tmp_path)


def test_safe_extract_valid(tmp_path):
    good_tar = tmp_path / "good.tar.gz"
    with tarfile.open(good_tar, "w:gz") as tar:
        info = tarfile.TarInfo(name="good.txt")
        data = b"hi"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    service = BackupService([])
    with tarfile.open(good_tar, "r:gz") as tar:
        service._safe_extract(tar, path=tmp_path)

    assert (tmp_path / "good.txt").read_text() == "hi"
