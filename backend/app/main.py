"""Main FastAPI application entry point."""
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import songs, game
from .config import settings, IS_FROZEN
from .utils.logger import logger


def get_local_ip() -> str:
    """Get the local IP address for LAN access."""
    try:
        # Create a socket to connect to an external address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # Try to connect to a public DNS server (doesn't actually send data)
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def print_qr_code(url: str) -> None:
    """Print QR code to console for easy mobile access."""
    try:
        import qrcode
        from io import StringIO
        import ctypes
        from ctypes import wintypes
        import os

        # Set Windows console to UTF-8 mode and font for proper Unicode display
        if os.name == 'nt':
            kernel32 = ctypes.windll.kernel32
            # Set console code page to UTF-8 (65001)
            kernel32.SetConsoleOutputCP(65001)

            # Try to set console font to Consolas for better Unicode support
            try:
                # Define CONSOLE_FONT_INFOEX structure
                class CONSOLE_FONT_INFOEX(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.ULONG),
                        ("nFont", wintypes.DWORD),
                        ("dwFontSizeX", wintypes.SHORT),
                        ("dwFontSizeY", wintypes.SHORT),
                        ("FontFamily", wintypes.UINT),
                        ("FontWeight", wintypes.UINT),
                        ("FaceName", wintypes.WCHAR * 32)
                    ]

                # Get stdout handle
                STD_OUTPUT_HANDLE = -11
                hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

                # Get current font info
                font_info = CONSOLE_FONT_INFOEX()
                font_info.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)

                if kernel32.GetCurrentConsoleFontEx(hConsole, False, ctypes.byref(font_info)):
                    # Set to Consolas font while keeping other settings
                    font_info.FaceName = "Consolas"
                    # Try to set a reasonable font size
                    font_info.dwFontSizeX = 0  # 0 means don't change
                    font_info.dwFontSizeY = 16  # 16 pixels height
                    kernel32.SetCurrentConsoleFontEx(hConsole, False, ctypes.byref(font_info))
            except Exception:
                # If font setting fails, continue anyway
                pass

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Generate ASCII QR code
        buffer = StringIO()
        qr.print_ascii(out=buffer, invert=True)
        buffer.seek(0)
        qr_text = buffer.read()

        print("\n" + "=" * 50)
        print("  Scan QR code to access from mobile device:")
        print("=" * 50)
        print(qr_text)
        print(f"  URL: {url}")
        print("=" * 50 + "\n")
    except Exception as e:
        logger.warning(f"Failed to generate QR code: {e}")
        print(f"\n  Access URL: {url}\n")


def show_access_info():
    """Show LAN access URL and QR code after startup."""
    if settings.HOST == '0.0.0.0':
        local_ip = get_local_ip()
        lan_url = f"http://{local_ip}:{settings.PORT}"
        print_qr_code(lan_url)
    else:
        print(f"\n  Server running at: http://{settings.HOST}:{settings.PORT}\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Bootstrap dependency injection container
    from .core.bootstrap import bootstrap_services
    bootstrap_services()

    # Load songs cache on startup
    from .api.songs import load_songs_cache
    load_songs_cache()

    # Show access info after all resources loaded
    show_access_info()

    yield

    # Cleanup
    from .core.container import reset_container
    reset_container()
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="External song selector for Hatsune Miku Project DIVA MegaMix+",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(songs.router, prefix="/api")
app.include_router(game.router, prefix="/api")

# Try to serve static frontend files
if IS_FROZEN:
    # In frozen mode, frontend files are in the bundle directory
    frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    # In development mode, frontend files are relative to backend
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Serve index.html for all routes (SPA behavior)
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


def main():
    """Main entry point for the application."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG and not IS_FROZEN,  # Disable reload in frozen mode
        log_level="debug" if settings.DEBUG else "info"
    )


if __name__ == "__main__":
    main()
