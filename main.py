import urllib.request
import xml.etree.ElementTree as ET
from tqdm import tqdm
from core import *
import http.server
import socket
import socketserver

RSS_URL = "https://api.ani.rip/ani-download.xml"
RSS_PATH = "temp/rss.xml"
IN_VIDEO_PATH = "temp/in.mp4"
OUT_SUBTITLE_PATH = "temp/out.srt"
OUT_VIDEO_PATH = "temp/out.mkv"
SERVE_HTTP = True

KeyExtractorConfig1080p1x = KeyConfig(
    200, 1000, 512, 16, 10, ContourConfig(32, 32, 2, 5, 1))
KeyExtractorConfig1080p2x = KeyConfig(
    50, 250, 512, 16, 10, ContourConfig(32, 32, 2, 3, 2))
KeyExtractorConfig = KeyExtractorConfig1080p1x
EasyOCRArgs = dict(
    blocklist="~@#$%^&*_-+={}[]|\\:;<>/",
    batch_size=4
)


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        self.update(b * bsize - self.n)


def download_anime_by_name(name: str):
    # 获取RSS
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)
    with DownloadProgressBar(unit='B', unit_scale=True,
                             miniters=1, desc="下载RSS") as t:
        urllib.request.urlretrieve(
            RSS_URL, filename=RSS_PATH, reporthook=t.update_to)

    for item in ET.parse(RSS_PATH).getroot().findall('./channel/item'):
        title = item.find("title").text
        link = item.find("link").text
        size_elem = [child for child in item if child.tag.endswith("size")]
        size = None
        if len(size_elem)==1:
            size = int(float(size_elem[0].text.split(" ")[0])*1024*1024)

        if name in title:
            print(f"发现视频 {title}")
            with DownloadProgressBar(unit='B', unit_scale=True, total=size,
                                     miniters=1, desc="下载视频") as t:
                urllib.request.urlretrieve(
                    link, filename=IN_VIDEO_PATH, reporthook=t.update_to)
            return

    raise Exception("未发现视频")


def convert_subtitle():
    keys = list(key_frame_generator(IN_VIDEO_PATH, KeyExtractorConfig))
    ocrs = list(ocr_text_generator(keys, EasyOCRArgs))
    srts = list(srt_entry_generator(ocrs))
    with open(OUT_SUBTITLE_PATH, "w") as f:
        print("\n\n".join(srts), file=f)

    os.system(" ".join([
        f"ffmpeg -y",
        f"-i {IN_VIDEO_PATH}",
        f"-sub_charenc 'UTF-8'",
        f"-f srt -i {OUT_SUBTITLE_PATH}",
        f"-map 0:0 -map 0:1 -map 1:0 -c:v copy -c:a copy",
        f"-c:s srt -metadata:s:s:0 language=zh-CN",
        f"{OUT_VIDEO_PATH}"
    ]))

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.path = OUT_VIDEO_PATH
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
def print_and_serve():
    print(f"转换完成,视频保存在 {os.path.abspath(OUT_VIDEO_PATH)}")

    if SERVE_HTTP:
        ip = socket.gethostbyname(socket.gethostname())
        handler = MyHttpRequestHandler
        with socketserver.TCPServer(("", 8000), handler) as httpd:
            print(f"转换完成,视频可通过 http://{ip}:8000 下载")
            httpd.serve_forever()

download_anime_by_name("星靈")
convert_subtitle()
print_and_serve()