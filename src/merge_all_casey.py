#!/usr/bin/env python3

import os
from pathlib import Path
import urllib.request
from urllib.error import HTTPError
from glslib import Application, GJSON
from munch import DefaultMunch
import re
from unidecode import unidecode

from dotenv import load_dotenv

class MergeAllCasey(Application):
    def __init__(self):
        super().__init__("Merge Casey with the song.")
        dotenv_path = os.path.expandvars(os.path.expanduser(self.config.secrets))
        load_dotenv(dotenv_path)

    def _arg_parse(self, parser):
        super()._arg_parse(parser)
        parser.add_argument("--hits_file", required=True, help="JSON file containing chart rows")
        parser.add_argument("--casey_dir", required=True, help="Input dir for all casey speech files")
        parser.add_argument("--output_dir", required=True, help="Output dir for merged mp3s")
        return parser

    def go(self):
        hits = DefaultMunch.fromDict(GJSON.loads(Path(self.args.hits_file).read_text(encoding="utf-8")))
        for index, hit in enumerate(hits, start=1):
            casey_path = Path(self.args.output_dir, f"CASEY_{index:03}.wav")
            mp3_path = casey_path.with_suffix(".mp3")
            # if casey_path exists, skip
            if mp3_path.exists():
                self.logger.print("Skipping", mp3_path)
                continue

if __name__ == "__main__":
    main = MergeAllCasey()
    raise SystemExit(main.go() or 0)
