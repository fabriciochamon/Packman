import dearpygui.dearpygui as dpg
import utils, os, subprocess

dpg.create_context()

# init packman
utils.init_packman_user_folder()
prefs = utils.load_prefs()
glb = {}

# --------- CALLBACKS --------- #

# toggle off all buttons within "add project" window
def toggle_off_all_buttons(name_prefix):
	index = 0
	while dpg.does_item_exist(f'{name_prefix}--{index}'):
		tag = f'{name_prefix}--{index}'
		dpg.bind_item_theme(tag, 'toogle_OFF')
		index += 1

# handles single/multi-selection toggles within "add project" window
def project_set_item(sender, app_data, user_data):
	global glb
	k = user_data[0]
	v = user_data[1]

	# handles multi-selection toogles
	if len(user_data) > 2 and user_data[2]:

		if k in glb.keys():

			isOFF = v not in glb[k]

			if isOFF:
				glb[k].append(v)
				dpg.bind_item_theme(sender, 'toogle_ON')
			else:
				try:
					del glb[k][glb[k].index(v)]
				except:
					pass
				dpg.bind_item_theme(sender, 'toogle_OFF')
		else:
			glb[k] = [v]
			dpg.bind_item_theme(sender, 'toogle_ON')

	# handles single-selection toogles
	else:
		glb[k] = v
		prefix = sender.split('--')[0]
		toggle_off_all_buttons(prefix)
		dpg.bind_item_theme(sender, 'toogle_ON')

# save package repo in prefs.json upon folder selection
def set_packages_repo(sender, app_data):
	global prefs

	folder = app_data['file_path_name']
	prefs['package_repo'] = folder
	utils.save_prefs(prefs)
	dpg.hide_item('package_repo_fb')
	dpg.set_value('package_repo_tooltip', f'Currently set to: \n{folder}')
	utils.show_status(f'Package repository set to: {folder}', color=(247, 207, 2))

# show add project window
def show_project_window(sender=None, app_data=None, user_data=None, edit=False, config=None):
	global glb
	glb['edit'] = edit
	button_groups=['houdini_version','houdini_product','packages']

	if not edit:
		dpg.configure_item('project_name', enabled=True)
		dpg.bind_item_theme('project_name', None)
		for btn_grp in button_groups:
			toggle_off_all_buttons(btn_grp)
		dpg.set_value('project_name', 'new project')
		if 'name' in glb.keys(): del glb['name']
		if 'houdini_version' in glb.keys(): del glb['houdini_version']
		if 'houdini_product' in glb.keys(): del glb['houdini_product']
		if 'packages' in glb.keys(): del glb['packages']
		glb['archived'] = False
		dpg.focus_item('project_name')
	else:
		dpg.configure_item('project_name', enabled=False)
		dpg.bind_item_theme('project_name', 'disabled_input_text')
		glb['name'] = config['name']
		glb['houdini_version'] = config['houdini_version']
		glb['houdini_product'] = config['houdini_product']
		glb['packages'] = config['packages']
		glb['archived'] = config['archived']
		dpg.set_value('project_name', config['name'])
		for btn_grp in button_groups:
			toggle_off_all_buttons(btn_grp)
			buttons = dpg.get_item_children(f'grp_{btn_grp}')[1]
			for btn in buttons:
				value = dpg.get_item_user_data(btn)[1]
				if value in glb[btn_grp]:
					dpg.bind_item_theme(btn, 'toogle_ON')
		
	dpg.show_item('add_project_win')
	size_item('add_project_win', 0.8, 0.8)
	center_item('add_project_win')

# saves new project configuration
def save_config():
	global glb, prefs
	glb['name'] = dpg.get_value('project_name')
	validation = utils.validate_new_project(glb)
	if validation['success']:
		utils.save_config(glb, prefs)
		dpg.hide_item('add_project_win')
		rebuild_config_list()
		status = 'created' if not glb['edit'] else 'edited successfully'
		utils.show_status(f'Project \"{glb["name"]}\" {status}.')
	else:
		dpg.set_value('ed_message', validation['message'])
		dpg.show_item('ed')
		center_item('ed')

