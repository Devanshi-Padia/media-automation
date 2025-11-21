import os
import shutil
import uuid
import base64
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
import mimetypes
from PIL import Image, ImageEnhance, ImageFilter
import io
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
try:
    from moviepy import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from ...models.media import MediaLibrary, MediaFile, MediaCollection, MediaCollectionItem, ProjectMedia, MediaEdit
from ...models.project import Project
import logging

logger = logging.getLogger(__name__)

class MediaManagementService:
    """Comprehensive media management service for handling images and videos stored in database"""
    
    def __init__(self):
        # No file system directories needed for database storage
        pass
    
    async def create_user_library(self, db: AsyncSession, user_id: int, name: str = "My Media Library") -> MediaLibrary:
        """Create a default media library for a user"""
        library = MediaLibrary(
            user_id=user_id,
            name=name,
            description="Default media library",
            created_at=datetime.utcnow(),
            updated_at=None
        )
        db.add(library)
        await db.commit()
        await db.refresh(library)
        return library
    
    async def get_user_library(self, db: AsyncSession, user_id: int) -> Optional[MediaLibrary]:
        """Get user's default media library"""
        result = await db.execute(
            select(MediaLibrary).where(MediaLibrary.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    def _encode_file_to_base64(self, file_data: bytes) -> str:
        """Encode file data to base64 string"""
        return base64.b64encode(file_data).decode('utf-8')
    
    def _decode_base64_to_file(self, base64_data: str) -> bytes:
        """Decode base64 string to file data"""
        return base64.b64decode(base64_data.encode('utf-8'))
    
    async def upload_media_file(
        self, 
        db: AsyncSession, 
        user_id: int, 
        file_data: bytes, 
        original_filename: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> MediaFile:
        """Upload and process a media file (image or video) to database"""
        
        print(f"[DEBUG] === UPLOAD_MEDIA_FILE FUNCTION STARTED ===")
        print(f"[DEBUG] Starting upload_media_file for user {user_id}")
        print(f"[DEBUG] Original filename: {original_filename}")
        print(f"[DEBUG] File data size: {len(file_data)} bytes")
        print(f"[DEBUG] Title: {title}")
        print(f"[DEBUG] Description: {description}")
        print(f"[DEBUG] Tags: {tags}")
        
        # Determine file type and mime type
        mime_type, _ = mimetypes.guess_type(original_filename)
        file_type = "image" if mime_type and mime_type.startswith("image/") else "video"
        
        print(f"[DEBUG] Determined file type: {file_type}, mime_type: {mime_type}")
        
        # Encode file data to base64
        file_data_base64 = self._encode_file_to_base64(file_data)
        print(f"[DEBUG] File encoded to base64, size: {len(file_data_base64)} characters")
        
        # Get or create user library
        print(f"[DEBUG] Getting user library...")
        try:
            library = await self.get_user_library(db, user_id)
            if not library:
                print(f"[DEBUG] Creating user library...")
                library = await self.create_user_library(db, user_id)
        except Exception as e:
            print(f"[DEBUG] Error with library: {e}")
            raise
        
        # Process media file to get metadata
        print(f"[DEBUG] Processing media file...")
        try:
            metadata = await self._process_media_file_db(file_data, file_type)
            print(f"[DEBUG] Media processing completed")
        except Exception as e:
            print(f"[DEBUG] Error processing media: {e}")
            raise
        
        # Create thumbnail
        print(f"[DEBUG] Creating thumbnail...")
        try:
            thumbnail_data = await self._create_thumbnail_db(file_data, file_type)
            thumbnail_base64 = self._encode_file_to_base64(thumbnail_data) if thumbnail_data else None
            print(f"[DEBUG] Thumbnail created, size: {len(thumbnail_data) if thumbnail_data else 0} bytes")
        except Exception as e:
            print(f"[DEBUG] Error creating thumbnail: {e}")
            thumbnail_base64 = None
        
        # Create media file record
        print(f"[DEBUG] Creating media file record...")
        try:
            media_file = MediaFile(
                library_id=library.id,
                filename=original_filename,
                title=title or original_filename,
                description=description,
                file_type=file_type,
                mime_type=mime_type,
                file_data=file_data_base64,
                file_size=len(file_data),
                width=metadata.get('width'),
                height=metadata.get('height'),
                duration=metadata.get('duration'),
                thumbnail_data=thumbnail_base64,
                thumbnail_size=len(thumbnail_data) if thumbnail_data else None,
                file_metadata=metadata,
                tags={"tags": tags or []},
                created_at=datetime.utcnow(),
                updated_at=None,
                library=library,
                collections=[],
                projects=[],
                edits=[]
            )
            
            db.add(media_file)
            await db.commit()
            await db.refresh(media_file)
            
            print(f"[DEBUG] Media file created with ID: {media_file.id}")
            return media_file
            
        except Exception as e:
            print(f"[DEBUG] Error creating media file record: {e}")
            await db.rollback()
            raise
    
    async def _process_media_file_db(self, file_data: bytes, file_type: str) -> Dict[str, Any]:
        """Process media file to extract properties and create thumbnails (in-memory)"""
        properties = {}
        try:
            if file_type == "image":
                with Image.open(io.BytesIO(file_data)) as img:
                    properties["width"] = img.width
                    properties["height"] = img.height
                    
                    # Create thumbnail (in-memory)
                    thumbnail_data = await self._create_thumbnail_db(file_data, file_type)
                    properties["thumbnail_data"] = self._encode_file_to_base64(thumbnail_data) if thumbnail_data else None
                    properties["thumbnail_size"] = len(thumbnail_data) if thumbnail_data else None
                    
            else:  # video
                if MOVIEPY_AVAILABLE:
                    # Use moviepy for video processing
                    with VideoFileClip(io.BytesIO(file_data)) as video:
                        properties["width"] = int(video.w)
                        properties["height"] = int(video.h)
                        properties["duration"] = video.duration
                        
                        # Create video thumbnail (in-memory)
                        thumbnail_data = await self._create_thumbnail_db(file_data, file_type)
                        properties["thumbnail_data"] = self._encode_file_to_base64(thumbnail_data) if thumbnail_data else None
                        properties["thumbnail_size"] = len(thumbnail_data) if thumbnail_data else None
                else:
                    # Fallback for when moviepy is not available
                    logger.warning("MoviePy not available, using basic video properties")
                    properties["width"] = None
                    properties["height"] = None
                    properties["duration"] = None
                    properties["thumbnail_data"] = None
                    properties["thumbnail_size"] = None
                    
        except Exception as e:
            logger.error(f"Error processing media file in DB: {e}")
            properties = {"width": None, "height": None, "duration": None, "thumbnail_data": None, "thumbnail_size": None}
        
        return properties
    
    async def _create_thumbnail_db(self, file_data: bytes, file_type: str) -> Optional[bytes]:
        """Create thumbnail for image or video (in-memory)"""
        try:
            if file_type == "image":
                # For images, use PIL to create thumbnail
                image = Image.open(io.BytesIO(file_data))
                
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                # Create thumbnail
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                
                # Convert to bytes
                thumbnail_bytes = io.BytesIO()
                image.save(thumbnail_bytes, "JPEG", quality=85)
                return thumbnail_bytes.getvalue()
                
            elif file_type == "video":
                # For videos, try to use MoviePy if available
                if not MOVIEPY_AVAILABLE:
                    logger.warning("MoviePy not available, cannot create video thumbnail")
                    return None
                    
                # Use moviepy to extract frame at 1 second
                with VideoFileClip(io.BytesIO(file_data)) as video:
                    # Extract frame at 1 second or middle of video
                    frame_time = min(1.0, video.duration / 2)
                    frame = video.get_frame(frame_time)
                    
                    # Convert numpy array to PIL Image
                    frame_img = Image.fromarray(frame)
                    
                    # Resize to thumbnail size
                    frame_img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                    
                    # Convert PIL Image to bytes
                    thumbnail_bytes = io.BytesIO()
                    frame_img.save(thumbnail_bytes, "JPEG", quality=85)
                    return thumbnail_bytes.getvalue()
            
            return None
                
        except Exception as e:
            logger.error(f"Error creating thumbnail in DB: {e}")
            return None
    
    async def get_user_media_files(
        self, 
        db: AsyncSession, 
        user_id: int, 
        file_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MediaFile]:
        """Get user's media files with optional filtering"""
        query = select(MediaFile).join(MediaLibrary).where(MediaLibrary.user_id == user_id)
        
        if file_type:
            query = query.where(MediaFile.file_type == file_type)
        
        query = query.order_by(MediaFile.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_media_file(self, db: AsyncSession, media_file_id: int, user_id: int) -> Optional[MediaFile]:
        """Get specific media file with user ownership check"""
        print(f"[DEBUG] Service: Getting media file {media_file_id} for user {user_id}")
        
        try:
            result = await db.execute(
                select(MediaFile)
                .join(MediaLibrary)
                .where(
                    and_(
                        MediaFile.id == media_file_id,
                        MediaLibrary.user_id == user_id
                    )
                )
            )
            media_file = result.scalar_one_or_none()
            print(f"[DEBUG] Service: Media file found: {media_file is not None}")
            if media_file:
                print(f"[DEBUG] Service: Media file ID: {media_file.id}, Title: {media_file.title}")
            return media_file
        except Exception as e:
            print(f"[DEBUG] Service: Error in get_media_file: {e}")
            raise
    
    async def edit_media_file(
        self,
        db: AsyncSession,
        media_file_id: int,
        user_id: int,
        edit_type: str,
        edit_params: Dict[str, Any]
    ) -> Optional[MediaFile]:
        """Edit a media file (crop, resize, apply filters, etc.)"""
        print(f"[DEBUG] === EDIT_MEDIA_FILE STARTED ===")
        print(f"[DEBUG] Media file ID: {media_file_id}, User ID: {user_id}")
        print(f"[DEBUG] Edit type: {edit_type}, Edit params: {edit_params}")
        
        # Get media file
        media_file = await self.get_media_file(db, media_file_id, user_id)
        if not media_file:
            print(f"[DEBUG] Media file not found")
            return None
        
        print(f"[DEBUG] Media file found: ID={media_file.id}, Title={media_file.title}")
        print(f"[DEBUG] File type: {media_file.file_type}")
        print(f"[DEBUG] File data size: {len(media_file.file_data)} characters")
        
        try:
            # Decode base64 file data to bytes
            print(f"[DEBUG] Decoding base64 file data...")
            file_data_bytes = self._decode_base64_to_file(media_file.file_data)
            print(f"[DEBUG] Decoded file size: {len(file_data_bytes)} bytes")
            
            # Create edited version
            print(f"[DEBUG] Applying edit...")
            edited_bytes = await self._apply_edit(file_data_bytes, edit_type, edit_params)
            
            if not edited_bytes:
                print(f"[DEBUG] Edit failed - no edited bytes returned")
                return None
            
            print(f"[DEBUG] Edit successful - edited bytes size: {len(edited_bytes)} bytes")
            
            # Update media file directly with edited version
            print(f"[DEBUG] Updating media file...")
            media_file.file_data = self._encode_file_to_base64(edited_bytes)
            media_file.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(media_file)
            print(f"[DEBUG] Media file updated successfully")
            
            return media_file
            
        except Exception as e:
            print(f"[DEBUG] Error in edit_media_file: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            raise
    
    async def _apply_edit(self, file_data: bytes, edit_type: str, edit_params: Dict[str, Any]) -> Optional[bytes]:
        """Apply edit to media file"""
        print(f"[DEBUG] === APPLY_EDIT STARTED ===")
        print(f"[DEBUG] Edit type: {edit_type}")
        print(f"[DEBUG] Edit params: {edit_params}")
        print(f"[DEBUG] Input file size: {len(file_data)} bytes")
        
        try:
            if edit_type == "crop":
                print(f"[DEBUG] Applying crop edit...")
                return await self._crop_image(file_data, edit_params)
            elif edit_type == "resize":
                print(f"[DEBUG] Applying resize edit...")
                return await self._resize_image(file_data, edit_params)
            elif edit_type == "filter":
                print(f"[DEBUG] Applying filter edit...")
                return await self._apply_filter(file_data, edit_params)
            elif edit_type == "brightness":
                print(f"[DEBUG] Applying brightness edit...")
                return await self._adjust_brightness(file_data, edit_params)
            elif edit_type == "contrast":
                print(f"[DEBUG] Applying contrast edit...")
                return await self._adjust_contrast(file_data, edit_params)
            elif edit_type == "trim":
                print(f"[DEBUG] Applying trim edit...")
                return await self._trim_video(file_data, edit_params)
            else:
                print(f"[DEBUG] Unknown edit type: {edit_type}")
                logger.warning(f"Unknown edit type: {edit_type}")
                return None
                
        except Exception as e:
            print(f"[DEBUG] Error in _apply_edit: {e}")
            logger.error(f"Error applying edit {edit_type}: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return None
    
    async def _crop_image(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Crop image"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                left = params.get("left", 0)
                top = params.get("top", 0)
                right = params.get("right", img.width)
                bottom = params.get("bottom", img.height)
                
                cropped = img.crop((left, top, right, bottom))
                
                # Save edited version (in-memory)
                edited_bytes = io.BytesIO()
                cropped.save(edited_bytes, "JPEG", quality=85)
                return edited_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Error cropping image: {e}")
            return None
    
    async def _resize_image(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Resize image"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                width = params.get("width", img.width)
                height = params.get("height", img.height)
                
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                
                # Save edited version (in-memory)
                edited_bytes = io.BytesIO()
                resized.save(edited_bytes, "JPEG", quality=85)
                return edited_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return None
    
    async def _apply_filter(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Apply filter to image"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                filter_type = params.get("filter_type", "blur")
                
                if filter_type == "blur":
                    filtered = img.filter(ImageFilter.BLUR)
                elif filter_type == "sharpen":
                    filtered = img.filter(ImageFilter.SHARPEN)
                elif filter_type == "emboss":
                    filtered = img.filter(ImageFilter.EMBOSS)
                elif filter_type == "edge_enhance":
                    filtered = img.filter(ImageFilter.EDGE_ENHANCE)
                else:
                    filtered = img
                
                # Save edited version (in-memory)
                edited_bytes = io.BytesIO()
                filtered.save(edited_bytes, "JPEG", quality=85)
                return edited_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Error applying filter: {e}")
            return None
    
    async def _adjust_brightness(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Adjust image brightness"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                factor = params.get("factor", 1.0)
                enhancer = ImageEnhance.Brightness(img)
                adjusted = enhancer.enhance(factor)
                
                # Save edited version (in-memory)
                edited_bytes = io.BytesIO()
                adjusted.save(edited_bytes, "JPEG", quality=85)
                return edited_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Error adjusting brightness: {e}")
            return None
    
    async def _adjust_contrast(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Adjust contrast of image"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                factor = params.get("factor", 1.0)
                
                # Convert to numpy array for contrast adjustment
                import numpy as np
                img_array = np.array(img)
                
                # Apply contrast adjustment
                adjusted = np.clip(img_array * factor, 0, 255).astype(np.uint8)
                adjusted_img = Image.fromarray(adjusted)
                
                # Save edited version (in-memory)
                edited_bytes = io.BytesIO()
                adjusted_img.save(edited_bytes, "JPEG", quality=85)
                return edited_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Error adjusting contrast: {e}")
            return None
    
    async def _trim_video(self, file_data: bytes, params: Dict[str, Any]) -> Optional[bytes]:
        """Trim video to specified start and end times"""
        try:
            start_time = params.get("start_time", 0)
            end_time = params.get("end_time", 0)
            
            print(f"[DEBUG] Trimming video from {start_time}s to {end_time}s")
            print(f"[DEBUG] FFMPEG_AVAILABLE: {FFMPEG_AVAILABLE}")
            print(f"[DEBUG] MOVIEPY_AVAILABLE: {MOVIEPY_AVAILABLE}")
            
            # Try FFmpeg first
            if FFMPEG_AVAILABLE:
                try:
                    print(f"[DEBUG] Attempting FFmpeg trim...")
                    import ffmpeg
                    
                    # Create input stream from bytes
                    input_stream = ffmpeg.input('pipe:', format='mp4')
                    
                    # Apply trim filter
                    trimmed = ffmpeg.output(
                        input_stream,
                        'pipe:',
                        vcodec='copy',  # Copy video codec without re-encoding
                        acodec='copy',  # Copy audio codec without re-encoding
                        ss=start_time,  # Start time
                        t=end_time - start_time,  # Duration
                        f='mp4'
                    )
                    
                    # Run the ffmpeg command
                    stdout, stderr = ffmpeg.run(
                        trimmed,
                        input=file_data,
                        capture_stdout=True,
                        capture_stderr=True
                    )
                    
                    print(f"[DEBUG] FFmpeg video trim successful, output size: {len(stdout)} bytes")
                    return stdout
                    
                except Exception as e:
                    print(f"[DEBUG] FFmpeg trim failed: {e}")
                    print(f"[DEBUG] FFmpeg error type: {type(e)}")
                    import traceback
                    print(f"[DEBUG] FFmpeg traceback: {traceback.format_exc()}")
                    # Fall back to MoviePy
                    pass
            
            # Fallback to MoviePy
            if MOVIEPY_AVAILABLE:
                try:
                    print(f"[DEBUG] Attempting MoviePy trim...")
                    import tempfile
                    import os
                    
                    # Create temporary files
                    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input, \
                         tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                        
                        print(f"[DEBUG] Created temp files: {temp_input.name}, {temp_output.name}")
                        
                        # Write input data to temporary file
                        temp_input.write(file_data)
                        temp_input.flush()
                        
                        # Create VideoFileClip from temporary file
                        clip = VideoFileClip(temp_input.name)
                        
                        # Trim the clip
                        trimmed_clip = clip.subclipped(start_time, end_time)
                        
                        # Write to temporary output file
                        trimmed_clip.write_videofile(
                            temp_output.name,
                            codec='libx264',
                            audio_codec='aac',
                            temp_audiofile='temp-audio.m4a',
                            remove_temp=True
                        )
                        
                        # Read the result
                        temp_output.seek(0)
                        result_bytes = temp_output.read()
                        
                        # Clean up
                        clip.close()
                        trimmed_clip.close()
                        
                        # Remove temporary files (with error handling)
                        try:
                            os.unlink(temp_input.name)
                        except (OSError, PermissionError):
                            print(f"[DEBUG] Could not delete temp input file: {temp_input.name}")
                        
                        try:
                            os.unlink(temp_output.name)
                        except (OSError, PermissionError):
                            print(f"[DEBUG] Could not delete temp output file: {temp_output.name}")
                        
                        print(f"[DEBUG] MoviePy video trim successful, output size: {len(result_bytes)} bytes")
                        return result_bytes
                        
                except Exception as e:
                    print(f"[DEBUG] MoviePy trim failed: {e}")
                    print(f"[DEBUG] MoviePy error type: {type(e)}")
                    import traceback
                    print(f"[DEBUG] MoviePy traceback: {traceback.format_exc()}")
                    pass
            
            print(f"[DEBUG] No video trimming method available")
            logger.error("No video trimming method available (FFmpeg or MoviePy)")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error trimming video: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            logger.error(f"Error trimming video: {e}")
            import traceback
            print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            return None
    
    def _get_edited_path(self, original_path: str) -> str:
        """Generate path for edited file"""
        filename = Path(original_path).stem
        extension = Path(original_path).suffix
        edited_filename = f"{filename}_edited_{int(datetime.utcnow().timestamp())}{extension}"
        return os.path.join(self.temp_dir, edited_filename)
    
    async def create_collection(
        self, 
        db: AsyncSession, 
        user_id: int, 
        name: str, 
        description: Optional[str] = None
    ) -> MediaCollection:
        """Create a new media collection"""
        library = await self.get_user_library(db, user_id)
        if not library:
            library = await self.create_user_library(db, user_id)
        
        collection = MediaCollection(
            library_id=library.id,
            name=name,
            description=description,
            cover_image_path=None,
            library=library,
            items=[],
            created_at=datetime.utcnow(),
            updated_at=None
        )
        
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        return collection
    
    async def add_to_collection(
        self, 
        db: AsyncSession, 
        collection_id: int, 
        media_file_id: int, 
        user_id: int
    ) -> bool:
        """Add media file to collection"""
        # Verify ownership
        collection_result = await db.execute(
            select(MediaCollection)
            .join(MediaLibrary)
            .where(
                and_(
                    MediaCollection.id == collection_id,
                    MediaLibrary.user_id == user_id
                )
            )
        )
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            return False
        
        # Check if already in collection
        existing = await db.execute(
            select(MediaCollectionItem).where(
                and_(
                    MediaCollectionItem.collection_id == collection_id,
                    MediaCollectionItem.media_file_id == media_file_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            return True  # Already in collection
        
        # Add to collection
        item = MediaCollectionItem(
            collection_id=collection_id,
            media_file_id=media_file_id,
            order_index=0,
            added_at=datetime.utcnow()
        )
        
        db.add(item)
        await db.commit()
        return True
    
    async def get_collection_media(
        self, 
        db: AsyncSession, 
        collection_id: int, 
        user_id: int
    ) -> List[MediaFile]:
        """Get media files in a collection"""
        result = await db.execute(
            select(MediaFile)
            .join(MediaCollectionItem)
            .join(MediaCollection)
            .join(MediaLibrary)
            .where(
                and_(
                    MediaCollection.id == collection_id,
                    MediaLibrary.user_id == user_id
                )
            )
            .order_by(MediaCollectionItem.order_index)
        )
        return result.scalars().all()
    
    async def delete_media_file(self, db: AsyncSession, media_file_id: int, user_id: int) -> bool:
        """Delete a media file"""
        media_file = await self.get_media_file(db, media_file_id, user_id)
        if not media_file:
            return False
        
        # No need to delete physical files since we're using database storage
        # The file data is stored in the database and will be deleted with the record
        
        # Delete from database
        await db.delete(media_file)
        await db.commit()
        return True 