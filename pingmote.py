'''
pingmote: a cross-platform Python global emote picker to quickly insert custom images/gifs

Author: David Chen
'''
import PySimpleGUI as sg
import json
import pyperclip
import keyboard
import os
import platform
import sys
from psgtray import SystemTray
# from config import *
from pathlib import Path
from time import sleep
from math import ceil


# from pathlib import Path

""" Hotkeys """
SHORTCUT = 'ctrl+alt+shift+q'
KILL_SHORTCUT = 'alt+shift+k'

""" Emote Picker """
NUM_COLS = 12  # max number of images per row in picker
NUM_FREQUENT = 12  # max number of images to show in the frequent section
SHOW_LABELS = True  # show section labels (frequents, static, gifs)
SEPARATE_GIFS = True  # separate static emojis and gifs into different sections
WINDOW_LOCATION = (1278,1278)  # initial position of GUI (before dragging)
GUI_BG_COLOR = '#36393F'  # background color (copied from discord colors)

""" Functionality """
AUTO_PASTE = True  # automatically paste the image after selection
AUTO_ENTER = True  # hit enter after pasting (useful in Discord)

""" Image Resizer """
RESIZE_GIFS = False  # requires `gifsicle`

""" Paths """
MAIN_PATH = Path(__file__).parent  # directory with pingmote.py
IMAGE_PATH = MAIN_PATH / 'assets' / 'resized'  # resized emotes
""" Experimental """
SHOW_FREQUENTS = True  # show frequents section (disabling removes hide button)
SLEEP_TIME = 0  # add delay if pasting/enter not working
PRESERVE_CLIPBOARD = False  # avoids copying link to clipboard (unreliable)
CUSTOM_HOTKEY_HANDLER = True  # workaround for alt+tab issues and broken scan codes


SYSTEM = platform.system()  # Windows, Linux, Darwin (Mac OS)


