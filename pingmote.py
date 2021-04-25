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
WINDOW_LOCATION = (100, 100)  # initial position of GUI (before dragging)
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
        self.system_tray = sg.SystemTray(menu=['_', ['Show', 'Hide', 'Edit Me', 'Settings', 'Exit']], data_base64=sg.EMOJI_BASE64_PONDER)
        self.system_tray.show_message('Ready', 'Window created and hidden', messageicon=sg.EMOJI_BASE64_HAPPY_JOY)

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
        self.window = sg.Window('Emote Picker', self.layout, location=self.window_location,
                                keep_on_top=True, no_titlebar=no_titlebar, grab_anywhere=True, finalize=True, right_click_menu= ['_', ['Edit Me', 'Hide', 'Exit']])
        if SYSTEM == 'Darwin':  # Mac hacky fix for blank hidden windows
            # read the window once, allows for hiding
            self.window.read(timeout=10)
        self.hide_gui()

    def layout_frequents_section(self):
        """ Return a list of frequent emotes """
        return self.list_to_table([
            sg.Button('', key=img_name, image_filename=IMAGE_PATH /
                      img_name, image_subsample=2, tooltip=img_name)
            for img_name in self.frequents
        ])

    def layout_main_section(self):
        """ Return a list of main section emotes.
        If SEPARATE_GIFS is True, split into static and emoji sections
        """
        main_section = []
        statics, gifs = [], []
        for img in sorted(IMAGE_PATH.iterdir()):
            if SHOW_FREQUENTS and img.name in self.frequents:  # don't show same image in both sections
                continue
            button = sg.Button(
                '', key=img.name, image_filename=img, image_subsample=2, tooltip=img.name)
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
                event, _ = self.window.read(timeout=100)
                tevent = self.system_tray.read(timeout=10)
                # Process events common in Window and Tray
                if 'Exit' in (event, tevent) or event == sg.WINDOW_CLOSED:
                    break
                elif 'Hide' in (event, tevent):
                    self.hide_gui()
                elif 'Edit Me' in (event, tevent):
                    sg.execute_editor(__file__)

                # Process events found only in Window or Tray
                if tevent == 'Show':
                    self.on_activate()
                if event in self.filename_to_link:
                    print(f'selection event = {event}')
                    self.on_select(event)
                # A tray double-click toggles visibility
                if tevent in (sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED, sg.EVENT_SYSTEM_TRAY_ICON_ACTIVATED):
                    self.on_activate() if self.hidden else self.hide_gui()
        except Exception as e:
            sg.popup('Pingmote - error in event loop', e)

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
            return {link.rsplit('/', 1)[-1]: link for link in links}

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
        os._exit(1)  # exit the entire program


if __name__ == '__main__':
    pingmote = PingMote()
