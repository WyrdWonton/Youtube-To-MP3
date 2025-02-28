import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import threading
import yt_dlp
import sys
import io
from datetime import datetime
import re
import shutil
import time
import json
import os.path


# Custom logger class for yt_dlp that redirects to text widget
class CustomLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
    def format_message(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if msg.strip():  # Only add timestamp for non-empty lines
            return f"[{timestamp}] {msg}"
        return msg
    
    def debug(self, msg):
        self._write_to_widget(msg)
    
    def info(self, msg):
        self._write_to_widget(msg)
    
    def warning(self, msg):
        self._write_to_widget(f"Warning: {msg}")
    
    def error(self, msg):
        self._write_to_widget(f"Error: {msg}")
    
    def _write_to_widget(self, msg):
        self.text_widget.config(state=tk.NORMAL)
        formatted_msg = self.format_message(msg)
        self.text_widget.insert(tk.END, f"{formatted_msg}\n")
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

# Custom stdout redirection class to capture console output
class ConsoleRedirector(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def write(self, string):
        self.text_widget.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format the output with timestamp
        if string.strip():  # Only add timestamp for non-empty lines
            self.text_widget.insert(tk.END, f"[{timestamp}] {string}")
        else:
            self.text_widget.insert(tk.END, string)
            
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)
        return len(string)
        
    def flush(self):
        pass

class ModernYouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube to MP3 Converter")
        self.root.geometry("900x600")
        self.root.minsize(800, 550)

        # Theme settings
        self.dark_mode = False
        self.colors = self.get_light_theme()
        
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Create main frame with rounded corners
        self.main_frame = tk.Frame(root, bg=self.colors['bg_secondary'], padx=20, pady=20)
        self.main_frame.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.9, anchor=tk.CENTER)
        
        # Header with app logo and title
        self.header_frame = tk.Frame(self.main_frame, bg=self.colors['bg_secondary'])
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_label = tk.Label(
            self.header_frame, 
            text="YouTube to MP3 Converter", 
            font=("Arial", 24, "bold"), 
            fg=self.colors['accent'], 
            bg=self.colors['bg_secondary']
        )
        self.title_label.pack(side=tk.LEFT, padx=10)
        
        # Create options menu dropdown
        self.menu_button = self.create_button(
            self.header_frame,
            "⋮ Options",
            self.show_options_menu,
            self.colors['accent_secondary'],
            width=100
        )
        self.menu_button.pack(side=tk.RIGHT, padx=10)
        
        # Content frame (left side)
        self.content_frame = tk.Frame(self.main_frame, bg=self.colors['bg_secondary'])
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # YouTube URL input with label
        self.url_frame = self.create_input_group(self.content_frame, "Enter YouTube URL:")
        self.link_entry = tk.Entry(
            self.url_frame, 
            font=("Arial", 12),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            bg=self.colors['input_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary']
        )
        self.link_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Save location input with label and button
        self.location_frame = self.create_input_group(self.content_frame, "Save Location:")
        
        self.location_inner_frame = tk.Frame(self.location_frame, bg=self.colors['bg_secondary'])
        self.location_inner_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.save_entry = tk.Entry(
            self.location_inner_frame, 
            font=("Arial", 12),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            bg=self.colors['input_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary']
        )
        self.save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Default save location is Downloads folder
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_entry.insert(0, downloads_path)
        
        self.browse_button = self.create_button(
            self.location_inner_frame, 
            "Browse", 
            self.browse_location,
            self.colors['accent_secondary'],
            width=80
        )
        self.browse_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Status label
        self.status_frame = self.create_input_group(self.content_frame, "Status:")
        self.status_label = tk.Label(
            self.status_frame, 
            text="Ready to download", 
            font=("Arial", 12), 
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary'],
            anchor="w"
        )
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # Progress bar
        self.progress_frame = tk.Frame(self.content_frame, bg=self.colors['bg_secondary'], pady=10)
        self.progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_label = tk.Label(
            self.progress_frame, 
            text="Download Progress:", 
            font=("Arial", 12, "bold"), 
            bg=self.colors['bg_secondary'], 
            fg=self.colors['text_primary'],
            anchor="w"
        )
        self.progress_label.pack(fill=tk.X)
        
        self.progress_bar_frame = tk.Frame(self.progress_frame, bg=self.colors['progress_bg'], height=20, bd=0, highlightthickness=0)
        self.progress_bar_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_var.set(0)
        
        self.progress_bar = tk.Frame(self.progress_bar_frame, bg=self.colors['accent'], width=0, height=20)
        self.progress_bar.place(x=0, y=0, height=20)
        
        self.progress_text = tk.Label(
            self.progress_bar_frame, 
            text="0%", 
            bg=self.colors['progress_bg'], 
            fg=self.colors['text_primary'],
            font=("Arial", 9)
        )
        self.progress_text.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Convert Button
        self.button_frame = tk.Frame(self.content_frame, bg=self.colors['bg_secondary'], pady=20)
        self.button_frame.pack(fill=tk.X)
        
        self.convert_button = self.create_button(
            self.button_frame, 
            "Convert to MP3", 
            self.start_conversion,
            self.colors['accent'],
            width=200
        )
        self.convert_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Console output frame (right side, initially hidden)
        self.console_frame = tk.Frame(self.main_frame, bg=self.colors['console_header_bg'], width=300)
        self.console_visible = False
        
        self.console_header = tk.Label(
            self.console_frame, 
            text="Console Output", 
            font=("Arial", 12, "bold"),
            bg=self.colors['console_header_bg'],
            fg=self.colors['text_primary'],
            pady=5
        )
        self.console_header.pack(fill=tk.X)
        
        # Keep console colors consistent regardless of theme
        self.console_output = scrolledtext.ScrolledText(
            self.console_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 10),
            bg="#272822",  # Dark background stays the same
            fg="#f8f8f2",  # Light text stays the same
            insertbackground="#f8f8f2"
        )
        self.console_output.pack(fill=tk.BOTH, expand=True)
        self.console_output.config(state=tk.DISABLED)
        
        # Create custom logger for yt-dlp
        self.custom_logger = CustomLogger(self.console_output)
        
        # Redirect stdout to our console widget
        self.stdout_redirector = ConsoleRedirector(self.console_output)
        self.original_stdout = sys.stdout
        
        # Animation variables
        self.animate_progress_id = None
        
        # Initialize with console hidden
        self.console_visible = False
        print("Application started.")
        print(f"Python executable: {sys.executable}")
        print("Console ready for output.")
        
        # Load settings after all UI elements are created
        self.load_settings()
        
    def get_light_theme(self):
        """Return light theme colors"""
        return {
            'bg_primary': '#6A5ACD',  # Slate Blue
            'bg_secondary': 'white',
            'text_primary': '#333',
            'text_secondary': '#666',
            'accent': '#6A5ACD',  # Slate Blue
            'accent_secondary': '#8A2BE2',  # BlueViolet
            'border': '#ddd',
            'input_bg': 'white',
            'progress_bg': '#eee',
            'console_header_bg': '#f0f0f0',
        }
    
    def get_dark_theme(self):
        """Return dark theme colors"""
        return {
            'bg_primary': '#1E1E2E',  # Dark blue-gray
            'bg_secondary': '#2A2A3C',  # Slightly lighter blue-gray
            'text_primary': '#E0E0E0',  # Light gray
            'text_secondary': '#BBBBBB',  # Medium gray
            'accent': '#7B68EE',  # Medium slate blue
            'accent_secondary': '#9370DB',  # Medium purple
            'border': '#444',
            'input_bg': '#3A3A4C',  # Dark input background
            'progress_bg': '#444',
            'console_header_bg': '#252535',
        }
    
    def toggle_theme(self):
        """Switch between light and dark themes"""
        self.dark_mode = not self.dark_mode
        
        # Update colors based on mode
        if self.dark_mode:
            self.colors = self.get_dark_theme()
        else:
            self.colors = self.get_light_theme()
        
        # Update all UI elements with new colors
        self.update_ui_colors()
        #save settings
        self.save_settings()
    
    def update_ui_colors(self):
        """Update all UI elements with current theme colors"""
        # Root and main frames
        self.root.configure(bg=self.colors['bg_primary'])
        self.main_frame.configure(bg=self.colors['bg_secondary'])
        
        # Header
        self.header_frame.configure(bg=self.colors['bg_secondary'])
        self.title_label.configure(fg=self.colors['accent'], bg=self.colors['bg_secondary'])
        self.menu_button.configure(bg=self.colors['accent_secondary'], fg="white")
        
        # Content frame
        self.content_frame.configure(bg=self.colors['bg_secondary'])
        
        # URL frame
        self.url_frame.configure(bg=self.colors['bg_secondary'])
        for child in self.url_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        
        self.link_entry.configure(
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            bg=self.colors['input_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary']
        )
        
        # Location frame
        self.location_frame.configure(bg=self.colors['bg_secondary'])
        for child in self.location_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        
        self.location_inner_frame.configure(bg=self.colors['bg_secondary'])
        self.save_entry.configure(
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            bg=self.colors['input_bg'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary']
        )
        self.browse_button.configure(bg=self.colors['accent_secondary'], fg="white")
        
        # Status frame
        self.status_frame.configure(bg=self.colors['bg_secondary'])
        for child in self.status_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
                
        self.status_label.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        
        # Progress frame
        self.progress_frame.configure(bg=self.colors['bg_secondary'])
        self.progress_label.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        self.progress_bar_frame.configure(bg=self.colors['progress_bg'])
        self.progress_bar.configure(bg=self.colors['accent'])
        self.progress_text.configure(bg=self.colors['progress_bg'], fg=self.colors['text_primary'])
        
        # Button frame
        self.button_frame.configure(bg=self.colors['bg_secondary'])
        self.convert_button.configure(bg=self.colors['accent'], fg="white")
        
        # Console frame
        if self.console_visible:
            self.console_frame.configure(bg=self.colors['console_header_bg'])
            self.console_header.configure(bg=self.colors['console_header_bg'], fg=self.colors['text_primary'])
            # Don't change console colors - keep them consistent
    
    def create_input_group(self, parent, label_text):
        """Create a labeled input group"""
        frame = tk.Frame(parent, bg=self.colors['bg_secondary'], pady=10)
        frame.pack(fill=tk.X)
        
        label = tk.Label(
            frame, 
            text=label_text, 
            font=("Arial", 12, "bold"), 
            bg=self.colors['bg_secondary'], 
            fg=self.colors['text_primary'],
            anchor="w"
        )
        label.pack(fill=tk.X)
        
        return frame
    
    def create_button(self, parent, text, command, color, width=None):
        """Create a styled button"""
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Arial", 11, "bold"),
            bg=color,
            fg="white",
            activebackground=self.colors['accent_secondary'] if color == self.colors['accent'] else self.colors['accent'],
            activeforeground="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        
        if width:
            button.config(width=width // 10)  # Approximate character width
            
        return button
        
    def toggle_console(self):
        """Toggle console visibility"""
        if self.console_visible:
            self.console_frame.pack_forget()
            self.console_visible = False
            sys.stdout = self.original_stdout
        else:
            self.console_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
            self.console_visible = True
            sys.stdout = self.stdout_redirector
        #save settings
        self.save_settings()
    
    def browse_location(self):
        """Open dialog to select save location"""
        directory = filedialog.askdirectory(initialdir=self.save_entry.get())
        if directory:
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, directory)
            print(f"Save location set to: {directory}")
        #save settings
        self.save_settings()
    
    def update_status(self, text):
        """Update status label with animation effect"""
        self.status_label.config(text=text)
        
        # Pulse animation for status update
        original_bg = self.status_label.cget("bg")
        pulse_color = "#e6e6fa" if not self.dark_mode else "#3A3A6A"  # Light purple or dark purple
        self.status_label.config(bg=pulse_color)
        
        def reset_bg():
            self.status_label.config(bg=original_bg)
            
        self.root.after(300, reset_bg)
    

    def show_options_menu(self):
        """Show options popup menu"""
        # Create a popup menu
        popup = tk.Menu(self.root, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                        activebackground=self.colors['accent'], activeforeground="white")
        
        # Add theme toggle option
        theme_text = "☀️ Light Mode" if self.dark_mode else "🌙 Dark Mode"
        popup.add_command(label=theme_text, command=self.toggle_theme)
        
        # Add console toggle option
        console_text = "Hide Console" if self.console_visible else "Show Console"
        popup.add_command(label=console_text, command=self.toggle_console)
        
        # Display the menu
        try:
            x = self.menu_button.winfo_rootx()
            y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
            popup.tk_popup(x, y, 0)
        finally:
            # Make sure to release the grab
            popup.grab_release()


    def save_settings(self):
        """Save current settings to a JSON file"""
        settings = {
            'dark_mode': self.dark_mode,
            'console_visible': self.console_visible,
            'save_location': self.save_entry.get()
        }
        
        # Save to a settings file in user's home directory
        settings_dir = os.path.join(os.path.expanduser("~"), ".youtube_mp3_converter")
        os.makedirs(settings_dir, exist_ok=True)
        settings_file = os.path.join(settings_dir, "settings.json")
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f)
            print(f"Settings saved to {settings_file}")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Load settings from JSON file"""
        settings_file = os.path.join(os.path.expanduser("~"), ".youtube_mp3_converter", "settings.json")
        
        if not os.path.exists(settings_file):
            print("No saved settings found, using defaults")
            return
        
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            
            # Apply loaded settings
            if 'dark_mode' in settings:
                self.dark_mode = settings['dark_mode']
                if self.dark_mode:
                    self.colors = self.get_dark_theme()
                else:
                    self.colors = self.get_light_theme()
                self.update_ui_colors()
            
            if 'console_visible' in settings and settings['console_visible']:
                # Toggle console if it should be visible
                self.toggle_console()
            
            if 'save_location' in settings and settings['save_location']:
                self.save_entry.delete(0, tk.END)
                self.save_entry.insert(0, settings['save_location'])
                
            print("Settings loaded successfully")
        except Exception as e:
            print(f"Error loading settings: {e}")


    def update_progress_bar(self, percent):
        """Update progress bar with animation"""
        if self.animate_progress_id:
            self.root.after_cancel(self.animate_progress_id)
            
        current = self.progress_var.get()
        target = percent
        
        # Progress text update
        self.progress_text.config(text=f"{int(target)}%")
        
        # Calculate width based on percentage
        bar_width = (self.progress_bar_frame.winfo_width() * target) / 100
        
        def animate_to(current_val, target_val, step=0):
            if abs(current_val - target_val) < 0.5 or step > 20:
                self.progress_var.set(target_val)
                self.progress_bar.place_configure(width=int(bar_width))
                self.animate_progress_id = None
                return
                
            # Calculate next value with easing
            next_val = current_val + (target_val - current_val) * 0.3
            self.progress_var.set(next_val)
            
            # Calculate interim width
            interim_width = (self.progress_bar_frame.winfo_width() * next_val) / 100
            self.progress_bar.place_configure(width=int(interim_width))
            
            # Continue animation
            self.animate_progress_id = self.root.after(
                20, animate_to, next_val, target_val, step + 1
            )
        
        animate_to(current, target)
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Print detailed info to console
            if 'speed' in d and d['speed'] is not None:
                speed_mb = d['speed'] / 1024 / 1024
                eta = d.get('eta', 'unknown')
                print(f"Download speed: {speed_mb:.2f} MB/s | ETA: {eta} seconds")
                
            # Update status with basic info
            self.update_status(f"Downloading... Please wait")
                
            # Update progress bar
            if 'total_bytes' in d and d['total_bytes']:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                self.update_progress_bar(percent)
                print(f"Progress: {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                self.update_progress_bar(percent)
                print(f"Progress: {percent:.1f}% (estimated)")
                
        elif d['status'] == 'finished':
            print("Download complete. Converting to MP3...")
            self.update_status("Processing audio... Please wait")
            self.update_progress_bar(100)
    
    def download_mp3(self):
        """Download YouTube video as MP3"""
        try:
            url = self.link_entry.get()
            save_path = self.save_entry.get()
            final_mp3_path = None
            temp_dir = None
            
            if not url:
                self.update_status("Error: Please enter a YouTube URL")
                print("Error: No YouTube URL provided")
                return
            
            # Validate URL
            if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$', url):
                self.update_status("Error: Invalid YouTube URL")
                print(f"Error: Invalid YouTube URL: {url}")
                return
            
            # Make sure save path exists
            if not os.path.exists(save_path):
                try:
                    os.makedirs(save_path)
                    print(f"Created save directory: {save_path}")
                except Exception as e:
                    self.update_status(f"Error: Cannot create save directory")
                    print(f"Error creating save directory: {e}")
                    return
            
            # Check write permissions
            if not os.access(save_path, os.W_OK):
                self.update_status("Error: No write permission to save location")
                print(f"Error: No write permission to save location: {save_path}")
                return
                
            print(f"Starting download from: {url}")
            print(f"Save location: {save_path}")
            
            self.update_status("Getting video information...")
            print("Retrieving video information...")
            
            # Reset progress bar
            self.update_progress_bar(0)
            
            try:
                # Create a temporary directory for download
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                temp_dir = os.path.join(save_path, f"_temp_youtube_dl_{timestamp}")
                os.makedirs(temp_dir, exist_ok=True)
                print(f"Created temporary directory: {temp_dir}")
                
                # Configure yt-dlp options
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'progress_hooks': [self.progress_hook],
                    'verbose': True,
                    'logger': self.custom_logger,
                }
                
                # Download and convert the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    video_title = info_dict.get('title', 'Unknown')
                    print(f"Downloaded: {video_title}")
                    
                    # Clean title for filename
                    clean_title = re.sub(r'[^\w\s.-]', '_', video_title)
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                    
                    # Find the mp3 file in the temp directory
                    temp_mp3_path = None
                    for file in os.listdir(temp_dir):
                        if file.endswith('.mp3'):
                            temp_mp3_path = os.path.join(temp_dir, file)
                            print(f"Found MP3 file: {temp_mp3_path}")
                            break
                    
                    if not temp_mp3_path:
                        raise FileNotFoundError(f"MP3 file not found in temporary directory: {temp_dir}")
                    
                    # Final mp3 path in the output directory
                    mp3_filename = f"{clean_title}.mp3"
                    final_mp3_path = os.path.join(save_path, mp3_filename)
                    
                    # Check if file already exists
                    counter = 1
                    base_name, ext = os.path.splitext(mp3_filename)
                    while os.path.exists(final_mp3_path):
                        final_mp3_path = os.path.join(save_path, f"{base_name}_{counter}{ext}")
                        counter += 1
                        print(f"File already exists, will save as: {final_mp3_path}")
                    
                    # Copy the file from temp to final destination
                    try:
                        shutil.copy2(temp_mp3_path, final_mp3_path)
                        print(f"Successfully copied MP3 file to: {final_mp3_path}")
                        
                        # Verify the file exists and has a non-zero size
                        if not os.path.exists(final_mp3_path) or os.path.getsize(final_mp3_path) == 0:
                            raise Exception(f"File copy verification failed for {final_mp3_path}")
                            
                    except Exception as e:
                        print(f"Error copying file: {e}")
                        raise Exception(f"Failed to copy MP3 file: {e}")
            
            finally:
                # Clean up the temporary directory - but only after we're sure we have the file
                if temp_dir and os.path.exists(temp_dir) and final_mp3_path and os.path.exists(final_mp3_path):
                    try:
                        time.sleep(1)  # Small delay to ensure file operations are complete
                        shutil.rmtree(temp_dir)
                        print(f"Removed temporary directory: {temp_dir}")
                    except Exception as e:
                        print(f"Warning: Could not clean up temp files: {e}")
            
            # Final success check
            if final_mp3_path and os.path.exists(final_mp3_path):
                print(f"✓ Conversion completed successfully!")    
                self.update_status(f"✓ Success! MP3 file saved")
                
                # Keep at 100% for a moment before showing success message
                def show_success():
                    # Open file explorer to show the file
                    folder_path = os.path.dirname(final_mp3_path)
                    file_name = os.path.basename(final_mp3_path)
                    
                    # Ask if user wants to open the file location
                    response = messagebox.askquestion(
                        "Success", 
                        f"MP3 file saved to:\n{final_mp3_path}\n\nWould you like to open the file location?",
                        icon='info'
                    )
                    
                    if response == 'yes':
                        try:
                            # Open file explorer and select the specific file
                            if sys.platform == 'win32':
                                # This opens Explorer and selects the specific file
                                os.system(f'explorer /select,"{final_mp3_path}"')
                            elif sys.platform == 'darwin':  # macOS
                                os.system(f'open -R "{final_mp3_path}"')
                            else:  # Linux
                                # For Linux, we'll just open the folder as file selection varies by desktop environment
                                os.system(f'xdg-open "{folder_path}"')
                                
                            # Play a notification sound (Windows only)
                            if sys.platform == 'win32':
                                import winsound
                                winsound.MessageBeep(winsound.MB_ICONINFORMATION)
                        except Exception as e:
                            print(f"Error opening file location: {e}")
                
                self.root.after(500, show_success)
            else:
                raise Exception(f"MP3 file not found at expected location: {final_mp3_path}")
            
        except Exception as e:
            err_msg = str(e)
            print(f"Error: {err_msg}")
            self.update_status(f"Error: {err_msg}")
            messagebox.showerror("Error", f"An error occurred:\n{err_msg}")
    
    def start_conversion(self):
        """Start conversion in a separate thread to keep UI responsive"""
        # Show pulsing animation on button
        original_bg = self.convert_button.cget("bg")
        self.convert_button.config(bg=self.colors['accent_secondary'])
        
        def reset_button():
            self.convert_button.config(bg=original_bg)
        
        self.root.after(200, reset_button)
        
        # Disable the convert button during conversion
        self.convert_button.config(state=tk.DISABLED)
        
        # Start conversion in a new thread
        thread = threading.Thread(target=self.download_mp3)
        thread.start()
        
        # Check if thread is still running and re-enable button when done
        def check_thread():
            if thread.is_alive():
                self.root.after(100, check_thread)
            else:
                self.convert_button.config(state=tk.NORMAL)
        
        check_thread()

if __name__ == "__main__":
    root = tk.Tk()
    root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(data='''
    R0lGODlhIAAgAOeJAAAAAAEBAQICAgMDAwQEBAUFBQYGBgcHBwgICAkJCQoKCgsLCwwMDA0NDQ4O
    Dg8PDxAQEBERERISEhMTExQUFBUVFRYWFhcXFxgYGBkZGRoaGhsbGxwcHB0dHR4eHh8fHyAgICEh
    ISIiIiMjIyQkJCUlJSYmJicnJygoKCkpKSoqKisrKywsLC0tLS4uLi8vLzAwMDExMTIyMjMzMzQ0
    NDU1NTY2Njc3Nzg4ODk5OTo6Ojs7Ozw8PD09PT4+Pj8/P0BAQEFBQUJCQkNDQ0REREVFRUZGRkdH
    R0hISElJSUpKSktLS0xMTE1NTU5OTk9PT1BQUFFRUVJSUlNTU1RUVFVVVVZWVldXV1hYWFlZWVpa
    WltbW1xcXF1dXV5eXl9fX2BgYGFhYWJiYmNjY2RkZGVlZWZmZmdnZ2hoaGlpaWpqamtra2xsbG1t
    bW5ubm9vb3BwcHFxcXJycnNzc3R0dHV1dXZ2dnd3d3h4eHl5eXp6ent7e3x8fH19fX5+fn9/f4CA
    gIGBgYKCgoODg4SEhIWFhYaGhoeHh4iIiImJiYqKiouLi4yMjI2NjY6Ojo+Pj5CQkJGRkZKSkpOT
    k5SUlJWVlZaWlpeXl5iYmJmZmZqampubm5ycnJ2dnZ6enp+fn6CgoKGhoaKioqOjo6SkpKWlpaam
    pqenp6ioqKmpqaqqqqurq6ysrK2tra6urq+vr7CwsLGxsbKysrOzs7S0tLW1tba2tre3t7i4uLm5
    ubq6uru7u7y8vL29vb6+vr+/v8DAwMHBwcLCwsPDw8TExMXFxcbGxsfHx8jIyMnJycrKysvLy8zM
    zM3Nzc7Ozs/Pz9DQ0NHR0dLS0tPT09TU1NXV1dbW1tfX19jY2NnZ2dra2tvb29zc3N3d3d7e3t/f
    3+Dg4OHh4eLi4uPj4+Tk5OXl5ebm5ufn5+jo6Onp6erq6uvr6+zs7O3t7e7u7u/v7/Dw8PHx8fLy
    8vPz8/T09PX19fb29vf39/j4+Pn5+fr6+vv7+/z8/P39/f7+/v///yH5BAEKAP8ALAAAAAAgACAA
    AAj+AP8JHEiwoMGDCBMqRMjrVy8YL1CUCBFiwoB8D4kQIhgxV6IPFwIgQ1jQ3AiOHGEZCGAMobkO
    mDBBIsIgHDiYGMVV2Mmzpz9iCdOlXJgLJlCfGzs5YdL06wQKEiRMsASqKNOqDcfhknmVwDhxWbNq
    VQWrq1eVGHTJPKoTLdq0ZnPCBMNjh8yjUECB8hQWpg+6CGvIfMo3rt+8fhw9AjCDJlInI0Z4CKNW
    mF29CR/LPKwZM+TAj6YowbEjSQ4dS7xyFuYvm+vXsGPLnl2QcjDNGW/cwAAq9bDGq137G2FQs+/f
    wHdneO3ad/ALN27YUF58ufPm0FGTLl6DhBPr2J//hfCRRLv5LDrWq//dHYiP9/B5l5/PI76PGfLn
    y7+f4wd9/Ub0YAMOPARoIAwu6EDggg18YMMPPjgRoQ9G0ABEDkv4IIQRR5T4oUE2ACDDDkYgQcSD
    UPzwBUI2lPjDEEDYYKMQQcRgkA0f/BBEFEUkAYUNT1QBBRc2dABCQTb4MAQQKPZARRU2uBgFGHLY
    EAIILdkwxhZMNNFEITbMwYUXUDgxphJQQGnmnGRy5AMAC2DkgQdM2JAAQT5o9MEHcNhQAEBr2DBG
    GGKwYYMFAImRRRYw2PACQD5cEaiiiqJhQwcDBdFGG3TYoIZAWbjhBh023JAAEQMBEQQUO9iAFUAW
    WBBBBB7YgAUQpBbUq0C5EiQFsQP9CqxAwxJkrLHH2nCEQaQaa+yxBVWK0A8abauttggh5MMXsNK6
    bRMDBQQAOw==
    '''))
    app = ModernYouTubeDownloader(root)
    root.mainloop()