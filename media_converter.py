import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import sys
import json
import winreg

# Safely try to import drag-and-drop functionality
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# --- UI Theme Configuration (Defaults) ---
ctk.set_appearance_mode("Dark")  # Will be overridden by config.json if present
ctk.set_default_color_theme("blue")

if DND_AVAILABLE:
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    RootClass = CTkDnD
else:
    RootClass = ctk.CTk


class MediaConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ConvertTLA")
        self.root.geometry("750x700")
        
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Apply the favicon
        try:
            self.root.iconbitmap(os.path.join(self.script_dir, "favicon.ico"))
        except Exception:
            pass 

        # Application State
        self.input_files = []
        self.file_checkboxes = []  
        self.output_format = ctk.StringVar(value="mp4")
        self.advanced_format = ctk.StringVar(value="mkv")
        
        # Advanced Settings State
        self.video_crf = ctk.IntVar(value=23) 
        self.audio_bitrate = ctk.IntVar(value=192) 
        
        # Custom Path State
        self.use_custom_folder = ctk.BooleanVar(value=False)
        self.custom_folder_path = ctk.StringVar(value="")
        
        # Hardware Acceleration State
        self.hw_accel_enabled = False

        self.create_widgets()
        self.load_configuration()
        self.handle_context_menu_args()

    def load_configuration(self):
        """Reads config.json and applies user preferences."""
        config_path = os.path.join(self.script_dir, "config.json")
        if not os.path.exists(config_path):
            return # Skip if onboarding hasn't been run

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # 1. Apply Theme
            theme = config.get("theme", "System")
            ctk.set_appearance_mode(theme)

            # 2. Apply Hardware Acceleration
            self.hw_accel_enabled = config.get("hardware_acceleration", False)

            # 3. Apply Save Location Preferences
            save_loc = config.get("save_location", "Source Folder")
            if save_loc == "Desktop":
                self.use_custom_folder.set(True)
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                        desktop = os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])
                except Exception:
                    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
                self.custom_folder_path.set(desktop)
                
            elif save_loc == "Custom Folder...":
                self.use_custom_folder.set(True)
                self.custom_folder_path.set(config.get("custom_path", ""))
                
            else:
                self.use_custom_folder.set(False)

            # Sync UI elements with loaded state
            self.toggle_custom_folder()

        except Exception as e:
            self.log_message(f"Notice: Failed to load config.json properly. {str(e)}\n")

    def handle_context_menu_args(self):
        """Processes files passed in via Windows Right-Click Context Menu."""
        if len(sys.argv) > 1:
            for file_path in sys.argv[1:]:
                if os.path.exists(file_path):
                    self.add_file_to_ui(file_path)
            self.log_message(f"Loaded {len(sys.argv)-1} file(s) from Windows Context Menu.\n")

    def create_widgets(self):
        # --- Title ---
        title_label = ctk.CTkLabel(self.root, text="ConvertTLA", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(15, 5))

        # --- File Selection / Drag & Drop Frame ---
        file_frame = ctk.CTkFrame(self.root)
        file_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=False)

        ctk.CTkLabel(file_frame, text="Input Files (Drag & Drop anywhere to add):", font=ctk.CTkFont(weight="bold")).pack(anchor=ctk.W, padx=10, pady=5)
        
        self.scroll_frame = ctk.CTkScrollableFrame(file_frame, height=150)
        self.scroll_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=10, pady=10)

        # Buttons for File Management
        btn_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
        btn_frame.pack(side=ctk.RIGHT, padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Browse Files", command=self.add_files).pack(pady=5)
        ctk.CTkButton(btn_frame, text="Remove Checked", command=self.remove_selected, fg_color="#E74C3C", hover_color="#C0392B").pack(pady=5)
        ctk.CTkButton(btn_frame, text="Clear All", command=self.clear_files, fg_color="#34495E", hover_color="#2C3E50").pack(pady=5)

        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.handle_drop)
        else:
            self.log_message("Notice: tkinterdnd2 not installed. Drag-and-drop disabled.\n")

        # --- Format Selection Frame ---
        format_frame = ctk.CTkFrame(self.root)
        format_frame.pack(pady=(10, 0), padx=20, fill=ctk.X)

        ctk.CTkLabel(format_frame, text="Target Format:", font=ctk.CTkFont(weight="bold")).pack(side=ctk.LEFT, padx=10, pady=10)
        
        self.all_formats = ["mkv", "webm", "mov", "gif", "aac", "flac", "ogg", "m4a", "jpeg", "webp", "ico", "bmp", "tiff"]
        
        self.main_combo = ctk.CTkComboBox(format_frame, variable=self.output_format, command=self.on_format_change, state="readonly")
        self.main_combo.pack(side=ctk.LEFT, padx=5)

        self.adv_combo = ctk.CTkComboBox(format_frame, values=self.all_formats, variable=self.advanced_format, state="readonly")
        
        self.adv_settings_btn = ctk.CTkButton(format_frame, text="⚙️ Advanced Options", width=140, command=self.open_advanced_settings, fg_color="#5D6D7E", hover_color="#34495E")
        self.adv_settings_btn.pack(side=ctk.RIGHT, padx=10, pady=10)

        # --- Custom Save Location Frame ---
        location_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        location_frame.pack(pady=5, padx=20, fill=ctk.X)

        self.custom_folder_cb = ctk.CTkCheckBox(location_frame, text="Save to custom folder", variable=self.use_custom_folder, command=self.toggle_custom_folder)
        self.custom_folder_cb.pack(side=ctk.LEFT, padx=(10, 5))

        self.browse_folder_btn = ctk.CTkButton(location_frame, text="Select Folder", command=self.select_custom_folder, state=ctk.DISABLED, width=100)
        self.browse_folder_btn.pack(side=ctk.LEFT, padx=5)

        self.folder_label = ctk.CTkLabel(location_frame, textvariable=self.custom_folder_path, text_color="gray", font=ctk.CTkFont(size=11))
        self.folder_label.pack(side=ctk.LEFT, padx=10)

        # --- Action Frame ---
        action_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        action_frame.pack(pady=5, padx=20, fill=ctk.X)

        self.convert_btn = ctk.CTkButton(action_frame, text="Convert All", command=self.start_conversion, font=ctk.CTkFont(size=14, weight="bold"), height=40)
        self.convert_btn.pack(side=ctk.LEFT, padx=5)

        self.progress = ctk.CTkProgressBar(action_frame, mode='determinate')
        self.progress.pack(side=ctk.LEFT, padx=15, fill=ctk.X, expand=True)
        self.progress.set(0)

        # --- Status Log Frame ---
        log_frame = ctk.CTkFrame(self.root)
        log_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
        
        ctk.CTkLabel(log_frame, text="Terminal Log:", font=ctk.CTkFont(weight="bold")).pack(anchor=ctk.W, padx=10, pady=(5, 0))

        self.log_text = ctk.CTkTextbox(log_frame, state=ctk.DISABLED, text_color="#00FF00", fg_color="#1E1E1E", font=ctk.CTkFont(family="Consolas", size=11))
        self.log_text.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        self.update_dropdown_options()

    # --- UI Logic ---
    def on_format_change(self, choice):
        if choice == "Advanced...":
            self.adv_combo.pack(side=ctk.LEFT, padx=5)
        else:
            self.adv_combo.pack_forget()

    def toggle_custom_folder(self):
        if self.use_custom_folder.get():
            self.browse_folder_btn.configure(state=ctk.NORMAL)
        else:
            self.browse_folder_btn.configure(state=ctk.DISABLED)

    def select_custom_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.custom_folder_path.set(folder)

    def open_advanced_settings(self):
        top = ctk.CTkToplevel(self.root)
        top.title("Advanced Conversion Options")
        top.geometry("400x320")
        top.attributes("-topmost", True)
        try:
            top.iconbitmap(os.path.join(self.script_dir, "favicon.ico"))
        except: pass
        
        ctk.CTkLabel(top, text="Video Quality (CRF)", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(20, 0))
        ctk.CTkLabel(top, text="Lower value = Better Quality, Larger File (Default: 23)", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=0)
        
        crf_val_label = ctk.CTkLabel(top, text=str(self.video_crf.get()), font=ctk.CTkFont(weight="bold"))
        crf_val_label.pack(pady=(5,0))
        
        def update_crf_label(val):
            self.video_crf.set(int(val))
            crf_val_label.configure(text=str(int(val)))

        crf_slider = ctk.CTkSlider(top, from_=0, to=51, command=update_crf_label)
        crf_slider.set(self.video_crf.get())
        crf_slider.pack(pady=(0, 20), padx=30, fill=ctk.X)

        ctk.CTkLabel(top, text="Audio Bitrate (kbps)", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(10, 0))
        ctk.CTkLabel(top, text="Higher value = Better Audio (Default: 192 kbps)", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=0)
        
        abr_val_label = ctk.CTkLabel(top, text=f"{self.audio_bitrate.get()} kbps", font=ctk.CTkFont(weight="bold"))
        abr_val_label.pack(pady=(5,0))

        def update_abr_label(val):
            self.audio_bitrate.set(int(val))
            abr_val_label.configure(text=f"{int(val)} kbps")

        abr_slider = ctk.CTkSlider(top, from_=64, to=320, number_of_steps=8, command=update_abr_label)
        abr_slider.set(self.audio_bitrate.get())
        abr_slider.pack(pady=(0, 10), padx=30, fill=ctk.X)
        
        ctk.CTkButton(top, text="Done", command=top.destroy, width=100).pack(pady=10)

    def update_dropdown_options(self):
        video_exts = {".mp4", ".avi", ".mkv", ".webm", ".mov", ".gif"}
        audio_exts = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".bmp", ".tiff"}

        std_video = ["mp4", "avi", "mov", "mkv"]
        std_audio = ["mp3", "wav", "aac", "flac"]
        std_image = ["jpg", "png", "webp", "ico"]

        has_video = False
        has_audio = False
        has_image = False

        for f in self.input_files:
            ext = os.path.splitext(f)[1].lower()
            if ext in video_exts: has_video = True
            elif ext in audio_exts: has_audio = True
            elif ext in image_exts: has_image = True

        if has_image and not has_video and not has_audio:
            formats = std_image.copy()
        elif has_audio and not has_video and not has_image:
            formats = std_audio.copy()
        elif has_video and not has_image:
            formats = std_video + std_audio
        else:
            formats = ["mp4", "mp3", "jpg"]

        formats.append("Advanced...")
        self.main_combo.configure(values=formats)
        
        current_val = self.output_format.get()
        if current_val not in formats:
            new_default = formats[0]
            self.output_format.set(new_default)
            self.on_format_change(new_default) 

    # --- File Management Methods ---
    def add_file_to_ui(self, path):
        if path not in self.input_files:
            self.input_files.append(path)
            cb = ctk.CTkCheckBox(self.scroll_frame, text=os.path.basename(path))
            cb.pack(anchor="w", pady=4, padx=5)
            cb.select() 
            self.file_checkboxes.append((path, cb))
        self.update_dropdown_options()

    def add_files(self):
        filetypes = (
            ("All Supported Formats", "*.mp4 *.avi *.mkv *.webm *.mov *.gif *.mp3 *.wav *.aac *.flac *.ogg *.m4a *.png *.jpg *.jpeg *.webp *.ico *.bmp *.tiff"),
            ("Video Files", "*.mp4 *.avi *.mkv *.webm *.mov *.gif"),
            ("Audio Files", "*.mp3 *.wav *.aac *.flac *.ogg *.m4a"),
            ("Image Files", "*.png *.jpg *.jpeg *.webp *.ico *.bmp *.tiff"),
            ("All files", "*.*")
        )
        
        filepaths = filedialog.askopenfilenames(title="Select Media or Image Files", filetypes=filetypes)
        for path in filepaths:
            self.add_file_to_ui(path)

    def handle_drop(self, event):
        filepaths = self.root.tk.splitlist(event.data)
        for path in filepaths:
            self.add_file_to_ui(path)

    def remove_selected(self):
        to_remove = []
        for filepath, cb in self.file_checkboxes:
            if cb.get(): 
                to_remove.append((filepath, cb))
                
        for filepath, cb in to_remove:
            cb.destroy()
            self.file_checkboxes.remove((filepath, cb))
            self.input_files.remove(filepath)
            
        self.update_dropdown_options()

    def clear_files(self):
        for filepath, cb in self.file_checkboxes:
            cb.destroy()
        self.file_checkboxes.clear()
        self.input_files.clear()
        self.update_dropdown_options()

    # --- Logging & UI Updates ---
    def log_message(self, message):
        def append():
            self.log_text.configure(state=ctk.NORMAL)
            self.log_text.insert(ctk.END, message)
            self.log_text.see(ctk.END)
            self.log_text.configure(state=ctk.DISABLED)
        self.root.after(0, append)

    def update_progress(self, value, maximum):
        def set_prog():
            progress_ratio = value / maximum if maximum > 0 else 0
            self.progress.set(progress_ratio)
        self.root.after(0, set_prog)

    # --- Conversion Logic ---
    def start_conversion(self):
        selected_format = self.output_format.get()
        if selected_format == "Advanced...":
            target_ext = self.advanced_format.get()
        else:
            target_ext = selected_format

        if not self.input_files:
            messagebox.showerror("Error", "Please add at least one file to convert.")
            return

        if self.use_custom_folder.get() and not self.custom_folder_path.get():
            messagebox.showerror("Error", "Custom save location is enabled but no folder is selected.")
            return

        self.convert_btn.configure(state=ctk.DISABLED)
        self.log_text.configure(state=ctk.NORMAL)
        self.log_text.delete(1.0, ctk.END)
        self.log_text.configure(state=ctk.DISABLED)
        self.progress.set(0)

        threading.Thread(target=self.process_batch, args=(target_ext,), daemon=True).start()

    def process_batch(self, output_ext):
        total_files = len(self.input_files)
        success_count = 0
        error_count = 0

        for index, input_path in enumerate(self.input_files):
            self.update_progress(index, total_files)
            
            if not os.path.exists(input_path):
                self.log_message(f"Skipping {input_path} - File not found.\n")
                error_count += 1
                continue

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            if self.use_custom_folder.get() and self.custom_folder_path.get():
                output_dir = self.custom_folder_path.get()
            else:
                output_dir = os.path.dirname(input_path)
                
            output_path = os.path.join(output_dir, f"{base_name}_converted.{output_ext}")

            cmd = ["ffmpeg", "-y"]
            
            # Smart Hardware Acceleration Injection
            if self.hw_accel_enabled:
                cmd.extend(["-hwaccel", "auto"])
                
            cmd.extend(["-i", input_path])
            
            # Smart flags application
            if output_ext == "ico":
                cmd.extend(["-vf", "scale=256:256"])
            elif output_ext in ["mp4", "mkv", "webm", "mov", "avi"]:
                cmd.extend(["-crf", str(self.video_crf.get())])
                
            if output_ext in ["mp4", "mkv", "webm", "mov", "avi", "mp3", "aac", "ogg", "m4a"]:
                cmd.extend(["-b:a", f"{self.audio_bitrate.get()}k"])
                
            cmd.append(output_path)
            
            self.log_message(f"[{index + 1}/{total_files}] Executing: {' '.join(cmd)}\n{'-'*50}\n")

            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, creationflags=creationflags
                )

                no_audio_error = False
                for line in process.stdout:
                    self.log_message(line)
                    if "Output file does not contain any stream" in line:
                        no_audio_error = True

                process.wait()

                if process.returncode == 0:
                    self.log_message(f"\n{'-'*50}\nSuccess: {os.path.basename(output_path)}\n\n")
                    success_count += 1
                else:
                    self.log_message(f"\n{'-'*50}\nFailed: {os.path.basename(input_path)}\n\n")
                    error_count += 1
                    if no_audio_error:
                        self.root.after(0, lambda p=input_path: messagebox.showwarning(
                            "Audio Missing", 
                            f"Failed to convert:\n{os.path.basename(p)}\n\nCannot convert to audio format because the source file has no audio track."
                        ))

            except FileNotFoundError:
                self.log_message("\nCRITICAL ERROR: FFmpeg not found in system PATH.\n")
                self.root.after(0, lambda: messagebox.showerror("Error", "FFmpeg is missing from PATH."))
                break 
            except Exception as e:
                self.log_message(f"\nUnexpected error: {str(e)}\n")
                error_count += 1

        self.update_progress(total_files, total_files)
        self.root.after(0, lambda: self.finish_gui(success_count, error_count, total_files))

    def finish_gui(self, success, errors, total):
        self.convert_btn.configure(state=ctk.NORMAL)
        msg = f"Batch Complete!\n\nSuccessfully converted: {success} of {total}"
        if errors > 0:
            msg += f"\nFailed: {errors} (Check log for details)"
            messagebox.showwarning("Finished with Errors", msg)
        else:
            messagebox.showinfo("Success", msg)


if __name__ == "__main__":
    root = RootClass()
    app = MediaConverterApp(root)
    root.mainloop()