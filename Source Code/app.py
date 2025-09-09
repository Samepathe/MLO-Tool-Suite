import customtkinter
import tkinter as tk
from tkinter import filedialog
import xml.etree.ElementTree as ET
import os
import textwrap
import sys
import traceback
from pathlib import Path
import webbrowser
from PIL import Image

import module_manifest
import module_autodoor
import module_probes
import assets

if sys.platform == 'win32':
    import ctypes

class RDR2MLOToolSuite(customtkinter.CTk):
    
    VERSION = "v1.0"
    ACTIVE_VIEW_COLOR = "#ff4d4d"
    INACTIVE_VIEW_COLOR = "#565B5E"
    HOVER_COLOR = "#e63939" 

    def __init__(self):
        super().__init__()
        
        self.ytyp_path = None
        self.ytyp_tree = None
        self.rooms_list = []
        self.available_probes = {}
        self.assignment_widgets = []
        self.active_log_widget = None
        self.database_path = module_manifest.find_database_path()
        self.probe_assignments = {}

        self.log_queue = []
        self.is_logging_anim = False
        
        self.title("RedM MLO Tool Suite")
        
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting window icon: {e}")

        self.geometry("710x585")
        self.minsize(710, 585)
        self.configure(fg_color="#2b2b2b")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._create_navigation()
        self._create_ytyp_loader()
        
        self.view_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.view_container.grid(row=2, column=0, padx=10, pady=(5, 5), sticky="nsew")
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

        self._create_manifest_view()
        self._create_autodoor_view()
        self._create_probes_view()
        
        self._create_footer() 
        
        self._display_view_specific_logos()
        self._switch_to_manifest_view()

    def _create_navigation(self):
        nav_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        nav_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.manifest_view_button = customtkinter.CTkButton(nav_frame, text="📃 ┆ _manifest", height=35, command=self._switch_to_manifest_view, hover_color=self.HOVER_COLOR)
        self.manifest_view_button.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.autodoor_view_button = customtkinter.CTkButton(nav_frame, text="🚪 ┆ Door Angle", height=35, command=self._switch_to_autodoor_view, hover_color=self.HOVER_COLOR)
        self.autodoor_view_button.grid(row=0, column=1, sticky="ew", padx=(5,5))
        self.probes_view_button = customtkinter.CTkButton(nav_frame, text="💡 ┆ Deferred Probes", height=35, command=self._switch_to_probes_view, hover_color=self.HOVER_COLOR)
        self.probes_view_button.grid(row=0, column=2, sticky="ew", padx=(5,0))

    def _create_ytyp_loader(self):
        ytyp_load_frame = customtkinter.CTkFrame(self, fg_color="#333333")
        ytyp_load_frame.grid(row=1, column=0, padx=10, pady=0, sticky="ew")
        ytyp_load_frame.grid_columnconfigure(1, weight=1)
        ytyp_load_label = customtkinter.CTkLabel(ytyp_load_frame, text="Ytyp File:")
        ytyp_load_label.grid(row=0, column=0, padx=10, pady=10)
        self.yty_entry = customtkinter.CTkEntry(ytyp_load_frame, state="disabled", placeholder_text="No YTYP file loaded...")
        self.yty_entry.grid(row=0, column=1, sticky="ew", pady=10)
        yty_button = customtkinter.CTkButton(ytyp_load_frame, text="...", width=40, command=self.select_ytyp_file, fg_color=self.INACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR)
        yty_button.grid(row=0, column=2, sticky="e", padx=10, pady=10)

    def _create_manifest_view(self):
        self.manifest_view_frame = customtkinter.CTkFrame(self.view_container, fg_color="transparent")
        self.manifest_view_frame.grid_rowconfigure(1, weight=1)
        self.manifest_view_frame.grid_columnconfigure(0, weight=1)
        imap_frame = customtkinter.CTkFrame(self.manifest_view_frame, fg_color="#333333")
        imap_frame.pack(fill="x")
        imap_frame.grid_columnconfigure(1, weight=1)
        imap_label = customtkinter.CTkLabel(imap_frame, text="Ymap Name:")
        imap_label.grid(row=0, column=0, padx=10, pady=10)
        self.imap_entry = customtkinter.CTkEntry(imap_frame, state="normal", placeholder_text="ex: my_mlo_y")
        self.imap_entry.grid(row=0, column=1, sticky="ew", padx=(0,10), pady=10)
        self.main_log_area = customtkinter.CTkTextbox(self.manifest_view_frame, state="disabled", font=("Courier New", 10))
        self.main_log_area.pack(fill="both", expand=True, pady=(5,0))
        self.main_log_area.tag_config("red", foreground="#ff4d4d")
        self.main_log_area.tag_config("green", foreground="#4CAF50")
        self.main_log_area.tag_config("orange", foreground="orange")
        self.main_log_area.tag_config("cyan", foreground="cyan")
        bottom_frame = customtkinter.CTkFrame(self.manifest_view_frame, fg_color="transparent", height=35)
        bottom_frame.pack(fill="x", pady=(10,0))
        self.generate_ymf_button = customtkinter.CTkButton(bottom_frame, text="Generate .ymf", command=lambda: module_manifest.generate_ymf_action(self), fg_color=self.ACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR, height=35)
        self.generate_ymf_button.place(relx=0.0, rely=0.0, relwidth=0.49)
        self.generate_xml_button = customtkinter.CTkButton(bottom_frame, text="Generate .ymf.pso.xml", command=lambda: module_manifest.generate_ymf_pso_xml_action(self), fg_color=self.ACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR, height=35)
        self.generate_xml_button.place(relx=0.51, rely=0.0, relwidth=0.49)

    def _create_autodoor_view(self):
        self.autodoor_view_frame = customtkinter.CTkFrame(self.view_container, fg_color="transparent")
        self.autodoor_view_frame.grid_rowconfigure(1, weight=1)
        self.autodoor_view_frame.grid_columnconfigure(0, weight=1)
        angle_frame = customtkinter.CTkFrame(self.autodoor_view_frame, fg_color="#333333")
        angle_frame.pack(fill="x")
        angle_frame.grid_columnconfigure(1, weight=1)
        angle_label = customtkinter.CTkLabel(angle_frame, text="Angle Value:")
        angle_label.grid(row=0, column=0, padx=10, pady=10)
        self.angle_value_entry = customtkinter.CTkEntry(angle_frame, state="normal")
        self.angle_value_entry.grid(row=0, column=1, sticky="ew", padx=(0,10), pady=10)
        self.angle_value_entry.insert(0, module_autodoor.AUTODOOR_DEFAULT_VALUE)
        self.autodoor_log_area = customtkinter.CTkTextbox(self.autodoor_view_frame, state="disabled", font=("Courier New", 10))
        self.autodoor_log_area.pack(fill="both", expand=True, pady=(5,0))
        self.autodoor_log_area.tag_config("red", foreground="#ff4d4d")
        self.autodoor_log_area.tag_config("green", foreground="#4CAF50")
        self.autodoor_log_area.tag_config("orange", foreground="orange")
        self.autodoor_log_area.tag_config("cyan", foreground="cyan")
        bottom_frame_door = customtkinter.CTkFrame(self.autodoor_view_frame, fg_color="transparent")
        bottom_frame_door.pack(fill="x", pady=(10,0))
        autodoor_button = customtkinter.CTkButton(bottom_frame_door, text="Correct Angle Value", command=lambda: module_autodoor.run_autodoor_correction(self), height=35, fg_color=self.ACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR)
        autodoor_button.pack(fill="x", expand=True)
        
    def _create_probes_view(self):
        self.probes_view_frame = customtkinter.CTkFrame(self.view_container, fg_color="transparent")
        self.probes_view_frame.grid_columnconfigure(0, weight=1)
        self.probes_view_frame.grid_rowconfigure(2, weight=1) 
        probes_load_frame = customtkinter.CTkFrame(self.probes_view_frame, fg_color="#333333")
        probes_load_frame.grid(row=0, column=0, sticky="ew")
        probes_load_frame.grid_columnconfigure(1, weight=1)
        probes_load_label = customtkinter.CTkLabel(probes_load_frame, text="Def Probes Folder:")
        probes_load_label.grid(row=0, column=0, padx=10, pady=10)
        self.probes_entry = customtkinter.CTkEntry(probes_load_frame, state="disabled", placeholder_text="No folder loaded...")
        self.probes_entry.grid(row=0, column=1, sticky="ew", pady=10)
        probes_load_button = customtkinter.CTkButton(probes_load_frame, text="Load Folder...", width=100, command=lambda: module_probes.load_probes_folder(self), fg_color=self.INACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR)
        probes_load_button.grid(row=0, column=2, sticky="e", padx=10, pady=10)
        self.probes_log_area = customtkinter.CTkTextbox(self.probes_view_frame, state="disabled", font=("Courier New", 10), height=150)
        self.probes_log_area.grid(row=1, column=0, sticky="ew", pady=(5,0))
        self.probes_log_area.tag_config("red", foreground="#ff4d4d")
        self.probes_log_area.tag_config("green", foreground="#4CAF50")
        self.probes_log_area.tag_config("orange", foreground="orange")
        self.probes_log_area.tag_config("cyan", foreground="cyan")
        self.probe_scrollable_frame = customtkinter.CTkScrollableFrame(self.probes_view_frame, fg_color="#1d1e1e")
        self.probe_scrollable_frame.grid(row=2, column=0, sticky="nsew", pady=(5,0))
        bottom_frame_probes = customtkinter.CTkFrame(self.probes_view_frame, fg_color="transparent")
        bottom_frame_probes.grid(row=3, column=0, sticky="ew", pady=(10,0))
        self.process_reflection_button = customtkinter.CTkButton(bottom_frame_probes, text="Assign Deferred Probes", command=lambda: module_probes.process_reflection_probes(self), height=35, fg_color=self.ACTIVE_VIEW_COLOR, hover_color=self.HOVER_COLOR)
        self.process_reflection_button.pack(fill="x", expand=True)

    def _create_footer(self):
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew") 

        version_label = customtkinter.CTkLabel(footer_frame, text=self.VERSION, text_color="gray")
        version_label.pack(side="left", padx=10)

        right_frame = customtkinter.CTkFrame(footer_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=10)
        
        social_links = [
            {"url": "https://discord.gg/TBuEKJVtJc/", "icon": "icon1.png"},
            {"url": "https://alterion-corp.teex.io/", "icon": "icon2.png"},
            {"url": "https://www.youtube.com/@samepathe/videos/", "icon": "icon3.png"}
        ]
        
        assets_path = Path("assets")

        for link in social_links:
            try:
                icon_path = assets_path / link["icon"]
                icon_image = customtkinter.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(24, 24)
                )
                btn = customtkinter.CTkButton(
                    right_frame, image=icon_image, text="", width=27, height=27,
                    fg_color="transparent", hover_color="#555555",
                    command=lambda u=link["url"]: self._open_url(u)
                )
                btn.pack(side="left", padx=5)
            except FileNotFoundError:
                print(f"Error: Icon '{link['icon']}' not found in the 'assets' folder.")
            except Exception as e:
                print(f"Error loading icon '{link['icon']}': {e}")
        
        text_holder_frame = customtkinter.CTkFrame(footer_frame, fg_color="transparent")
        
        made_by_label = customtkinter.CTkLabel(text_holder_frame, text="Made by ")
        made_by_label.pack(side="left")
        
        corp_label = customtkinter.CTkLabel(text_holder_frame, text="Alterion Corp", text_color=self.ACTIVE_VIEW_COLOR)
        corp_label.pack(side="left")

        text_holder_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    def _open_url(self, url):
        webbrowser.open_new_tab(url)

    def _switch_to_manifest_view(self):
        self.autodoor_view_frame.grid_forget()
        self.probes_view_frame.grid_forget()
        self.manifest_view_frame.grid(row=0, column=0, sticky="nsew")
        self.manifest_view_button.configure(fg_color=self.ACTIVE_VIEW_COLOR)
        self.autodoor_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.probes_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.active_log_widget = self.main_log_area

    def _switch_to_autodoor_view(self):
        self.manifest_view_frame.grid_forget()
        self.probes_view_frame.grid_forget()
        self.autodoor_view_frame.grid(row=0, column=0, sticky="nsew")
        self.manifest_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.autodoor_view_button.configure(fg_color=self.ACTIVE_VIEW_COLOR)
        self.probes_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.active_log_widget = self.autodoor_log_area

    def _switch_to_probes_view(self):
        self.manifest_view_frame.grid_forget()
        self.autodoor_view_frame.grid_forget()
        self.probes_view_frame.grid(row=0, column=0, sticky="nsew")
        self.manifest_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.autodoor_view_button.configure(fg_color=self.INACTIVE_VIEW_COLOR)
        self.probes_view_button.configure(fg_color=self.ACTIVE_VIEW_COLOR)
        self.active_log_widget = self.probes_log_area
        
    def _display_view_specific_logos(self):
        current_active_log = self.active_log_widget
        
        self.active_log_widget = self.main_log_area
        self.clear_log()
        self.log_instant(assets.LOGO_MANIFEST)
        
        self.active_log_widget = self.autodoor_log_area
        self.clear_log()
        self.log_instant(assets.LOGO_AUTODOOR)
        
        self.active_log_widget = self.probes_log_area
        self.clear_log()
        self.log_instant(assets.LOGO_PROBES)

        self.active_log_widget = current_active_log

    def select_ytyp_file(self):
        path = filedialog.askopenfilename(title="Select ytyp.rsc.xml file", filetypes=[("YTYP Files", "*.ytyp.rsc.xml")])
        if not path: return
        
        self.yty_entry.configure(state="normal")
        self.yty_entry.delete(0, "end")
        self.yty_entry.insert(0, Path(path).name)
        self.yty_entry.configure(state="disabled")
        
        self.imap_entry.configure(state="normal")
        default_imap_name = os.path.basename(path).replace('.ytyp.rsc.xml', '_y')
        self.imap_entry.delete(0, "end")
        self.imap_entry.insert(0, default_imap_name)

        self.ytyp_path = path
        try:
            self.ytyp_tree = ET.parse(self.ytyp_path)
            
            original_log_widget = self.active_log_widget

            self.active_log_widget = self.main_log_area
            self.clear_log()
            self.log_instant(assets.LOGO_MANIFEST)
            self.log_instant("") 
            main_ityp_name, mlo_collision_name, _ = module_manifest.parse_ytyp(self, self.ytyp_path)
            if mlo_collision_name:
                self.log(f"Parent YTYP: {main_ityp_name}", "cyan")
                self.log(f"Collision name: {mlo_collision_name}", "cyan")

            self.active_log_widget = self.autodoor_log_area
            self.clear_log()
            self.log_instant(assets.LOGO_AUTODOOR)
            self.log_instant("") 
            door_count = module_autodoor.get_door_count(self.ytyp_tree)
            self.log(f"{door_count} door extension(s) (CExtensionDefDoor) detected.", "green")

            self.active_log_widget = self.probes_log_area
            self.clear_log()
            self.log_instant(assets.LOGO_PROBES)
            self.log_instant("") 
            room_count = module_probes.get_room_count(self.ytyp_tree)
            self.log(f"{room_count} room(s) detected in the file.", "green")
            
            self.available_probes.clear()
            self.probe_assignments.clear()
            self.probes_entry.configure(state="normal")
            self.probes_entry.delete(0, "end")
            self.probes_entry.configure(state="disabled")
            
            self.active_log_widget = original_log_widget

            room_elements = self.ytyp_tree.getroot().findall('.//rooms/Item')
            self.rooms_list = sorted([r.find('name').text for r in room_elements if r.find('name') is not None])
            module_probes.build_probe_assignment_ui(self)

        except Exception as e:
            self.log(f"Critical error while reading YTYP: {e}", "red")

    def log_instant(self, message, tags=None):
        if not self.active_log_widget: return
        self.active_log_widget.configure(state="normal")
        self.active_log_widget.insert("end", f"{message}\n", tags)
        self.active_log_widget.see("end")
        self.active_log_widget.configure(state="disabled")

    def log(self, text, tags=None):
        if not self.active_log_widget: return
        target_widget = self.active_log_widget
        self.log_queue.append((target_widget, text, tags))
        if not self.is_logging_anim:
            self._process_log_queue()

    def _process_log_queue(self):
        if self.log_queue:
            self.is_logging_anim = True
            widget, text, tags = self.log_queue.pop(0)
            self._animate_log(widget, text, tags)
        else:
            self.is_logging_anim = False
            
    def _animate_log(self, widget, text, tags=None, index=0):
        if index == 0:
            widget.configure(state="normal")

        if index < len(text):
            char = text[index]
            widget.insert("end", char, tags)
            widget.see("end")
            self.after(5, lambda: self._animate_log(widget, text, tags, index + 1))
        else:
            widget.insert("end", "\n")
            widget.see("end")
            widget.configure(state="disabled")
            self._process_log_queue()

    def clear_log(self):
        if not self.active_log_widget: return
        self.active_log_widget.configure(state="normal")
        self.active_log_widget.delete('1.0', "end")
        self.active_log_widget.configure(state="disabled")

    def _save_ytyp(self):
        if not self.ytyp_path or not self.ytyp_tree: return
        ET.indent(self.ytyp_tree.getroot())
        self.ytyp_tree.write(self.ytyp_path, encoding='UTF-8', xml_declaration=True)
        self.log("YTYP file saved successfully.", "green")
            
    def _save_probe_assignment(self, probe_name, selected_room):
        if selected_room:
            self.probe_assignments[probe_name] = selected_room
        elif probe_name in self.probe_assignments:
            del self.probe_assignments[probe_name]

if __name__ == "__main__":
    try:
        app = RDR2MLOToolSuite()
        app.mainloop()
    except Exception:
        print("--- CRITICAL ERROR ---")
        print(traceback.format_exc())
        input("\nThe script encountered a fatal error. Press Enter to close.")