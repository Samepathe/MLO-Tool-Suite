# Fichier : module_manifest.py
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict

def find_database_path():
    """
    Finds the path to the DATA_BASE directory.
    It checks next to the .exe when frozen, or next to the script otherwise.
    """
    try:
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle/frozen (.exe),
            # the base path is the directory of the executable itself.
            base_path = os.path.dirname(sys.executable)
        else:
            # If running as a normal script, the base path is the script's directory.
            base_path = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
        
        db_path = os.path.join(base_path, "DATA_BASE")
        return db_path if os.path.isdir(db_path) else None
    except Exception:
        return None

def generate_ymf_action(app):
    app.clear_log()
    content, save_path_base = process_and_generate_manifest(app)
    if content and save_path_base:
        save_manifest_file(app, content, save_path_base + ".ymf")

def generate_ymf_pso_xml_action(app):
    app.clear_log()
    content, save_path_base = process_and_generate_manifest(app)
    if content and save_path_base:
        save_manifest_file(app, content, save_path_base + ".ymf.pso.xml")

def process_and_generate_manifest(app):
    if not app.database_path:
        app.log("CRITICAL ERROR: 'DATA_BASE' directory not found.", "red")
        app.log("Please make sure it is placed next to the .exe file.", "red")
        return None, None
    if not app.ytyp_path:
        app.log("ERROR: Please select a valid YTYP file.", "red")
        return None, None
    imap_name = app.imap_entry.get()
    if not imap_name:
        app.log("ERROR: Please select a YTYP file and verify the IMAP name.", "red")
        return None, None
    
    app.log("--- Analyzing ---")
    main_ityp, mlo_name, props = parse_ytyp(app, app.ytyp_path)
    if not main_ityp: return None, None

    save_path_base = os.path.join(os.path.dirname(app.ytyp_path), f"_manifest_{main_ityp}")
    prop_to_rpf = build_prop_to_rpf_map(app)
    
    dependencies = OrderedDict([(main_ityp, True)])
    props_not_found = []
    for prop in props:
        if prop in prop_to_rpf:
            dependencies[prop_to_rpf[prop]] = True
        elif not prop.startswith(main_ityp):
            props_not_found.append(prop)

    deps_list = list(dependencies.keys())
    manifest_content = generate_manifest_xml(imap_name, mlo_name, deps_list)
    
    app.log("\nFound ytyp list:")
    for dep in deps_list: app.log(f"  - {dep}")

    if props_not_found:
        app.log(f"\nYTYP not found for {len(props_not_found)} Entities:")
        for p in props_not_found: app.log(f"  - {p}")
        save_missing_props_file(app, props_not_found, save_path_base)
    
    app.log("\n--- Result ---")
    app.log(f"YTYP added: {len(deps_list)}", "green")
    if props_not_found:
        app.log(f"YTYP not found: {len(props_not_found)} Entities", "red")
        app.log("You may have to add them by hand.", "red")
    return manifest_content, save_path_base

def save_missing_props_file(app, missing_props, save_path_base):
    if not missing_props: return
    try:
        manifest_basename = os.path.basename(save_path_base)
        txt_filename = f"missing_ytyp_for_{manifest_basename}.txt"
        txt_save_path = os.path.join(os.path.dirname(save_path_base), txt_filename)
        with open(txt_save_path, 'w', encoding='utf-8') as f:
            f.write("# This file lists all entities for which a parent ytyp was not found in the DATA_BASE.\n")
            f.write("# You may need to find the corresponding ytyp in Codex or else and add them by hand to the _manifest\n\n")
            for prop in missing_props: f.write(prop + '\n')
        app.log(f"\n📝 List of missing props saved to:")
        app.log(f"   '{txt_filename}'")
    except Exception as e:
        app.log(f"\n❌ ERROR while saving missing props file: {e}", "red")

def save_manifest_file(app, content, full_save_path):
    try:
        with open(full_save_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        file_name = os.path.basename(full_save_path)
        app.log(f"\n✅ _manifest '{file_name}' generated successfully!")
    except Exception as e:
        app.log(f"\n❌ ERROR while saving: {e}", "red")
    app.log("------------------")

def parse_ytyp(app, ytyp_path):
    try:
        tree = ET.parse(ytyp_path)
        root = tree.getroot()
        base_name = os.path.basename(ytyp_path)
        main_ityp_name = base_name.replace('.ytyp.rsc.xml', '')
        mlo_archetype = root.find('.//archetypes/Item[@type="CMloArchetypeDef"]/name')
        if mlo_archetype is None:
            app.log("ERROR: Could not find CMloArchetypeDef archetype.", "red")
            return None, None, []
        mlo_collision_name = mlo_archetype.text
        prop_archetypes = root.findall('.//archetypes/Item/entities/Item/archetypeName')
        prop_list = list(OrderedDict.fromkeys([prop.text.strip() for prop in prop_archetypes]))
        return main_ityp_name, mlo_collision_name, prop_list
    except Exception as e:
        app.log(f"Critical error during YTYP parsing: {e}", "red")
        return None, None, []

def build_prop_to_rpf_map(app):
    prop_map = {}
    if not app.database_path: return {}
    for filename in os.listdir(app.database_path):
        if filename.endswith('.xml'):
            file_path = os.path.join(app.database_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f: content = f.read()
                clean_content = re.sub(r'<\?xml.*?\?>', '', content).strip()
                if not clean_content: continue
                rpf_tree = ET.fromstring(clean_content)
                rpf_name = rpf_tree.get('name')
                if rpf_name:
                    for prop_node in rpf_tree.findall('Prop_Name'):
                        if prop_node.text:
                            prop_map[prop_node.text.strip()] = rpf_name.strip()
            except (ET.ParseError, IOError) as file_error:
                app.log(f"Warning: Could not parse {filename}: {file_error}", "red")
    return prop_map

def generate_manifest_xml(imap_name, mlo_collision_name, ityp_dependencies):
    indent = ' ' * 8
    ityp_dep_items = '\n'.join([f"{indent}<Item>{dep}</Item>" for dep in ityp_dependencies])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CPackFileMetaData>
  <MapDataGroups />
  <HDTxdBindingArray />
  <imapDependencies />
  <imapDependencies_2>
    <Item>
      <imapName>{imap_name}</imapName>
      <manifestFlags>INTERIOR_DATA</manifestFlags>
      <itypDepArray>
{ityp_dep_items}
      </itypDepArray>
    </Item>
  </imapDependencies_2>
  <itypDependencies_2 />
  <Interiors>
    <Item>
      <Name>{mlo_collision_name}</Name>
      <Bounds>
        <Item>{mlo_collision_name}</Item>
      </Bounds>
    </Item>
  </Interiors>
  <redm_loves_you_7cc2afb2d40476ed />
  <redm_loves_you_c1fa8cdfbc6c9972 />
  <txdRelationships />
  <imapAliases />
  <assetOwnerMap />
</CPackFileMetaData>
"""

