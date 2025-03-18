
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import httpx
import re
import json
import logging
from typing import Optional, Dict, Any, Union
from bs4 import BeautifulSoup
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TikTok Downloader API",
    description="API to download TikTok videos without watermark",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class TikTokURL(BaseModel):
    url: HttpUrl

class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int

class DownloadResponse(BaseModel):
    video_url: str
    audio_url: Optional[str] = None
    author: str
    title: str
    cover: str
    duration: int
    download_url: str

@app.post(
    "/api/download",
    response_model=DownloadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Video Not Found"},
        500: {"model": ErrorResponse, "description": "Server Error"},
    },
)
async def download_video(tiktok_url: TikTokURL):
    """
    Download a TikTok video without watermark
    
    - **url**: TikTok video URL
    
    Returns video information including download URL
    """
    try:
        url = str(tiktok_url.url)
        logger.info(f"Processing TikTok URL: {url}")
        
        # Updated regex to validate both the vm.tiktok.com format and the traditional format
        if not re.match(r'https?://(vm\.tiktok\.com/[A-Za-z0-9]+/?|(www\.)?tiktok\.com/@[\w.-]+/video/\d+)', url):
            raise HTTPException(
                status_code=400, 
                detail={"error": "invalid_url", "message": "Invalid TikTok URL format", "status": 400}
            )
        
        # Handle redirects for vm.tiktok.com URLs
        if 'vm.tiktok.com' in url:
            url = await resolve_shortened_url(url)
            logger.info(f"Resolved shortened URL to: {url}")
        
        # Extract video information using real implementation
        video_data = await extract_video_data_real(url)
        
        if not video_data:
            raise HTTPException(
                status_code=404,
                detail={"error": "video_not_found", "message": "Video not found or is private", "status": 404}
            )
        
        return video_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "server_error", "message": "Failed to process the video", "status": 500}
        )

async def resolve_shortened_url(url: str) -> str:
    """Follow redirects to get the full TikTok URL from a shortened vm.tiktok.com URL"""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=10.0)
            return str(response.url)
    except Exception as e:
        logger.error(f"Error resolving shortened URL: {str(e)}", exc_info=True)
        return url  # Return original URL if resolution fails

async def extract_video_data_real(url: str) -> Dict[str, Any]:
    """Extract real TikTok video data without watermark"""
    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Get the TikTok page content
            headers = {
                "User-Agent": user_agent,
                "Referer": "https://www.tiktok.com/",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Extract video ID
            video_id = None
            if "/video/" in url:
                video_id_match = re.search(r'/video/(\d+)', url)
                if video_id_match:
                    video_id = video_id_match.group(1)
            
            if not video_id:
                logger.error("Could not extract video ID from URL")
                return None
                
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Find JSON-LD data
            json_ld = None
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if '@type' in data and data['@type'] == 'VideoObject':
                        json_ld = data
                        break
                except Exception as e:
                    logger.error(f"Error parsing JSON-LD: {e}")
                    continue
            
            # Extract metadata from the page
            title = "TikTok Video"
            author = "TikTok User"
            cover = ""
            duration = 30
            
            if json_ld:
                title = json_ld.get('name', title)
                author = json_ld.get('author', {}).get('name', author)
                cover = json_ld.get('thumbnailUrl', '')[0] if isinstance(json_ld.get('thumbnailUrl', ''), list) else json_ld.get('thumbnailUrl', '')
                # Convert duration from ISO 8601 if available
                if 'duration' in json_ld:
                    iso_duration = json_ld['duration']
                    if 'PT' in iso_duration:
                        duration_str = iso_duration.replace('PT', '')
                        minutes = 0
                        seconds = 0
                        if 'M' in duration_str:
                            minutes_part = duration_str.split('M')[0]
                            minutes = int(minutes_part)
                            duration_str = duration_str.split('M')[1]
                        if 'S' in duration_str:
                            seconds_part = duration_str.split('S')[0]
                            seconds = int(seconds_part)
                        duration = minutes * 60 + seconds
            
            # Method 2: Use alternative API to get no-watermark video
            # This approach uses a third-party TikTok downloader API
            # We'll try multiple services for reliability
            
            # Try multiple services to ensure we get a working no-watermark URL
            no_watermark_url = await get_no_watermark_url(url, video_id)
            
            if not no_watermark_url:
                logger.error("Could not extract no-watermark URL")
                return None
            
            # Prepare the response
            video_data = {
                "video_url": no_watermark_url,
                "author": author,
                "title": title,
                "cover": cover,
                "duration": duration,
                "download_url": no_watermark_url
            }
            
            return video_data
    
    except Exception as e:
        logger.error(f"Error extracting video data: {str(e)}", exc_info=True)
        return None

async def get_no_watermark_url(url: str, video_id: str) -> Optional[str]:
    """Try multiple methods to get no-watermark URL"""
    try:
        # Method 1: Use ssstik.io service
        async with httpx.AsyncClient() as client:
            form_data = {
                'id': url,
                'locale': 'en',
                'tt': 'azM1a2M',
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://ssstik.io/',
                'Origin': 'https://ssstik.io',
            }
            response = await client.post('https://ssstik.io/abc', data=form_data, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                download_links = soup.select('a.download')
                
                for link in download_links:
                    if 'without watermark' in link.text.lower():
                        return link['href']
        
        # Method 2: Try alternative service if first method fails
        async with httpx.AsyncClient() as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            api_url = f"https://api.tikmate.app/api/lookup?url={url}"
            response = await client.get(api_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if 'videoUrl' in data:
                    return data['videoUrl']
        
        # Final fallback: Return a direct URL constructed from video ID
        # This approach may not work for all videos but serves as a fallback
        return f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/play/?video_id={video_id}&line=0&is_play_url=1&source=PackSourceEnum_FEED"
    
    except Exception as e:
        logger.error(f"Error getting no-watermark URL: {str(e)}", exc_info=True)
        return None

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Uncaught exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "server_error", "message": "An unexpected error occurred", "status": 500},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
