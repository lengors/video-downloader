import youtube_dl as ydl
import PySimpleGUI as psg
from tkinter import filedialog
import youtube_dl.utils as yutils
from urllib.parse import urlparse
import os, sys, time, tempfile, json

default_language = {
    "name": "English (United States)",
    "title": "Your favorite downloader ❤️",
    "error": "Error",
    "information": "Information",
    "link_error": "link not specified",
    "video_link": "Video's link",
    "file_location": "File's location",
    "file_name": "File's name",
    "download_success": "download ended successfully",
    "download_failed": "download failed"
}

class Logger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        psg.popup('Erro: ' + msg)

def get_string(value, language_name = None):
    global languages, personal_data, default_language
    
    if language_name is None:
        language_name = personal_data.get('language')
    
    dictionary = languages.get(language_name)
    if dictionary is None:
        dictionary = default_language
    return dictionary.get(value, default_language.get(value))

def fix_personal_data(personal_data):
    if personal_data is None:
        personal_data = { }
    
    # fix folder
    folder = personal_data.setdefault('folder', os.path.join(os.path.expanduser('~'), 'Downloads'))
    if not os.path.isdir(folder):
        personal_data['folder'] = os.path.join(os.path.expanduser('~'), 'Downloads')

    # fix language
    personal_data.setdefault('language', 'en-US.lang')
    return personal_data

def format_bytes(size : int):
    initialsize = size
    power = 2 ** 10
    n = 0
    while size > power:
        size /= power
        n += 1
    if n > 4:
        return size, 0
    return size, n

def hook(data : dict):
    status = data.get('status')
    filename = data.get('filename')
    filename = os.path.basename(filename)
    filename, *_ = os.path.splitext(filename)
    downloaded_bytes = data.get('downloaded_bytes')
    total_bytes = data.get('total_bytes', data.get('total_bytes_estimate'))

    global progress_bar, link_input, browse_input, filename_input, download_button, window
    
    eta = data.get('eta')
    speed = data.get('speed')

    # title = 'O teu downloader favorito ❤️'
    title_content = list()

    if eta is not None:
        eta = time.gmtime(eta)
        eta = time.strftime('%H:%M:%S', eta)
        title_content.append(eta)
    if speed is not None:
        formatter = { 0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T' }
        speed, n = format_bytes(speed)
        title_content.append(f'{"{:.3}".format(speed)}{formatter[n]}B/s')

    if len(title_content) > 0:
        download_button.Update(f'{", ".join(title_content)}')
    else:
        download_button.Update('Download')
    progress_bar.UpdateBar(downloaded_bytes, max = total_bytes)

    link_input.Update(disabled = status == 'downloading')
    browse_input.Update(disabled = status == 'downloading')
    filename_input.Update(value = filename, disabled = status == 'downloading')
    download_button.Update(disabled = status == 'downloading')

    if status == 'finished' or status == 'error':
        if status == 'finished':
            psg.popup(f"{get_string('information')}: {get_string('download_success')}")
            link_input.Update('')
            filename_input.Update('')
        else:
            psg.popup(f"{get_string('error')}: {get_string('download_failed')}")
        progress_bar.UpdateBar(0)

cachepath = os.path.abspath(os.path.join(tempfile.gettempdir(), 'tmp-video-downloader-fd10a5c8-8a68-4d62-a0bd-20f8ee93a716.cache'))
languagepath = 'languages.json'

languages = {}
if os.path.isfile(languagepath):
    with open(languagepath, 'r', encoding = 'utf-8') as fin:
        try:
            languages = json.loads(fin.read())
        except json.JSONDecodeError:
            pass

personal_data = None
if os.path.isfile(cachepath):
    with open(cachepath, 'rb') as fin:
        try:
            personal_data = json.loads(fin.read().decode())
        except json.JSONDecodeError:
            pass

personal_data = fix_personal_data(personal_data)
with open(cachepath, 'wb') as fout:
    fout.write(json.dumps(personal_data).encode())

video_link_txt = psg.Text(get_string('video_link'))
file_location_txt = psg.Text(get_string('file_location'))
file_name_txt = psg.Text(get_string('file_name'))

first_column = [
    [ video_link_txt ],
    [ file_location_txt ],
    [ file_name_txt ]
]

link_input = psg.InputText(size = (64, 1), key = 'link')
browse_input = psg.FolderBrowse(get_string('browse'), initial_folder = personal_data['folder'], change_submits = True)
filename_input = psg.InputText(size = (64, 1), key = 'filename')
second_column = [
    [ link_input ],
    [ psg.InputText(personal_data['folder'], readonly = True, key = 'folder', size = (55, 1)), browse_input ],
    [ filename_input ]
]

langs = [ get_string('name', key) for key in languages.keys() ]
if len(langs) == 0:
    langs.append(get_string('name'))
combo_selector = psg.Combo(langs, default_value = get_string('name'), key = 'Language', enable_events = True, readonly = True, auto_size_text = True)
download_button = psg.Submit('Download', size = (16, 1))
progress_bar = psg.ProgressBar(100, orientation = 'h', size=(43, 20), key = 'progressbar')

a = psg.Column(first_column, size = (146, 78))
layout = [
    [ psg.Column([[ combo_selector ]], justification = 'right') ],
    [ a, psg.Column(second_column) ],
    [ progress_bar, download_button ]
]

logger = Logger()
window = psg.Window(get_string('title'), layout)
while True:
    event, values = window.Read()
    if event in (None, 'Exit'):
        sys.exit()
    elif event == 'Download':
        link = values['link'].strip()
        folder = values['folder'].strip()
        filename = values['filename'].strip()

        if len(link) == 0:
            psg.popup(f"{get_string('error')}: {get_string('link_error')}")
            continue

        if len(filename) == 0:
            filename = "%(title)s.%(ext)s"
        else:
            filename = filename + ".%(ext)s"

        personal_data['folder'] = os.path.abspath(folder)
        with open(cachepath, 'wb') as fout:
            fout.write(json.dumps(personal_data).encode())

        ydl_opts = {
            'outtmpl': os.path.join(folder, filename),
            'format': 'best[protocol^=http][protocol!=http_dash_segments]/best',
            'fixup': 'detect_or_warn',
            'retries': 5,
            'logger': logger,
            'progress_hooks': [ hook ]
        }
        with ydl.YoutubeDL(ydl_opts) as dl:
            try:
                dl.download([ link ])
            except yutils.DownloadError:
                pass
    elif event == 'Language':
        print(browse_input.get_size())

        language_key = None
        for key in languages.keys():
            if get_string('name', key) == values[event]:
                language_key = key
                break

        if language_key is not None:
            personal_data['language'] = language_key
            with open(cachepath, 'wb') as fout:
                fout.write(json.dumps(personal_data).encode())
            video_link_txt.Update(get_string('video_link'))
            file_location_txt.Update(get_string('file_location'))
            file_name_txt.Update(get_string('file_name'))
            window.set_title(get_string('title'))
            browse_input.Update(get_string('browse'))