class PingMote():

    def __init__(self):
        # Load frequencies from json for frequents section
        self.clean_frequencies()
        self.frequencies = self.load_frequencies()
        self.frequents = self.get_frequents(self.frequencies)

        # Load links and file paths
        self.filename_to_link = self.load_links()

        # Setup
        self.window = None
        self.hidden = True
        self.window_location = WINDOW_LOCATION
        self.setup_hardware()
        if CUSTOM_HOTKEY_HANDLER:
            keyboard.hook(self.custom_hotkey)
        self.setup_gui()
        self.create_window_gui()

    def setup_gui(self):
        sg.theme('LightBrown1')  # Use this as base theme
        # Set location for where the window opens, (0, 0) is top left

        # sg.SetOptions(border_width=0)
        button_color = sg.theme_button_color()
        sg.theme_background_color(GUI_BG_COLOR)
        sg.theme_text_element_background_color(GUI_BG_COLOR)
        sg.theme_text_color('white')
        sg.theme_button_color((button_color[0], GUI_BG_COLOR))
        sg.theme_border_width(0)
        self.layout_gui()
        self.system_tray = SystemTray(menu=['_', ['Show', 'Hide', 'Edit Me', 'Settings', 'Exit']], icon=ICON, window=self.window, single_click_events=True)
        self.system_tray.show_message('Ready', 'Window created and hidden')

    def layout_gui(self):
        """ Layout GUI, then build a window and hide it """
        print('loading layout...')
        self.layout = []
        if SHOW_FREQUENTS:
            if SHOW_LABELS:
                self.layout.append([sg.Text('Frequently Used'),
                                    sg.Button('Hide', button_color=('black', 'orange'))])
            self.layout.append([sg.HorizontalSeparator()])
            self.layout += self.layout_frequents_section()
        self.layout += self.layout_main_section()
        if self.window:  # close old window before opening new (for rebuilds)
            self.window.close()
        no_titlebar = SYSTEM == 'Windows'
        self.window = sg.Window('Emote Picker', self.layout, location=self.window_location, icon=ICON,
                                keep_on_top=True, no_titlebar=no_titlebar, grab_anywhere=True, finalize=True, right_click_menu= ['_', ['Edit Me', 'Hide', 'Exit']])
        if SYSTEM == 'Darwin':  # Mac hacky fix for blank hidden windows
            # read the window once, allows for hiding
            self.window.read(timeout=10)
        self.hide_gui()

    def layout_frequents_section(self):
        """ Return a list of frequent emotes """
        return self.list_to_table([
            sg.Button('', key=img_name, image_filename=IMAGE_PATH / img_name, image_subsample=2, tooltip=img_name)
            for img_name in self.frequents])

    def layout_main_section(self):
        """ Return a list of main section emotes.
        If SEPARATE_GIFS is True, split into static and emoji sections
        """
        main_section = []
        statics, gifs = [], []
        for img in sorted(IMAGE_PATH.iterdir()):
            if SHOW_FREQUENTS and img.name in self.frequents:  # don't show same image in both sections
                continue
            button = sg.Button(key=img.name, image_filename=img, image_subsample=2, tooltip=img.name)
            if SEPARATE_GIFS:
                if img.suffix == '.png':
                    statics.append(button)
                else:  # gif
                    gifs.append(button)
            else:
                main_section.append(button)
        if SEPARATE_GIFS:
            combined = []
            if SHOW_LABELS:
                combined.append([sg.Text('Images')])
                combined.append([sg.HorizontalSeparator()])
            combined += self.list_to_table(statics)
            if SHOW_LABELS:
                combined.append([sg.Text('GIFs')])
            combined.append([sg.HorizontalSeparator()])
            combined += self.list_to_table(gifs)
            return combined

        return self.list_to_table(main_section)

    def create_window_gui(self):
        """ Run the event loop for the GUI, listening for clicks """
        # Event loop
        try:
            while True:
                event, values = self.window.read()
                self.system_tray.show_message(event, values)

                if event == self.system_tray.key:
                    event = values[event]
                # event = self.system_tray.read(timeout=10)
                # Process events common in Window and Tray
                if event in ('Exit', sg.WINDOW_CLOSED):
                    break
                elif event == 'Hide':
                    self.hide_gui()
                elif event == 'Edit Me':
                    sg.execute_editor(__file__)
                elif event == 'Show':
                    self.on_activate()
                if event in self.filename_to_link:
                    print(f'selection event = {event}')
                    self.on_select(event)
                elif event in (sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED, sg.EVENT_SYSTEM_TRAY_ICON_ACTIVATED):
                    # A tray double-click toggles visibility
                    self.on_activate() if self.hidden else self.hide_gui()
                else:
                    self.system_tray.show_message(f'NOT FOUND selection event = {event}')
        except Exception as e:
            sg.popup('Pingmote - error in event loop - CLOSING', e)

        self.system_tray.close()
        self.window.close()

    def on_select(self, event):
        """ Paste selected image link """
        self.hide_gui()
        if event not in self.filename_to_link:  # link missing
            print('Error: Link missing -', event)
            return

        if AUTO_PASTE:
            if PRESERVE_CLIPBOARD:  # write text with pynput
                self.paste_selection(event)
            else:  # copy to clipboard then paste
                self.copy_to_clipboard(event)
                self.paste_link()
            if AUTO_ENTER:
                self.keyboard_enter()
        else:
            self.copy_to_clipboard(event)

        self.window_location = self.window.current_location()  # remember window position
        self.update_frequencies(event)  # update count for chosen image

    def copy_to_clipboard(self, filename):
        """ Given an an image, copy the image link to clipboard """
        pyperclip.copy(self.filename_to_link[filename])

    def paste_selection(self, filename):
        """ Use keyboard to write the link instead of copy paste """
        keyboard.write(self.filename_to_link[filename])

    def paste_link(self):
        """ Press ctrl + v to paste """
        sleep(SLEEP_TIME)  # wait a bit if needed
        paste_cmd = 'command+v' if SYSTEM == 'Darwin' else 'ctrl+v'
        keyboard.send(paste_cmd)

    def keyboard_enter(self):
        """ Hit enter on keyboard to send pasted link """
        sleep(SLEEP_TIME)
        keyboard.send('enter')

    def update_frequencies(self, filename):
        """ Increment chosen image's counter in frequencies.json
            Rebuilds GUI if layout changes (frequents section changes)
        """
        if filename not in self.frequencies:
            self.frequencies[filename] = 0
        self.frequencies[filename] += 1
        self.write_frequencies(self.frequencies)
        prev_frequents = self.frequents
        self.frequents = self.get_frequents(
            self.frequencies)  # update frequents list
        if self.frequents != prev_frequents:  # frequents list has changed, update layout
            self.layout_gui()

    def clean_frequencies(self):
        """ Clean frequencies.json on file changes """
        frequencies = self.load_frequencies()
        filenames = {img_path.name for img_path in IMAGE_PATH.iterdir()}
        for file in list(frequencies):
            if file not in filenames:
                del frequencies[file]  # remove key, file not present
        self.write_frequencies(frequencies)

    def load_links(self):
        """ Load image links from links.txt """
        with open(MAIN_PATH / 'assets' / 'links.txt') as f:
            links = f.read().splitlines()
            link_dict = dict()
            for link in links:
                l = link.rsplit('/', 1)[-1]
                if l[-4] != '.':
                    print(f'EXCEPTION to link found: {l}')
                    l = l[:l.find('.')+4]
                    print(f'NEW link: {l}')
                link_dict[l] = link
            # link_dict = {link.rsplit('/', 1)[-1]: link for link in links}
            return link_dict

    def load_frequencies(self):
        """ Load the frequencies dictionary from frequencies.json """
        with open(MAIN_PATH / 'assets' / 'frequencies.json', 'r') as f:
            return json.load(f)

    def write_frequencies(self, frequencies):
        """ Write new frequencies to frequencies.json """
        with open(MAIN_PATH / 'assets' / 'frequencies.json', 'w') as f:
            json.dump(frequencies, f, indent=4)

    def get_frequents(self, frequencies):
        """ Get the images used most frequently """
        # sort in descending order by frequency
        desc_frequencies = sorted(
            frequencies.items(), key=lambda x: x[-1], reverse=True)
        return [img for img, _ in desc_frequencies[:NUM_FREQUENT]]

    def list_to_table(self, a, num_cols=NUM_COLS):
        """ Given a list a, convert it to rows and columns
            ex) a = [1, 2, 3, 4, 5], num_cols = 2
            returns: [[1, 2], [3, 4], [5]]
            """
        return [a[i * num_cols:i * num_cols + num_cols] for i in range(ceil(len(a) / num_cols))]

    def setup_hardware(self):
        """ Create mouse controller, setup hotkeys """
        if CUSTOM_HOTKEY_HANDLER:
            self.hotkeys = {
                SHORTCUT: self.on_activate,
                KILL_SHORTCUT: self.kill_all,
            }
        else:
            keyboard.add_hotkey(SHORTCUT, self.on_activate)
            keyboard.add_hotkey(KILL_SHORTCUT, self.kill_all)

    def custom_hotkey(self, event):
        """ Hook and react to hotkeys with custom handler """
        try:
            pressed_keys = [e.name.lower()
                            for e in keyboard._pressed_events.values()]
        except AttributeError:  # Fn might return as None
            pressed_keys = []
        for hotkey, func in self.hotkeys.items():
            pressed = all(
                key in pressed_keys
                for key in hotkey.split('+')
            )

            if pressed:
                func()

    def hide_gui(self):
        self.window.hide()
        self.hidden = True
        if SYSTEM == 'Darwin':  # Unfocus Python to allow for pasting
            keyboard.send('command+tab')

    def show_gui(self):
        self.window.un_hide()
        self.window.TKroot.focus_force()  # force window to be focused
        self.hidden = False

    def on_activate(self):
        """ When hotkey is activated, toggle the GUI """
        if self.hidden:
            self.show_gui()
        else:
            self.hide_gui()

    def kill_all(self):
        """ Kill the script in case it's frozen or buggy """
        print('exit program')
        self.window.close()
        sys.exit(1)  # exit the entire program


if __name__ == '__main__':
    ICON = b'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'
    pingmote = PingMote()