# houdini loader for current clicked config
def launch_config(sender, app_data, user_data):
	config = user_data
	env = os.environ.copy()
	packman_home = utils.packman_home
	subfolder = 'configs' if not config['archived'] else 'archived'
	packages_path = os.path.join(packman_home, subfolder, config['name'].replace(' ', '_'))
	env['HOUDINI_PACKAGE_DIR'] = packages_path
	env['HOUDINI_SPLASH_MESSAGE'] = f'Packman enviroment: \"{config["name"]}\"'
	#env['HOUDINI_SPLASH_FILE'] = ''
	houdini_path = os.path.join('/opt', 'hfs'+config['houdini_version'], 'bin')
	product = ''
	if config['houdini_product'] == 'Core':
		product='-core'
	if config['houdini_product'] == 'Indie':
		product='-indie'
	cmd = f'{houdini_path}/houdini {product}'
	utils.show_status(f'Launching \"{config["name"]}\"...', color=(64, 207, 102))
	subprocess.Popen(cmd.split(), env=env)

# center widget on main window
def center_item(tag, offsetX=0, offsetH=0):
	dpg.split_frame()
	dpg.split_frame()
	w = dpg.get_item_rect_size(tag)[0]
	h = dpg.get_item_rect_size(tag)[1]
	pw = dpg.get_item_rect_size('mainwin')[0]
	ph = dpg.get_item_rect_size('mainwin')[1]
	posx = (pw-w)/2
	posy = (ph-h)/2
	dpg.set_item_pos(tag, (posx+offsetX, posy+offsetH))

# resize widget to fit X% of parent's size
def size_item(tag, percentW, percentH):
	dpg.split_frame()
	dpg.split_frame()
	pw = dpg.get_item_rect_size('mainwin')[0]
	ph = dpg.get_item_rect_size('mainwin')[1]
	dpg.set_item_width(tag, pw*percentW)
	dpg.set_item_height(tag, ph*percentH)

# display confirmation dialog for archiving/deleting configs
def show_confirmation_dialog(config, action_name):
	name = config['name']
	config['do_action'] = True
	callbacks={
		'archive':   config_archive,
		'unarchive': config_unarchive, 
		'delete':    config_delete,
	}
	dpg.set_value('cd_message', f'Do you really want to {action_name} "{name}" ?')
	dpg.set_item_user_data('cd_btn_ok', config)
	dpg.set_item_callback('cd_btn_ok', callbacks[action_name])
	dpg.show_item('cd')
	center_item('cd')

# edit current config
def config_edit(sender, app_data, user_data):
	show_project_window(edit=True, config=user_data)

# archive current config
def config_archive(sender, app_data, user_data):
	config = user_data.copy()
	if 'do_action' in config.keys() and config['do_action']:
		del config['do_action']
		dpg.hide_item('cd')
		utils.archive_config(config)
		rebuild_config_list()
		utils.show_status(f'Project \"{config["name"]}\" was archived.')
	else:
		show_confirmation_dialog(config, 'archive')

# unarchive current config
def config_unarchive(sender, app_data, user_data):
	config = user_data.copy()
	if 'do_action' in config.keys() and config['do_action']:
		del config['do_action']
		dpg.hide_item('cd')
		utils.unarchive_config(config)
		rebuild_config_list()
		utils.show_status(f'Project \"{config["name"]}\" was restored.')
	else:
		show_confirmation_dialog(config, 'unarchive')

# delete current config
def config_delete(sender, app_data, user_data):
	config = user_data.copy()
	if 'do_action' in config.keys() and config['do_action']:
		del config['do_action']
		dpg.hide_item('cd')
		utils.delete_config(config)
		rebuild_config_list()
		utils.show_status(f'Project \"{config["name"]}\" was deleted!', color=(245, 78, 78))
	else:
		show_confirmation_dialog(config, 'delete')

# refresh main configs list
def rebuild_config_list():
	groups = ['all_running_configs', 'all_archived_configs']
	for grp in groups:
		archived = grp=='all_archived_configs'
		dpg.delete_item(grp, children_only=True)
		configs = utils.load_configs() if not archived else utils.load_archived_configs()
		for config in configs:
			name = config['name']
			with dpg.group(horizontal=True, parent=grp):
				btn_load = dpg.add_button(label=name, user_data=config, width=-1, callback=launch_config)
				
				with dpg.popup(btn_load, mousebutton=dpg.mvMouseButton_Right):
					
					btn = dpg.add_button(label='Edit', width=100, user_data=config, callback=config_edit)
					dpg.bind_item_theme(btn, 'config_edit_buttons_theme')
					dpg.bind_item_font(btn, font_small)

					btn = dpg.add_button(label='Archive' if not archived else 'Unarchive', width=100, user_data=config, callback=config_archive if not archived else config_unarchive)
					dpg.bind_item_theme(btn, 'config_edit_buttons_theme')
					dpg.bind_item_font(btn, font_small)

					btn = dpg.add_button(label='Delete', width=100, user_data=config, callback=config_delete)
					dpg.bind_item_theme(btn, 'config_edit_buttons_theme')
					dpg.bind_item_font(btn, font_small)

				dpg.bind_item_theme(btn_load, 'big_buttons_theme' if not archived else 'big_buttons_archived_theme')
				dpg.bind_item_font(btn_load, font_big)
				with dpg.tooltip(parent=btn_load, delay=0.4):
					dpg.add_text(utils.format_config_display(config), indent=20)


