import dearpygui.dearpygui as dpg
import os, re, json, shutil, sys
from pathlib import Path

packman_home = os.path.expanduser('~/.packman')

# get a list of houdini installs on current machine
def get_houdini_installed_versions():
	installs = []
	
	# windows
	if os.name == 'nt':
		programs = os.listdir('C:/Program Files/Side Effects Software')
		pattern = re.compile(r'Houdini (\d{2})\.(\d)\.(\d{3})')
	
	# linux
	else:
		programs = os.listdir('/opt')
		pattern = re.compile(r'hfs(\d{2})\.(\d)\.(\d{3})')	
	
	for p in programs:
		if pattern.match(p): 
			installs.append(p.replace('hfs', '').replace('Houdini ', ''))

	return sorted(installs, reverse=True)

# creates a home folder to store program data ('~/.packman')
def init_packman_user_folder():
	global packman_home
	if not os.path.isdir(packman_home):
		os.makedirs(packman_home)

# save custom data
def save_prefs(data):
	global packman_home
	prefs_file = os.path.join(packman_home, 'prefs.json')
	with open(prefs_file, 'w') as f:
		json.dump(data, f, indent=4)

# load custom data
def load_prefs():
	global packman_home
	prefs_file = os.path.join(packman_home, 'prefs.json')
	prefs = {}
	if os.path.isfile(prefs_file):
		with open(prefs_file, 'r') as f:
			prefs = json.load(f)
	return prefs

# return available packages from prefs file
def get_available_packages(prefs):
	packages = []
	if 'package_repo' in prefs.keys() and prefs['package_repo'] is not None and prefs['package_repo'] != '':
		packages = [item for item in os.listdir(prefs['package_repo'])]
	return sorted(packages)

# validates a new project before saving (clashing names, all options chosen, etc)
def validate_new_project(glb):
	ret = {'success': True}
	message = 'Could not create project due to errors below:\n'
	configs_folder = os.path.join(packman_home, 'configs')
	config_file = os.path.join(configs_folder, glb['name']+'.json')
	config_file = config_file.replace(' ', '_')
	pattern = re.compile(r'[a-zA-Z0-9\-_\ ]+')
	if glb['name'].strip()=='':
		ret['success'] = False
		message += '- Invalid project name (blank).\n'
	if not re.fullmatch(pattern, glb['name']):
		ret['success'] = False
		message += '- Invalid project name. \n\tallowed chars: \n\t\ta-z \n\t\tA-Z \n\t\t0-9 \n\t\t"-" | "_" | " " (dash, underscore, whitespace).\n'
	if os.path.isfile(config_file) and not glb['edit']:
		ret['success'] = False
		message += '- Config name already exists.\n'
	if 'houdini_version' not in glb.keys():
		ret['success'] = False
		message += '- Houdini version not selected.\n'
	if 'houdini_product' not in glb.keys():
		ret['success'] = False
		message += '- Houdini product not selected.\n'

	ret['message'] = message
	return ret

# saves a new project data inside packman home
def save_config(glb, prefs):
	global packman_home

	archived = glb['archived']
	config={
		'name': glb['name'],
		'archived': archived
	}
	delete_config(config)

	if 'packages' not in glb.keys():
		glb['packages'] = []

	# save .json
	configs_folder = os.path.join(packman_home, 'configs' if not archived else 'archived')
	if not os.path.isdir(configs_folder):
		os.makedirs(configs_folder)
	config_file = os.path.join(configs_folder, glb['name'].strip()+'.json')
	config_file = config_file.replace(' ', '_')
	with open(config_file, 'w') as f:
		json.dump(glb, f, indent=4)

	# save folder with packages copied
	package_repo = prefs['package_repo']
	pkg_folder = glb['name'].strip().replace(' ', '_')
	pkg_folder = os.path.join(configs_folder, pkg_folder)
	if not os.path.isdir(pkg_folder):
		os.makedirs(pkg_folder)
	
	for item in glb['packages']:
		src = os.path.join(package_repo, item)
		dst = os.path.join(pkg_folder, item)
		shutil.copyfile(src, dst)

