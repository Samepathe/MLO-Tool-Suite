# Fichier : module_autodoor.py
import re
import xml.etree.ElementTree as ET
import traceback

AUTODOOR_DEFAULT_VALUE = "1.470796"

def get_door_count(ytyp_tree):
    """
    Counts and returns the number of CExtensionDefDoor elements in a YTYP tree.
    """
    if not ytyp_tree:
        return 0
    root = ytyp_tree.getroot()
    door_extensions = root.findall(".//Item[@type='CExtensionDefDoor']")
    return len(door_extensions)

def run_autodoor_correction(app):
    if not app.ytyp_path:
        return app.log("Please load a YTYP file first!", "orange")

    app.clear_log()
    app.log("--- Starting Door Correction ---", "cyan")
    
    angle_value_str = app.angle_value_entry.get()
    if not angle_value_str:
        angle_value_str = AUTODOOR_DEFAULT_VALUE
        app.log(f"No value entered, using default: {angle_value_str}", "orange")
    
    try:
        float(angle_value_str) 
    except ValueError:
        return app.log(f"ERROR: '{angle_value_str}' is not a valid numerical value.", "red")

    try:
        tree = ET.parse(app.ytyp_path)
        root = tree.getroot()
        
        modifications_made = False
        
        parent_map = {c: p for p in root.iter() for c in p}
        
        door_extensions = root.findall(".//Item[@type='CExtensionDefDoor']")
        app.log(f"\n{len(door_extensions)} door extension(s) (CExtensionDefDoor) detected.", "green")
        
        limit_angle_elements = root.findall(".//limitAngle")
        if limit_angle_elements:
            app.log("\n--- Rule #1: Converting <limitAngle> ---", "cyan")
            for limit_angle_element in limit_angle_elements:
                parent_item = parent_map.get(limit_angle_element)
                if parent_item is None or parent_item.tag != 'Item': continue

                archetype_name_element = parent_item.find('name')
                if archetype_name_element is not None:
                    archetype_name = archetype_name_element.text
                    value = limit_angle_element.get('value')
                    
                    app.log(f"\n<archetypeName>{archetype_name}</archetypeName>")
                    app.log(f'  <limitAngle value="{value}" />', "orange")
                    app.log("  changed to:")

                    idx = list(parent_item).index(limit_angle_element)
                    parent_item.remove(limit_angle_element)
                    new_elem1 = ET.Element("nbjubyaa_0xcfe37bdb", value=value)
                    new_elem2 = ET.Element("gfkrydta_0xa0cf3c8d", value=value)
                    parent_item.insert(idx, new_elem2)
                    parent_item.insert(idx, new_elem1)
                    
                    modifications_made = True
                    
                    app.log(f'    <nbjubyaa_0xcfe37bdb value="{value}" />', "green")
                    app.log(f'    <gfkrydta_0xa0cf3c8d value="{value}" />', "green")
        
        false_value_elements = root.findall(".//*[@value='false']")
        archetypes_to_update = {}
        for element in false_value_elements:
            if element.tag in ["nbjubyaa_0xcfe37bdb", "gfkrydta_0xa0cf3c8d"]:
                parent_archetype = parent_map.get(element)
                if parent_archetype is not None and parent_archetype.tag == 'Item':
                    if parent_archetype not in archetypes_to_update:
                        archetypes_to_update[parent_archetype] = []
                    archetypes_to_update[parent_archetype].append(element)

        if archetypes_to_update:
            app.log("\n--- Rule #2: Updating value=\"false\" ---", "cyan")
            app.log(f"\nCExtensionDefDoor")
            for archetype, elements in archetypes_to_update.items():
                archetype_name = archetype.find('name').text
                app.log(f"<archetypeName>{archetype_name}</archetypeName>")
                
                for element in elements:
                    app.log(f'  <{element.tag} value="false" />', "orange")
                    element.set("value", angle_value_str)
                    modifications_made = True
                
                app.log("  value changed to:")
                app.log(f'    <... value="{angle_value_str}" />', "green")

        if modifications_made:
            ET.indent(root)
            tree.write(app.ytyp_path, encoding='UTF-8', xml_declaration=True)
            app.log("\nCorrection finished and YTYP file saved.", "green")
            app.ytyp_tree = ET.parse(app.ytyp_path)
        else:
            app.log("\nNo modifications were made, angle values seem correct.", "cyan")

    except Exception as e:
        app.log(f"An unexpected error occurred: {e}", "red")
        traceback.print_exc()