# --------- CALLBACKS --------- #

#dpg.show_style_editor()

# set UI font
with dpg.font_registry():
	font_path = utils.get_path('./font/Zain-Regular.ttf')
	font_small  = dpg.add_font(font_path, 26)
	font_medium = dpg.add_font(font_path, 30)
	font_large  = dpg.add_font(font_path, 40)
	font_big    = dpg.add_font(font_path, 50)
dpg.bind_font(font_medium)

# load UI images
with dpg.texture_registry():
	width, height, channels, data = dpg.load_image(utils.get_path('./images/warning.png'))
	dpg.add_static_texture(width=width, height=height, default_value=data, tag='img_warning')
	width, height, channels, data = dpg.load_image(utils.get_path('./images/error.png'))
	dpg.add_static_texture(width=width, height=height, default_value=data, tag='img_error')

# --- THEMES --- #
with dpg.theme(tag='big_buttons_theme'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 30, category=dpg.mvThemeCat_Core)

with dpg.theme(tag='big_buttons_archived_theme'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_Text, (100,100,100), category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 30, category=dpg.mvThemeCat_Core)

with dpg.theme(tag='big_buttons_action_theme'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 30, category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (50, 168, 82), category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (50, 168, 82), category=dpg.mvThemeCat_Core)

with dpg.theme(tag='toogle_OFF'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 30, category=dpg.mvThemeCat_Core)

with dpg.theme(tag='toogle_ON'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (15, 83, 135), category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 83, 135), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 30, category=dpg.mvThemeCat_Core)

with dpg.theme(tag='config_edit_buttons_theme'):
	with dpg.theme_component(dpg.mvAll):
		dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 20, category=dpg.mvThemeCat_Core)
		dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (15, 83, 135), category=dpg.mvThemeCat_Core)
		dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (15, 83, 135), category=dpg.mvThemeCat_Core)

with dpg.theme(tag='disabled_input_text'):
	with dpg.theme_component(dpg.mvInputText, enabled_state=False):
		dpg.add_theme_color(dpg.mvThemeCol_Text, (120,120,120), category=dpg.mvThemeCat_Core)
# --- THEMES --- #

# add menubar
with dpg.viewport_menu_bar() as main_menu:
	dpg.add_menu_item(label="Add project", callback=show_project_window)
	dpg.add_menu_item(label="Set packages repo", callback=lambda: dpg.show_item('package_repo_fb'))
	with dpg.tooltip(parent=dpg.last_item(), delay=0.1):
		pkgrepo = prefs['package_repo'] if 'package_repo' in prefs.keys() else '[None]'
		dpg.add_text(f'Currently set to: \n{pkgrepo}', tag='package_repo_tooltip')
		dpg.bind_item_font(dpg.last_item(), font_small)

# WINDOW: main
with dpg.window(tag='mainwin'):
	with dpg.group():
		dpg.add_spacer(height=30)
		
		# Running configs
		dpg.add_group(tag='all_running_configs')
		
		dpg.add_spacer(height=20)

		# Archived configs
		with dpg.collapsing_header(label='Archived'):
			dpg.add_group(tag='all_archived_configs')
			

