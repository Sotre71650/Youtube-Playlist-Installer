import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import yt_dlp
import tempfile
import shutil
import threading

class YouTubeDownloader:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Universal Media Downloader")
        self.window.geometry("700x500")
        
        # Left side - Main controls
        left_frame = ttk.Frame(self.window, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # URL Entry
        url_frame = ttk.Frame(left_frame, padding="5")
        url_frame.pack(fill=tk.X)
        
        ttk.Label(url_frame, text="Enter URL:").pack()
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(pady=5)
        
        # Format Selection
        format_frame = ttk.Frame(left_frame, padding="5")
        format_frame.pack(fill=tk.X)
        
        ttk.Label(format_frame, text="Select Format:").pack()
        self.format_var = tk.StringVar(value="mp4_1080")
        
        formats = [
            ("Video - 1440p", "mp4_1440"),
            ("Video - 1080p", "mp4_1080"),
            ("Video - 720p", "mp4_720"),
            ("Audio Only (MP3)", "mp3")
        ]
        
        for text, value in formats:
            ttk.Radiobutton(format_frame, text=text, variable=self.format_var, 
                          value=value).pack()
        
        # Progress
        progress_frame = ttk.Frame(left_frame, padding="5")
        progress_frame.pack(fill=tk.X)
        
        self.progress_var = tk.StringVar(value="Ready to download")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack()
        
        self.progress = ttk.Progressbar(progress_frame, length=300, mode='determinate')
        self.progress.pack(pady=5)
        
        # Download count
        self.download_count = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.download_count).pack()
        
        # Current file being downloaded
        self.current_file = tk.StringVar(value="")
        ttk.Label(left_frame, textvariable=self.current_file).pack(pady=5)
        
        # Download button
        self.download_btn = ttk.Button(left_frame, text="Download", command=self.start_download)
        self.download_btn.pack(pady=10)
        
        # Right side - Failed downloads list
        right_frame = ttk.Frame(self.window, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        ttk.Label(right_frame, text="Failed Downloads:").pack()
        self.failed_list = scrolledtext.ScrolledText(right_frame, width=40, height=20)
        self.failed_list.pack(fill=tk.BOTH, expand=True)
        
        # Track download statistics
        self.successful_downloads = 0
        self.total_videos = 0
        self.failed_downloads = []

    def get_format_options(self):
        format_choice = self.format_var.get()
        format_priority = {
            "mp4_1440": [
                'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'bestvideo+bestaudio/best'
            ],
            "mp4_1080": [
                'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'bestvideo+bestaudio/best'
            ],
            "mp4_720": [
                'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'bestvideo+bestaudio/best'
            ],
            "mp3": [
                'bestaudio/best'
            ]
        }

        postprocessors = []
        if format_choice == "mp3":
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })

        return {
            'format': format_priority.get(format_choice, ['bestvideo+bestaudio/best']),
            'postprocessors': postprocessors,
            'merge_output_format': 'mp4' if "mp4" in format_choice else None
        }

    def download_with_fallback(self, ydl, url, formats):
        for format_option in formats:
            ydl.params['format'] = format_option
            try:
                ydl.download([url])
                return True
            except yt_dlp.DownloadError:
                continue
        return False

    def progress_hook(self, d):
        try:
            if d['status'] == 'downloading':
                if 'filename' in d:
                    filename = os.path.basename(d['filename'])
                    self.current_file.set(f"Downloading: {filename}")
                
                if 'downloaded_bytes' in d and 'total_bytes' in d:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    self.progress['value'] = percent
                    self.progress_var.set(f"Progress: {percent:.1f}%")
                elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                    self.progress['value'] = percent
                    self.progress_var.set(f"Progress: {percent:.1f}%")
                else:
                    downloaded = d.get('downloaded_bytes', 0)
                    self.progress_var.set(f"Downloaded: {downloaded/1024/1024:.1f} MB")
            elif d['status'] == 'finished':
                self.progress_var.set("Download finished, processing...")
                self.progress['value'] = 100
                self.successful_downloads += 1
                self.update_download_count()
            self.window.update()
        except Exception as e:
            pass

    def update_download_count(self):
        if self.total_videos > 0:
            self.download_count.set(f"Downloaded: {self.successful_downloads} of {self.total_videos}")

    def log_failed_download(self, video_info):
        if video_info and 'title' in video_info:
            failed_msg = f"Failed: {video_info['title']}\n"
            self.failed_downloads.append(video_info['title'])
            self.failed_list.insert(tk.END, failed_msg)
            self.failed_list.see(tk.END)

    def download_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        try:
            self.successful_downloads = 0
            self.total_videos = 0
            self.failed_downloads = []
            self.failed_list.delete('1.0', tk.END)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                self.progress_var.set("Starting download...")
                
                format_options = self.get_format_options()
                ydl_opts = {
                    'ffmpeg_location': r'C:\\ffmpeg-2024-12-16-git-d2096679d5-full_build\\bin',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'ignoreerrors': True,
                    **{k: v for k, v in format_options.items() if k != 'format'}
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print(f"Attempting formats: {format_options['format']}")  # Debugging info
                    if not self.download_with_fallback(ydl, url, format_options['format']):
                        raise Exception("No formats available or download failed.")
                
                files = os.listdir(temp_dir)
                if not files:
                    raise Exception("No files were downloaded successfully. Please check the URL and try again.")
                
                zip_path = filedialog.asksaveasfilename(
                    defaultextension=".zip",
                    filetypes=[("Zip files", "*.zip")],
                    title="Save Media As"
                )
                
                if zip_path:
                    self.progress_var.set("Creating zip file...")
                    shutil.make_archive(zip_path[:-4], 'zip', temp_dir)
                    
                    status_msg = f"Download completed!\nSuccessfully downloaded: {self.successful_downloads} files.\n"
                    if self.failed_downloads:
                        status_msg += f"Failed downloads: {len(self.failed_downloads)} files.\n"
                    status_msg += f"\nSaved as: {zip_path}"
                    messagebox.showinfo("Success", status_msg)
                else:
                    messagebox.showinfo("Cancelled", "Save operation was cancelled.")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.download_btn['state'] = 'normal'
            self.progress_var.set("Ready to download")
            self.progress['value'] = 0
            self.current_file.set("")

    def start_download(self):
        self.download_btn['state'] = 'disabled'
        self.progress['value'] = 0
        threading.Thread(target=self.download_playlist, daemon=True).start()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.run()
