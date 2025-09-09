import customtkinter
from tkinter import filedialog
import xml.etree.ElementTree as ET
import os

def get_room_count(ytyp_tree):
    """
    Counts and returns the number of rooms (CMloRoomDef) in a YTYP tree.
    """
    if not ytyp_tree:
        return 0
    root = ytyp_tree.getroot()
    room_elements = root.findall('.//rooms/Item')
    return len(room_elements)

def load_probes_folder(app):
    if not app.ytyp_path:
        app.log("Please load a YTYP before loading probes.", "orange")
        return False
    
    path = filedialog.askdirectory(title="Select the Probes source folder")
    if not path: return False
    
    app.probes_entry.configure(state="normal")
    app.probes_entry.delete(0, "end")
    app.probes_entry.insert(0, path)
    app.probes_entry.configure(state="disabled")
    
    probes_found_count = 0
    for root_dir, dirs, files in os.walk(path):
        if root_dir.endswith(os.path.join('ref_probes', 'output')):
            ref_probes_dir = os.path.dirname(root_dir)
            descriptive_name_base = os.path.basename(ref_probes_dir)
            for file in files:
                if file.endswith('_YTYP.xml'):
                    final_name = f"{descriptive_name_base} -- ({file})"
                    try:
                        tree = ET.parse(os.path.join(root_dir, file))
                        if tree.getroot().tag == 'reflectionProbes':
                            app.available_probes[final_name] = tree
                            probes_found_count += 1
                    except ET.ParseError:
                        pass
                        
    if probes_found_count == 0:
        app.log("No valid probes found in the selected folder.", "orange")
    else:
        app.log(f"{probes_found_count} probe(s) found and added to the list.", "green")
    
    build_probe_assignment_ui(app)
    return probes_found_count > 0

def build_probe_assignment_ui(app):
    for widget in app.probe_scrollable_frame.winfo_children():
        widget.destroy()
    app.assignment_widgets = []

    if not app.rooms_list:
        label = customtkinter.CTkLabel(app.probe_scrollable_frame, text="No rooms were found in the YTYP.", text_color="orange")
        label.pack(pady=20)
        return
    if not app.available_probes:
        label = customtkinter.CTkLabel(app.probe_scrollable_frame, text="No probes loaded. Use the buttons above.", text_color="orange")
        label.pack(pady=20)
        return

    for probe_name in sorted(app.available_probes.keys()):
        row_frame = customtkinter.CTkFrame(app.probe_scrollable_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2, padx=5)
        row_frame.grid_columnconfigure(0, weight=2)
        row_frame.grid_columnconfigure(1, weight=1)
        
        label = customtkinter.CTkLabel(row_frame, text=probe_name, anchor='w')
        label.grid(row=0, column=0, sticky="ew", padx=(0,10))
        
        room_options = [""] + app.rooms_list 
        combobox = customtkinter.CTkComboBox(row_frame, 
                                             values=room_options, 
                                             state="readonly",
                                             command=lambda choice, p_name=probe_name: app._save_probe_assignment(p_name, choice))
        combobox.grid(row=0, column=1, sticky="e")
        
        if probe_name in app.probe_assignments:
            combobox.set(app.probe_assignments[probe_name])
        else:
            combobox.set("")
            
        app.assignment_widgets.append({"probe_name": probe_name, "combobox": combobox})

def process_reflection_probes(app):
    if not app.available_probes:
        return app.log("No probes are loaded.", "orange")
    if not app.ytyp_path:
        return app.log("Please load a YTYP file.", "orange")
    
    app.clear_log()
    ytyp_root = app.ytyp_tree.getroot()
    count = 0
    
    for assignment in app.assignment_widgets:
        room_name = assignment["combobox"].get()
        if not room_name:
            continue
        
        probe_name = assignment["probe_name"]
        target_room = next((r for r in ytyp_root.findall('.//rooms/Item') if r.find('name').text == room_name), None)
        
        if target_room is not None:
            probe_to_add = app.available_probes[probe_name].getroot()
            existing_probes = target_room.find('reflectionProbes')
            if existing_probes is not None:
                target_room.remove(existing_probes)
            target_room.append(probe_to_add)
            count += 1
            app.log(f"- {probe_name}  ->  '{room_name}'", "green")
            
    if count > 0:
        app.log(f"\n{count} assignment(s) applied.", "cyan")
        app._save_ytyp()
    else:
        app.log("No assignments were selected to be applied.", "orange")