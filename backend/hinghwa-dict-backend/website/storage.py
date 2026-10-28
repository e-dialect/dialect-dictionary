# -*-coding:utf-8-*-
import os
import shutil
from pathlib import Path
from urllib.parse import quote

import requests
from django.conf import settings
from qcloud_cos import CosConfig, CosS3Client


class FileTooLargeError(ValueError):
    pass


def validate_file_size(file):
    max_size = settings.MAX_UPLOAD_SIZE
    if file.size > max_size:
        raise FileTooLargeError(f"文件不能超过 {max_size} 字节")


def upload_file(path, key):
    if getattr(settings, "FILE_STORAGE", "cos") == "local":
        target = _local_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        return settings.PUBLIC_API_BASE.rstrip("/") + "/media/" + quote(key, safe="/")
    config = CosConfig(
        Region=settings.COS_REGION,
        SecretId=settings.COS_SECRET_ID,
        SecretKey=settings.COS_SECRET_KEY,
    )
    client = CosS3Client(config)
    response = client.upload_file(
        Bucket=settings.COS_BUCKET, LocalFilePath=path, Key=key
    )
    base = getattr(settings, "COS_PUBLIC_BASE_URL", "")
    if not base:
        raise ValueError("COS_PUBLIC_BASE_URL must be configured for cloud storage")
    return base.rstrip("/") + "/" + quote(key, safe="/")


def _local_path(key):
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / key).resolve()
    if not key or target == root or not target.is_relative_to(root):
        raise ValueError(
            "storage key must remain inside this dictionary's media directory"
        )
    return target


def delete_file(key):
    if getattr(settings, "FILE_STORAGE", "cos") == "local":
        _local_path(key).unlink(missing_ok=True)
        return
    config = CosConfig(
        Region=settings.COS_REGION,
        SecretId=settings.COS_SECRET_ID,
        SecretKey=settings.COS_SECRET_KEY,
    )
    client = CosS3Client(config)
    client.delete_object(Bucket=settings.COS_BUCKET, Key=key)


def download_file(url, type, user_id, filename):
    path = None
    response = None
    try:
        folder = os.path.join(settings.MEDIA_ROOT, type, user_id)
        if not os.path.exists(folder):
            os.makedirs(folder)
        path = os.path.join(folder, filename)
        response = requests.get(url, stream=True, timeout=(5, 30))
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(f"文件不能超过 {settings.MAX_UPLOAD_SIZE} 字节")
        downloaded = 0
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > settings.MAX_UPLOAD_SIZE:
                    raise FileTooLargeError(
                        f"文件不能超过 {settings.MAX_UPLOAD_SIZE} 字节"
                    )
                f.write(chunk)
        key = f'files/{type}/{user_id}/{filename.replace("_", "/")}'
        url = upload_file(path, key)
        return url
    except Exception as e:
        if path and os.path.exists(path):
            os.remove(path)
        print("Error occurred when downloading file, error message:")
        print(e)
        return None
    finally:
        if response is not None:
            response.close()