# gets all the saved configs under packman home
def load_configs():
	global packman_home
	configs = []
	configs_folder = os.path.join(packman_home, 'configs')
	if os.path.isdir(configs_folder):
		for item in sorted(os.listdir(configs_folder)):
			if item.endswith('.json'):
				with open(os.path.join(configs_folder, item), 'r') as f:
					config = json.load(f)
					config['archived'] = False
					configs.append(config)
	return configs

# prettify a config json to be displayed in the UI
def format_config_display(config):
	ret = ''
	ret += f'Houdini {config["houdini_version"]}  ({config["houdini_product"]})    '
	ret += '\nPackages:\n\t' 
	if len(config['packages']):
		ret += '- '
		ret += '\n\t- '.join(config['packages'])
	else:
		ret += '(None)'

	return ret


# archive config (move to "archived" folder)
def archive_config(config):
	global packman_home

	config_name = config['name'].replace(' ', '_')
	configs_folder = os.path.join(packman_home, 'configs')
	archived_folder = os.path.join(packman_home, 'archived')
	
	if not os.path.isdir(archived_folder):
		os.makedirs(archived_folder)

	src = os.path.join(configs_folder, config_name+'.json')
	dst = os.path.join(archived_folder, config_name+'.json')
	shutil.move(src, dst)

	src = os.path.join(configs_folder, config_name)
	dst = os.path.join(archived_folder, config_name)
	shutil.move(src, dst)

# unarchive config (move back to "configs" folder)
def unarchive_config(config):
	global packman_home

	config_name = config['name'].replace(' ', '_')
	configs_folder = os.path.join(packman_home, 'configs')
	archived_folder = os.path.join(packman_home, 'archived')
	
	src = os.path.join(archived_folder, config_name+'.json')
	dst = os.path.join(configs_folder, config_name+'.json')
	shutil.move(src, dst)

	src = os.path.join(archived_folder, config_name)
	dst = os.path.join(configs_folder, config_name)
	shutil.move(src, dst)


# gets all the archived configs under packman home
def load_archived_configs():
	global packman_home
	configs = []
	configs_folder = os.path.join(packman_home, 'archived')
	if os.path.isdir(configs_folder):
		for item in sorted(os.listdir(configs_folder)):
			if item.endswith('.json'):
				with open(os.path.join(configs_folder, item), 'r') as f:
					config = json.load(f)
					config['archived'] = True
					configs.append(config)
	return configs

# delete config (running or archived)
def delete_config(config):
	global packman_home
	config_name = config['name'].replace(' ', '_')
	subfolder = 'configs' if not config['archived'] else 'archived'
	del_json = os.path.join(packman_home, subfolder, config_name+'.json')
	del_folder = os.path.join(packman_home, subfolder, config_name)
	if os.path.isdir(del_folder):
		shutil.rmtree(del_folder)
	if os.path.isfile(del_json):
		os.remove(del_json)

# save dpg init file (window positions, etc)
def save_ui():
	prefs = load_prefs()
	ui = {
		'pos': dpg.get_viewport_pos(),
		'size': (dpg.get_viewport_width(), dpg.get_viewport_height()),
	}
	prefs['ui'] = ui
	save_prefs(prefs)
	dpg.stop_dearpygui()

# load dpg init file 
def load_ui():
	prefs = load_prefs()
	ui = None
	if 'ui' in prefs.keys():
		ui = prefs['ui']

	return ui

# update status text position upon viewport resizing
def update_status_pos():
	dpg.set_item_pos('info_box', (dpg.get_viewport_width()-dpg.get_item_rect_size('info_box')[0]-30, dpg.get_viewport_height()-50))

# update status text and color (and reset alpha)
def show_status(message='', color=(46, 143, 199)):
	dpg.set_value('info_box', message)
	dpg.split_frame()
	dpg.split_frame()
	update_status_pos()
	dpg.configure_item('info_box', color=(color[0], color[1], color[2], 255))

# pyinstaller: get path relative to tmp directory (extracted files) if running from binary
def get_path(relative_path):
	if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
		bundle_dir = Path(sys._MEIPASS)
	else:
		bundle_dir = Path(__file__).parent

	bundle_dir = str(bundle_dir).replace('\\', '/')
	resource_path = f'{bundle_dir}/{relative_path}'
	
	return resource_path

