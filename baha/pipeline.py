import xml.etree.ElementTree as ET
import torch
import queue
import threading

from . import stages

config = stages.SubsConfig(
    exe = stages.ExecConfig(
        batch = 3,
        device = "cuda"
    ),
    key = stages.KeyConfig(
        empty=0.003, 
        diff_tol=0.4,
    ),
    box = stages.CropConfig(
        top=856,
        down=0,
        left=192,
        right=192,
        width=1920,
        height=1080
    ),
    filter=stages.FilterConfig(
        block_col = 512,
        max_text_row = 2,

        range_y_black = 24,
        range_y_white = 56,
        range_uv_grey = 16,
        row_min_keep = 4,
        col_min_keep = 4,
        row_max_break = 16,
        filter_white_row = 4,
        filter_black_row = 4,
    ),
    ocr = dict(
        # https://www.jaided.ai/easyocr/documentation/
        blocklist=" `~@#$%^&*_+={}[]|\\:;<>/",
        batch_size=16,
        contrast_ths=0,
        # https://github.com/clovaai/CRAFT-pytorch/issues/51
        #text_threshold=0.3,
        #low_text=0.2
    )
)

def async_iterable(xs, limit=2):
    def async_generator():
        q = queue.Queue(limit)

        def decode_worker():
            for x in xs:
                q.put(x)
            q.put(None)
            q.task_done()
        threading.Thread(target=decode_worker, daemon=True).start()
        while True:
            x = q.get()
            if x is None: break
            else: yield x

    if isinstance(xs, list): return xs
    else: return async_generator()

def convert_subtitle(in_video_path: str, out_sub_path: str):
    keys = async_iterable(stages.key_frame_generator(in_video_path, config))
    ocrs = async_iterable(stages.ocr_text_generator(keys, config))
    srts = stages.srt_generator(out_sub_path, ocrs)
    torch.cuda.empty_cache()

    