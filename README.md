# pingmote
A cross-platform Python global emote picker to quickly insert custom images/gifs 

Motivation: *Poor Man's Discord Nitro*


# Demo
![pingmote demo](https://user-images.githubusercontent.com/37674516/107857226-1e72f000-6dfb-11eb-8a9a-e938368b65bc.gif)

# How It Works
All images/gifs (properly sized) are stored in `assets/resized`. These images are shown in the GUI, and clicking on them copies the corresponding URL to clipboard (with options to auto-paste). The URLs are stored in `links.txt`.

# Getting Started
- Clone this repo: `git clone https://github.com/dchen327/pingmote.git` or download the code as a zip and extract
- Change into the pingmote directory (make sure you can see `pingmote.py`)
- Run `pip install -r requirements.txt` to install all necessary dependencies (use `pip3` if needed)

# Usage
- Running `python pingmote.py` (or `python3 pingmote.py`) will start the script, and when you hit the shortcut specified at the top of `pingmote.py` (default `ctrl+q`), the emote picker will show up, allowing you to click and pick an emote to insert
- Note: you need to wait 2-3s for the GUI to load.
- Hit the shortcut again to hide the GUI, and drag the GUI to where you want it to show up in the future

# Adding Your Own Emotes
- Sorry for this being a bit complicated, I'm working on simplifying the workflow
- Drop image files in the `original` folder, then run `image_resizer.py` which will resize all the images (ignoring gifs) and drop them in the `resized` folder
- Unfortunately, `image_resizer.py` is currently unable to resize gifs, so a website like [this](https://www.iloveimg.com/resize-image/resize-gif) is useful. After downloading the resized gifs (64x64), extract them to the `original` folder in assets, then run `image_resizer.py` to create the resized folder while ignoring gifs
- Windows Paint 3D also works for gif resizing
- Upload files to an image hoster (I like [postimages](https://postimages.org/)). Copy the direct image links (ending in file extension) and paste in `links.txt`
- Imgur doesn't work currently, since Imgur links don't contain the original filename
- Some emote sources (right click save image): [discordmojis.com](https://discordmojis.com/), [emoji.gg](https://emoji.gg/)

# Configs
- Check the top of `pingmote.py` for configs

# Notes
- Since this program pastes image/gif URLs as emotes, we can't use inline emotes or reacts.
- Images have slight padding in discord, so they don't look *exactly* the same as regular emotes
- Pretty much only Discord works (Facebook Messenger and Slack don't autoembed)

# TODOs
- Mac hotkey + GUI testing
- Better ordering of emotes (categorization, etc.)
- Simplify the process for adding new emotes
- Gif resizing? (idk PIL isn't very good for this)
- Ensure gif thumbnail isn't blank (not fully sure how to do this)
- Search emotes by keyword (would require files to be named, since most of my files now are just a bunch of numbers)
- Emote deletion

# Reasons you should still buy Discord Nitro
- Support Discord!
- Inline emotes/gifs, keyboard shortcuts by name (ex: :emote_name:)
- React with emotes
- Other nitro benefits!

# Acknowledgements
- Thanks to [Luke Tong](https://github.com/luke-rt) for cross-platform GUI and clipboard testing
- Thanks to [Stephane Morel](https://github.com/SoAsEr) for Windows testing
- Thanks to [Brazil-0034](https://github.com/Brazil-0034) for adding support for non-destructive pasting

# Progress Timeline
- Initial method (50 lines): `xclip` for copying local images, `xdotool` for pasting and keyboard commands
- Switched to PyAutoGUI for keyboard simulation, `xdotool` no longer needed
- Wrote `image_resizer.py` for locally resizing images
- Uploaded images to postimages; simplified copy pasting of links only and not image data (removed all subprocess calls)
- Added frequents section for favorite emotes
- Added feature to open the GUI near the mouse cursor
- Cleaned up links for better file to link mapping
- Switched to `pynput` for cross-platform global hotkey mapping, fully removed PyAutoGUI dependencies
- Added section labels and ability to separate images and gifs
- Switched to `keyboard` from `pynput` to fix hotkey blocking behavior (after 3 weeks of zero progress)

# License
[MIT License](https://github.com/dchen327/pingmote/blob/master/LICENSE.md)