# WINDOW: add project
with dpg.window(width=600, height=600, pos=(50,50), show=False, tag='add_project_win', no_title_bar=True):
	
	# Project info
	with dpg.group(horizontal=True):
		dpg.add_text('Name:')
		dpg.add_input_text(tag='project_name', default_value='new project')

	dpg.add_spacer(height=10)

	# Houdini version
	with dpg.collapsing_header(label='Houdini version', default_open=True):
		houdini_installs = utils.get_houdini_installed_versions()
		multi_selection = False
		for i, item in enumerate(houdini_installs):
			if (i%4==0):
				grp = dpg.add_group(horizontal=True, tag='grp_houdini_version')
			btn_item = dpg.add_button(tag=f'houdini_version--{i}', label=f'{item}', user_data=['houdini_version', item, multi_selection], callback=project_set_item, parent=grp)
			dpg.bind_item_theme(btn_item, 'toogle_OFF')

	dpg.add_spacer(height=10)

	# Houdini product
	with dpg.collapsing_header(label='Houdini product', default_open=True):
		houdini_products = ['FX', 'Core', 'Indie']
		multi_selection = False
		with dpg.group(horizontal=True, tag='grp_houdini_product'):
			for i, item in enumerate(houdini_products):
				btn_item = dpg.add_button(tag=f'houdini_product--{i}', label=f'{item}', user_data=['houdini_product', item, multi_selection], callback=project_set_item)
				dpg.bind_item_theme(btn_item, 'toogle_OFF')

	dpg.add_spacer(height=10)

	# Selected packages
	with dpg.collapsing_header(label='Load Packages', default_open=True):
		available_packages = utils.get_available_packages(prefs)
		multi_selection = True
		for i, item in enumerate(available_packages):
			if (i%3==0):
				grp = dpg.add_group(horizontal=True)
			btn_package = dpg.add_button(tag=f'packages--{i}', label=f'{item}', user_data=['packages', item, multi_selection], callback=project_set_item, parent=grp)
			dpg.bind_item_theme(btn_package, 'toogle_OFF')

	dpg.add_spacer(height=30)

	# Action buttons
	with dpg.group(horizontal=True):
		btn_save = dpg.add_button(label=f'Save', width=120, callback=save_config)
		btn_cancel = dpg.add_button(label=f'Cancel', width=120, callback=lambda:dpg.hide_item('add_project_win'))
		dpg.bind_item_theme(btn_save, 'big_buttons_action_theme')
		dpg.bind_item_font(btn_save, font_large)
		dpg.bind_item_theme(btn_cancel, 'big_buttons_action_theme')
		dpg.bind_item_font(btn_cancel, font_large)

# WINDOW: confirmation dialog
with dpg.window(tag='cd', show=False, label='Action confirmation', autosize=True):
	with dpg.group(horizontal=True):
		dpg.add_image(texture_tag='img_warning')
		dpg.add_text('', tag='cd_message')
	with dpg.group(horizontal=True):
		dpg.add_button(label='Ok', width=75, tag='cd_btn_ok')
		dpg.add_button(label='Cancel', width=75, callback=lambda:dpg.hide_item('cd'))
dpg.bind_item_font('cd', font_small)

# WINDOW: error dialog
with dpg.window(tag='ed', show=False, label='Error', autosize=True):
	with dpg.group(horizontal=True):
		dpg.add_image(texture_tag='img_error')
		dpg.add_text('', tag='ed_message')
	with dpg.group(horizontal=True):
		dpg.add_button(label='Ok', width=75, callback=lambda:dpg.hide_item('ed'))
dpg.bind_item_font('ed', font_small)

# STATUS TEXT BOX
dpg.add_text('', color=(37,37,38, 255), tag='info_box', parent='mainwin')

# FILE BROWSER: set packages repo
fb = dpg.add_file_dialog(
	label='Choose packages repository...',
	directory_selector=True, 
	default_path=os.path.expanduser('~'), 
	modal=True,
	show=False, 
	callback=set_packages_repo, 
	tag="package_repo_fb",
	width=450,
	height=380,
)
dpg.bind_item_font(fb, font_small)

# init DPG
ui = utils.load_ui()
viewport_w = 800 if not ui else ui['size'][0]
viewport_h = 800 if not ui else ui['size'][1]
viewport_x = 100 if not ui else ui['pos'][0]
viewport_y = 100 if not ui else ui['pos'][1]


dpg.create_viewport(
	title='Packman - Houdini Loader', 
	width=viewport_w, 
	height=viewport_h, 
	x_pos=viewport_x, 
	y_pos=viewport_y, 
	disable_close=True)

dpg.set_primary_window('mainwin', True)
dpg.set_exit_callback(callback=utils.save_ui)
dpg.set_viewport_resize_callback(utils.update_status_pos)

# rebuild config buttons (placed here to avoid popup bug showing at (0,0))
rebuild_config_list()

# init DPG (continue)
dpg.setup_dearpygui()
dpg.show_viewport()
#dpg.start_dearpygui()
utils.update_status_pos()

# use render loop to fade info_box color (alpha)
while dpg.is_dearpygui_running():
    fade_speed = 0.75
    info_box_color = dpg.get_item_configuration('info_box')['color']
    info_box_alpha = info_box_color[3]*255
    info_box_alpha -= fade_speed
    if info_box_alpha<=0: info_box_alpha=0
    info_box_color = [info_box_color[0]*255, info_box_color[1]*255, info_box_color[2]*255, info_box_alpha]
    dpg.configure_item('info_box', color=info_box_color)
    
    dpg.render_dearpygui_frame()

dpg.destroy_context()