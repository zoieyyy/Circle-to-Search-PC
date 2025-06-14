import pyautogui
import tkinter as tk
import os
from datetime import datetime
import time
import webbrowser
import requests
import urllib.parse
import re
from PIL import Image
import pystray
import keyboard
from threading import Thread

class RegionSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect = None
        self.root = None
        self.canvas = None
        
    def select_region(self):
        """Create a transparent overlay for region selection"""
        self.root = tk.Toplevel()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        self.root.cursor = 'crosshair'
        
        # Create canvas
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(bg='black')
        
        # Bind mouse events
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Escape>', self.cancel_selection)
        
        # Add instructions
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 50,
            text="Click and drag to select area. Press ESC to cancel.",
            fill='white', font=('Arial', 16)
        )
        
        self.canvas.focus_set()
        self.root.wait_window()
        
        if all([self.start_x, self.start_y, self.end_x, self.end_y]):
            left = min(self.start_x, self.end_x)
            top = min(self.start_y, self.end_y)
            width = abs(self.end_x - self.start_x)
            height = abs(self.end_y - self.start_y)
            
            if width > 10 and height > 10:
                return (left, top, width, height)
        
        return None
    
    def on_click(self, event):
        self.start_x = event.x
        self.start_y = event.y
        
    def on_drag(self, event):
        if self.start_x and self.start_y:
            if self.rect:
                self.canvas.delete(self.rect)
            
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=2, fill='', stipple='gray50'
            )
            
    def on_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.root.destroy()
        
    def cancel_selection(self, event):
        self.start_x = self.start_y = self.end_x = self.end_y = None
        self.root.destroy()

class CircleToSearch:
    """Google Lens Circle to Search functionality"""
    
    def upload_to_tmpfiles(self, file_path):
        """Upload file to tmpfiles.org and return standardized download URL"""
        url = "https://tmpfiles.org/api/v1/upload"
        
        try:
            with open(file_path, "rb") as file:
                files = {"file": (os.path.basename(file_path), file)}
                response = requests.post(url, files=files, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        download_url = result["data"]["url"]
                        return self.standardize_tmpfiles_url(download_url)
                    else:
                        raise Exception(f"Upload failed: {result.get('error', 'Unknown error')}")
                else:
                    raise Exception(f"HTTP Error: {response.status_code}")
                    
        except Exception as e:
            raise Exception(f"Upload error: {str(e)}")
    
    def standardize_tmpfiles_url(self, url):
        """Convert tmpfiles.org URL to the /dl/ format"""
        url = url.replace("http://", "https://")
        
        if "/dl/" in url:
            return url
        
        match = re.match(r"(https://tmpfiles\.org)/(\d+/[^/]+)$", url)
        if match:
            base, path = match.groups()
            return f"{base}/dl/{path}"
        
        match_fallback = re.match(r"(https://tmpfiles\.org)/(.+)$", url)
        if match_fallback:
            base, path = match_fallback.groups()
            return f"{base}/dl/{path}"
        
        return url
    
    def search_with_google_lens(self, image_path):
        """Upload to tmpfiles.org and search with Google Lens"""
        try:
            print("Uploading image to tmpfiles.org...")
            tmpfiles_url = self.upload_to_tmpfiles(image_path)
            
            print(f"✓ Image uploaded successfully!")
            print(f"📎 Direct image URL: {tmpfiles_url}")
            
            # Create Google Lens URL
            encoded_url = urllib.parse.quote(tmpfiles_url, safe='')
            lens_url = f"https://lens.google.com/uploadbyurl?url={encoded_url}"
            
            print(f"🔍 Google Lens URL: {lens_url}")
            print("Opening Google Lens...")
            webbrowser.open(lens_url)
            
            return True
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

class SimpleCircleSearch:
    def __init__(self):
        self.circle_search = CircleToSearch()
        self.screenshots_dir = self.create_screenshots_dir()
        self.icon = None
        self.running = True
        
    def create_screenshots_dir(self):
        """Create screenshots directory in the same directory as the script"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        screenshots_dir = os.path.join(script_dir, "screenshots")
        
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            print(f"Created screenshots directory: {screenshots_dir}")
        
        return screenshots_dir
        
    def get_filename(self):
        """Generate a unique filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"circle_search_{timestamp}.png"
    
    def take_screenshot(self):
        """Take screenshot of selected region"""
        print("Circle to Search - Select an area to search")
        print(f"Screenshots will be saved to: {self.screenshots_dir}")
        print("Press ESC to cancel selection")
        
        root = tk.Tk()
        root.withdraw()
        
        try:
            time.sleep(0.2)
            selector = RegionSelector()
            region = selector.select_region()
            
            if region:
                print("Taking screenshot of selected area...")
                screenshot = pyautogui.screenshot(region=region)
                save_path = os.path.join(self.screenshots_dir, self.get_filename())
                screenshot.save(save_path)
                
                print(f"Screenshot saved: {save_path}")
                print("Uploading and searching with Google Lens...")
                
                success = self.circle_search.search_with_google_lens(save_path)
                
                if success:
                    print("✓ Successfully opened in Google Lens!")
                else:
                    print("✗ Failed to upload and search")
                    
            else:
                print("Selection cancelled")
                
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            root.destroy()

    def create_system_tray_icon(self):
        """Create system tray icon with menu"""
        # Create a simple white icon with black text
        image = Image.new('RGB', (64, 64), color='white')
        icon = pystray.Icon(
            "Circle to Search",
            image,
            "Circle to Search",
            menu=pystray.Menu(
                pystray.MenuItem("Take Screenshot", self.take_screenshot),
                pystray.MenuItem("Exit", self.quit_application)
            )
        )
        return icon

    def quit_application(self):
        """Quit the application and remove system tray icon"""
        self.running = False
        if self.icon:
            self.icon.stop()
        keyboard.unhook_all()

    def run(self):
        """Main application flow"""
        # Create system tray icon
        self.icon = self.create_system_tray_icon()
        
        # Start hotkey listener in separate thread
        def hotkey_listener():
            while self.running:
                keyboard.wait('home')
                if self.running:
                    self.take_screenshot()
        
        Thread(target=hotkey_listener, daemon=True).start()
        
        # Run system tray icon
        print("Circle to Search is running in system tray")
        print("Press Home key to take a screenshot")
        print("Right-click tray icon for menu options")
        self.icon.run()

def main():
    # Install required packages if needed
    required_packages = [
        ('requests', 'requests'),
        ('pyautogui', 'pyautogui'),
        ('PIL', 'pillow'),
        ('pystray', 'pystray'),
        ('keyboard', 'keyboard')
    ]
    
    for import_name, pip_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pip_name}...")
            os.system(f"pip install {pip_name}")
    
    # Disable pyautogui failsafe
    pyautogui.FAILSAFE = False
    
    # Run the application
    app = SimpleCircleSearch()
    app.run()

if __name__ == "__main__":
    main()