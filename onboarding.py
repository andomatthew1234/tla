import customtkinter as ctk
from tkinter import filedialog
import subprocess
import threading
import sys
import os
import winreg
import json
import webbrowser

# Safely try to import drag-and-drop functionality
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# --- UI Theme Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if DND_AVAILABLE:
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    RootClass = CTkDnD
else:
    RootClass = ctk.CTk

# --- ToolTip Helper Class ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.schedule_id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        
    def enter(self, event=None):
        self.schedule_id = self.widget.after(400, self.show)
        
    def leave(self, event=None):
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            
    def show(self):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, fg_color="#333333", text_color="white", corner_radius=6, padx=10, pady=5)
        label.pack()


class OnboardingWizard(RootClass):
    def __init__(self):
        super().__init__()

        self.title("ConvertTLA Setup Wizard")
        self.geometry("650x550")
        self.resizable(False, False)

        # Base paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.script_dir, "config.json")

        try:
            self.iconbitmap(os.path.join(self.script_dir, "favicon.ico"))
        except:
            pass

        # Wizard App State Tracking
        self.current_step = 0
        self.steps = [
            self.show_welcome, 
            self.show_checks, 
            self.show_preferences, 
            self.show_integrations, 
            self.show_finish
        ]
        self.step_names = ["Welcome", "System", "Settings", "Integrate", "Finish"]

        # User Configuration Variables
        self.hw_accel_var = ctk.BooleanVar(value=False)
        self.gpu_detected = False
        
        self.theme_var = ctk.StringVar(value="Dark")
        self.save_loc_var = ctk.StringVar(value="Source Folder")
        self.custom_path_var = ctk.StringVar(value="")
        
        self.shortcut_var = ctk.BooleanVar(value=True)
        self.context_menu_var = ctk.BooleanVar(value=True)

        # Layout Hierarchy Fix: Bottom first, then Top, then expanding Middle
        self.navigation_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.navigation_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=30, pady=20)

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(side=ctk.TOP, fill=ctk.X, padx=30, pady=(25, 0))

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, padx=30, pady=10)

        # Permanent Navigation Controls
        self.back_btn = ctk.CTkButton(self.navigation_frame, text="Back", command=self.previous_step, fg_color="#34495E", hover_color="#2C3E50", state="disabled")
        self.back_btn.pack(side=ctk.LEFT)

        self.next_btn = ctk.CTkButton(self.navigation_frame, text="Next", command=self.next_step)
        self.next_btn.pack(side=ctk.RIGHT)

        # Progress bar behind the indicator pills
        self.step_progress = ctk.CTkProgressBar(self.header_frame, height=4, progress_color="#2E86C1", fg_color="#333333")
        self.step_progress.place(relx=0.1, rely=0.4, relwidth=0.8, anchor="w")
        self.step_progress.set(0)

        self.indicator_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.indicator_frame.pack(fill=ctk.X)
        self.indicator_frame.grid_columnconfigure(list(range(len(self.step_names))), weight=1)

        self.step_labels = []
        for i, name in enumerate(self.step_names):
            lbl_container = ctk.CTkFrame(self.indicator_frame, fg_color="transparent")
            lbl_container.grid(row=0, column=i, sticky="n")
            
            lbl = ctk.CTkLabel(lbl_container, text=f" {i+1} ", width=26, height=26, corner_radius=13, 
                               fg_color="#555555", text_color="white", font=ctk.CTkFont(weight="bold"))
            lbl.pack(pady=(0, 5))
            
            desc = ctk.CTkLabel(lbl_container, text=name, font=ctk.CTkFont(size=11), text_color="gray")
            desc.pack()
            
            self.step_labels.append((lbl, desc))

        # Drop-Zone Overlay for Accidental Drags
        self.drop_overlay = ctk.CTkFrame(self, fg_color="#1E1E1E", bg_color="#1E1E1E")
        self.drop_label = ctk.CTkLabel(self.drop_overlay, text="Finish setup first!\nDrop files in the main app.", font=ctk.CTkFont(size=22, weight="bold"), text_color="#E74C3C")
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        
        if DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<DropEnter>>', self.show_overlay)
            self.dnd_bind('<<DropLeave>>', self.hide_overlay)
            self.dnd_bind('<<Drop>>', self.hide_overlay)

        # Render first sequence
        self.current_step_frame = None
        self.update_indicators()
        self.transition_to_step(0, direction=1)

    def show_overlay(self, event):
        self.drop_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.drop_overlay.lift()
        
    def hide_overlay(self, event):
        self.drop_overlay.place_forget()

    def update_indicators(self):
        """Animates the breadcrumb header based on current step."""
        target_progress = self.current_step / (len(self.steps) - 1)
        self.step_progress.set(target_progress)
        
        for i, (lbl, desc) in enumerate(self.step_labels):
            if i < self.current_step:
                lbl.configure(fg_color="#2ECC71", text_color="white") # Completed
                desc.configure(text_color="white")
            elif i == self.current_step:
                lbl.configure(fg_color="#2E86C1", text_color="white") # Active
                desc.configure(text_color="#2E86C1")
            else:
                lbl.configure(fg_color="#555555", text_color="gray") # Pending
                desc.configure(text_color="gray")

    def transition_to_step(self, step_idx, direction=1):
        """Smooth sliding transition between screens."""
        new_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.steps[step_idx](new_frame)
        
        if self.current_step_frame:
            old_frame = self.current_step_frame
            start_x = 0.2 * direction
            new_frame.place(relx=start_x, rely=0, relwidth=1, relheight=1)
            
            def animate(curr_x):
                if abs(curr_x) < 0.01:
                    new_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
                    old_frame.destroy()
                else:
                    next_x = curr_x * 0.7  # Smooth exponential decay
                    new_frame.place(relx=next_x)
                    old_frame.place(relx=next_x - (0.2 * direction))
                    self.after(16, animate, next_x)
                    
            animate(start_x)
        else:
            new_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            
        self.current_step_frame = new_frame

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.update_indicators()
            self.transition_to_step(self.current_step, direction=1)
            self.back_btn.configure(state="normal")
            
            if self.current_step == len(self.steps) - 1:
                self.next_btn.configure(text="Finish")
        else:
            self.save_configuration()
            self.launch_main_app()

    def previous_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.update_indicators()
            self.transition_to_step(self.current_step, direction=-1)
            
            if self.current_step == 0:
                self.back_btn.configure(state="disabled")
            self.next_btn.configure(text="Next", state="normal")

    # --- STEP 1: Welcome Screen ---
    def show_welcome(self, parent):
        title = ctk.CTkLabel(parent, text="Welcome to ConvertTLA", font=ctk.CTkFont(size=26, weight="bold"))
        title.pack(pady=(40, 10))

        tagline = ctk.CTkLabel(parent, text="The Ultimate Desktop Media & Image Converter", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2E86C1")
        tagline.pack(pady=(0, 30))

        description = (
            "This setup wizard will verify your encoding engine, detect hardware\n"
            "acceleration capabilities, and personalize your workspace.\n\n"
            "Click 'Next' to initialize system validation."
        )
        ctk.CTkLabel(parent, text=description, font=ctk.CTkFont(size=13), justify="center").pack(pady=10)

    # --- STEP 2: Verification & Hardware Checks ---
    def show_checks(self, parent):
        self.next_btn.configure(state="disabled")

        title = ctk.CTkLabel(parent, text="System & Hardware Verification", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        self.py_status = ctk.CTkLabel(parent, text="", anchor="w", font=ctk.CTkFont(family="Consolas", size=13))
        self.py_status.pack(fill=ctk.X, padx=40, pady=8)

        self.ff_status = ctk.CTkLabel(parent, text="", anchor="w", font=ctk.CTkFont(family="Consolas", size=13))
        self.ff_status.pack(fill=ctk.X, padx=40, pady=8)

        self.gpu_status = ctk.CTkLabel(parent, text="", anchor="w", font=ctk.CTkFont(family="Consolas", size=13))
        self.gpu_status.pack(fill=ctk.X, padx=40, pady=8)

        self.gpu_opt_in_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.gpu_opt_in_frame.pack(fill=ctk.X, padx=40, pady=10)
        
        self.err_label_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.err_label_container.pack(fill=ctk.X)

        self.checking_active = True
        self.py_done = False
        self.ff_done = False
        self.gpu_done = False
        self.spinner_idx = 0
        
        self.animate_spinners()
        threading.Thread(target=self.run_validation_logic, daemon=True).start()

    def animate_spinners(self):
        """Creates a smooth spinning micro-animation while background threads process."""
        if not hasattr(self, 'checking_active') or not self.checking_active:
            return
            
        chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        char = chars[self.spinner_idx]
        self.spinner_idx = (self.spinner_idx + 1) % len(chars)

        if not self.py_done:
            self.py_status.configure(text=f"{char} Checking Python Runtime Environment...", text_color="#3498DB")
        if not self.ff_done:
            self.ff_status.configure(text=f"{char} Checking FFmpeg Encoding Pipelines...", text_color="#3498DB")
        if not self.gpu_done:
            self.gpu_status.configure(text=f"{char} Scanning for Dedicated GPUs...", text_color="#3498DB")

        self.after(80, self.animate_spinners)

    def run_validation_logic(self):
        # Use cached results if the user clicks 'Back' to prevent rescanning
        if hasattr(self, 'checks_completed') and self.checks_completed:
            self.after(0, lambda: self.update_check_ui(self.cached_py, self.cached_ff, self.cached_gpu))
            return

        py_valid = sys.version_info >= (3, 0)
        self.after(100, lambda: setattr(self, 'py_done', True)) # Slight artificial delay for UX smoothness
        
        ff_valid = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == 'nt' else 0).returncode == 0
        self.after(300, lambda: setattr(self, 'ff_done', True))

        gpu_detected = False
        try:
            creationflags = 0x08000000 if os.name == 'nt' else 0
            wmic_output = subprocess.check_output(["wmic", "path", "win32_VideoController", "get", "name"], text=True, creationflags=creationflags)
            wmic_upper = wmic_output.upper()
            if "NVIDIA" in wmic_upper or "AMD" in wmic_upper or "RADEON" in wmic_upper:
                gpu_detected = True
        except Exception:
            pass
            
        self.after(600, lambda: setattr(self, 'gpu_done', True))

        self.cached_py = py_valid
        self.cached_ff = ff_valid
        self.cached_gpu = gpu_detected
        self.checks_completed = True

        self.after(650, lambda: self.update_check_ui(py_valid, ff_valid, gpu_detected))

    def update_check_ui(self, py, ff, gpu):
        self.checking_active = False 

        if py: self.py_status.configure(text="✅ Python 3 Framework: Operational", text_color="#2ECC71")
        else: self.py_status.configure(text="❌ Python 3 Framework: Error", text_color="#E74C3C")

        if ff: self.ff_status.configure(text="✅ FFmpeg Core: Active", text_color="#2ECC71")
        else: self.ff_status.configure(text="❌ FFmpeg Core: Missing", text_color="#E74C3C")

        if gpu:
            self.gpu_detected = True
            self.hw_accel_var.set(True) 
            self.gpu_status.configure(text="🚀 Hardware Acceleration Detected (NVIDIA/AMD)!", text_color="#F1C40F", font=ctk.CTkFont(family="Consolas", weight="bold", size=13))
            
            ctk.CTkLabel(self.gpu_opt_in_frame, text="Would you like to use your GPU for faster video conversions?").pack(anchor="w")
            
            switch = ctk.CTkSwitch(self.gpu_opt_in_frame, text="Enable Hardware Acceleration (NVENC/AMF)", variable=self.hw_accel_var, progress_color="#2ECC71")
            switch.pack(anchor="w", pady=5)
            ToolTip(switch, "Offloads heavy video encoding algorithms to your dedicated graphics card\nfor massive conversion speed boosts and lower CPU usage.")
        else:
            self.gpu_status.configure(text="ℹ️ Standard Software Encoding Configured.", text_color="gray")

        if py and ff:
            self.next_btn.configure(state="normal")
        else:
            ctk.CTkLabel(self.err_label_container, text="Please run installer.bat to correct missing dependencies.", text_color="#E74C3C", font=ctk.CTkFont(weight="bold")).pack(pady=20)

    # --- STEP 3: User Preferences ---
    def show_preferences(self, parent):
        title = ctk.CTkLabel(parent, text="Personalize ConvertTLA", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        ctk.CTkLabel(parent, text="Default App Theme:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        
        def update_theme(choice):
            ctk.set_appearance_mode(choice)
            
        theme_menu = ctk.CTkOptionMenu(parent, values=["Dark", "Light", "System"], variable=self.theme_var, command=update_theme)
        theme_menu.pack(anchor="w", padx=20, pady=(5, 20))

        ctk.CTkLabel(parent, text="Default Output Folder:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        
        def toggle_custom_path(choice):
            if choice == "Custom Folder...":
                folder = filedialog.askdirectory(title="Select Default Folder")
                if folder:
                    self.custom_path_var.set(folder)
                    self.save_loc_var.set("Custom Folder...")
                else:
                    self.save_loc_var.set("Source Folder") 
            
        loc_menu = ctk.CTkOptionMenu(parent, values=["Source Folder", "Desktop", "Custom Folder..."], variable=self.save_loc_var, command=toggle_custom_path)
        loc_menu.pack(anchor="w", padx=20, pady=5)

        self.custom_path_label = ctk.CTkLabel(parent, textvariable=self.custom_path_var, text_color="gray", font=ctk.CTkFont(size=11))
        self.custom_path_label.pack(anchor="w", padx=20)

    # --- STEP 4: System Integrations ---
    def show_integrations(self, parent):
        title = ctk.CTkLabel(parent, text="System Integrations", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        ctk.CTkLabel(parent, text="How would you like to access ConvertTLA?", font=ctk.CTkFont(size=13)).pack(pady=10)

        ctk.CTkCheckBox(parent, text="Create Desktop Shortcut (.lnk)", variable=self.shortcut_var).pack(pady=15, padx=40, anchor="w")
        
        ctx_desc = "Add 'Convert with ConvertTLA' to Windows Right-Click Menu"
        ctx_box = ctk.CTkCheckBox(parent, text=ctx_desc, variable=self.context_menu_var)
        ctx_box.pack(pady=10, padx=40, anchor="w")
        ctk.CTkLabel(parent, text="  (Allows you to right-click media files and instantly open them in the app)", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=60)
        
        ToolTip(ctx_box, "Writes a secure Windows Registry key so you can right-click\nany media file and send it directly to this application's queue.")

    def build_system_integrations(self):
        if self.shortcut_var.get() and os.name == 'nt':
            try: self.generate_windows_shortcut()
            except Exception as e: print(f"Shortcut Error: {e}")
            
        if self.context_menu_var.get() and os.name == 'nt':
            try: self.generate_context_menu()
            except Exception as e: print(f"Context Menu Error: {e}")

    def generate_windows_shortcut(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                desktop = os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])
        except Exception:
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")

        shortcut_path = os.path.join(desktop, "ConvertTLA.lnk")
        target_script = os.path.join(self.script_dir, "media_converter.py")
        icon_path = os.path.join(self.script_dir, "favicon.ico")

        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
            f"$Shortcut.TargetPath = 'pythonw.exe'; "  
            f"$Shortcut.Arguments = '\"{target_script}\"'; "
            f"$Shortcut.WorkingDirectory = '{self.script_dir}'; "
        )
        if os.path.exists(icon_path):
            ps_cmd += f"$Shortcut.IconLocation = '{icon_path}'; "
            
        ps_cmd += "$Shortcut.Save()"
        subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)

    def generate_context_menu(self):
        target_script = os.path.join(self.script_dir, "media_converter.py")
        icon_path = os.path.join(self.script_dir, "favicon.ico")
        
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe

        command_string = f'"{pythonw_exe}" "{target_script}" "%1"'

        try:
            key_path = r"Software\Classes\*\shell\ConvertTLA"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Convert with ConvertTLA")
                if os.path.exists(icon_path):
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{icon_path}"')
            
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as sub_key:
                winreg.SetValueEx(sub_key, "", 0, winreg.REG_SZ, command_string)
        except Exception as e:
            print(f"Failed to create context menu: {e}")

    # --- STEP 5: Finalization ---
    def save_configuration(self):
        config_data = {
            "theme": self.theme_var.get(),
            "save_location": self.save_loc_var.get(),
            "custom_path": self.custom_path_var.get(),
            "hardware_acceleration": self.hw_accel_var.get()
        }
        
        with open(self.config_path, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
            
        self.build_system_integrations()

    def show_finish(self, parent):
        title = ctk.CTkLabel(parent, text="Configuration Completed!", font=ctk.CTkFont(size=22, weight="bold"), text_color="#2ECC71")
        title.pack(pady=(40, 10))

        desc = (
            "ConvertTLA has been personalized and provisioned.\n\n"
            "Click 'Finish' to exit this setup routine and launch\n"
            "your configured conversion interface."
        )
        ctk.CTkLabel(parent, text=desc, font=ctk.CTkFont(size=13), justify="center").pack(pady=20)
        
        self.next_btn.configure(text="Finish")

    def launch_main_app(self):
        self.destroy()
        
        # Fire off the HTML success sequence in the browser
        html_path = os.path.join(self.script_dir, "finished.html")
        if os.path.exists(html_path):
            webbrowser.open(f"file://{html_path}")

        # Launch the main media converter app
        target_app = os.path.join(self.script_dir, "media_converter.py")
        if os.path.exists(target_app):
            subprocess.Popen([sys.executable, target_app])


if __name__ == "__main__":
    app = OnboardingWizard()
    app.mainloop()