"""File service for handling file uploads (photos, documents)."""

import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image

from core.config import config
from core.exceptions.base  import ValidationException

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file uploads and storage."""

    def __init__(self):
        """Initialize file service and create upload directories."""
        self.upload_dir = Path(config.UPLOAD_DIR)
        self.photos_dir = self.upload_dir / "photos"
        self.announcements_dir = self.upload_dir / "announcements"
        self.thumbnails_dir = self.upload_dir / "thumbnails"

        # Create directories if they don't exist
        for dir_path in [self.photos_dir, self.announcements_dir, self.thumbnails_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def validate_file(self, file: UploadFile, allowed_types: list[str]) -> None:
        """
        Validate file type.

        Args:
            file: The uploaded file
            allowed_types: List of allowed MIME types

        Raises:
            ValidationException: If file is invalid

        Note: Size validation happens after reading the file content in save methods.
        """
        # Check MIME type
        if file.content_type not in allowed_types:
            raise ValidationException(
                message=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )

    async def save_photo(self, file: UploadFile, class_id: str) -> tuple[str, str, int, int, int]:
        """
        Save photo and create thumbnail.

        Args:
            file: The uploaded image file
            class_id: ID of the class this photo belongs to

        Returns:
            Tuple of (file_path, thumbnail_path, width, height, file_size)

        Raises:
            ValidationException: If file is invalid
        """
        self.validate_file(file, config.ALLOWED_IMAGE_TYPES)

        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        unique_name = f"{uuid4()}{ext}"

        # Class-specific subdirectory
        class_dir = self.photos_dir / class_id
        class_dir.mkdir(parents=True, exist_ok=True)

        # Read and validate size
        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE:
            max_mb = config.MAX_FILE_SIZE / 1024 / 1024
            raise ValidationException(message=f"File too large (max {max_mb:.0f}MB)")

        # Save original
        file_path = class_dir / unique_name
        with open(file_path, "wb") as f:
            f.write(content)

        # Create thumbnail
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if needed (for PNG with transparency)
                if img.mode == "RGBA":
                    img = img.convert("RGB")

                width, height = img.size

                # Create thumbnail (300x300 max, maintaining aspect ratio)
                img.thumbnail((300, 300))
                thumbnail_dir = self.thumbnails_dir / class_id
                thumbnail_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_path = thumbnail_dir / unique_name

                # Save as JPEG for thumbnails (smaller size)
                if ext.lower() == ".png":
                    thumbnail_path = thumbnail_path.with_suffix(".jpg")

                img.save(thumbnail_path, "JPEG", optimize=True, quality=85)

        except Exception as e:
            # Clean up the original file if thumbnail creation fails
            if file_path.exists():
                file_path.unlink()
            logger.error(f"Failed to create thumbnail for {file.filename}: {e}")
            raise ValidationException(message="Failed to process image file")

        # Return relative paths and file size
        return (
            str(file_path.relative_to(self.upload_dir)),
            str(thumbnail_path.relative_to(self.upload_dir)),
            width,
            height,
            len(content),
        )

    async def save_announcement_attachment(self, file: UploadFile) -> str:
        """
        Save announcement attachment (PDF or image).

        Args:
            file: The uploaded file

        Returns:
            Relative file path

        Raises:
            ValidationException: If file is invalid
        """
        allowed = config.ALLOWED_IMAGE_TYPES + config.ALLOWED_DOCUMENT_TYPES
        self.validate_file(file, allowed)

        # Generate unique filename
        ext = Path(file.filename).suffix.lower()
        unique_name = f"{uuid4()}{ext}"

        # Read and validate size
        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE:
            max_mb = config.MAX_FILE_SIZE / 1024 / 1024
            raise ValidationException(message=f"File too large (max {max_mb:.0f}MB)")

        # Save file
        file_path = self.announcements_dir / unique_name
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved announcement attachment: {unique_name}")

        return str(file_path.relative_to(self.upload_dir))

    async def delete_file(self, relative_path: str) -> None:
        """
        Delete a file.

        Args:
            relative_path: Path relative to upload directory
        """
        full_path = self.upload_dir / relative_path
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted file: {relative_path}")
        else:
            logger.warning(f"File not found for deletion: {relative_path}")

    async def delete_photo(self, file_path: str, thumbnail_path: Optional[str]) -> None:
        """
        Delete photo and its thumbnail.

        Args:
            file_path: Photo file path (relative to upload directory)
            thumbnail_path: Thumbnail path (relative to upload directory)
        """
        await self.delete_file(file_path)
        if thumbnail_path:
            await self.delete_file(thumbnail_path)


def get_file_service() -> FileService:
    """Get file service instance (dependency injection)."""
    return FileService()
