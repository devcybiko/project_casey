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

class AIGenerateAllCasey(Application):
    def __init__(self):
        super().__init__("Generate Casey's voice for Billboard hits.")
        dotenv_path = os.path.expandvars(os.path.expanduser(self.config.secrets))
        load_dotenv(dotenv_path)

    def _arg_parse(self, parser):
        super()._arg_parse(parser)
        parser.add_argument("--input_dir", required=True, help="JSON file containing chart rows")
        parser.add_argument("--output_dir", required=True, help="Output dir for generated speeches")
        return parser

    def _clean_trivia(self, trivia):
        trivia = re.sub(r"\[[^\]\r\n]*\]", "", trivia)
        trivia = (
            trivia
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2026", "...")
        )
        trivia = unidecode(trivia)
        return trivia.strip()

    def _render_payload(self, hit):
        payload_path = Path(self.config.trivia.tts_payload).read_text(encoding="utf-8")
        payload = DefaultMunch.fromDict(GJSON.loads(payload_path))
        return payload

    def _tts(self, text, outfile):
        self.tts_payload.gen_text = text
        self.tts_payload.output_path = outfile
        # call the TTS API using request module
        self.logger.print(GJSON.dumps(self.tts_payload))
        result = urllib.request.urlopen(
            "http://localhost:8101/api/tts", 
            data=GJSON.dumps(self.tts_payload).encode())
        self.logger.print("TTS called", GJSON.loads(result.read()))

    def go(self):
        self.tts_payload = self._render_payload(None)
        # for each HITS_*.json in self.args.input_dir 
        for hit_file in sorted(Path(self.args.input_dir).glob("HIT_*.json")):
            hit = DefaultMunch.fromDict(GJSON.loads(hit_file.read_text(encoding="utf-8")))
            # create a new path CASEY_XXX.json
            casey_path = Path(self.args.output_dir, f"CASEY_{hit.ranking:03}.wav")
            # if casey_path exists, skip
            if casey_path.exists():
                self.logger.print("Skipping", casey_path)
                continue
            trivia = self._clean_trivia(hit.trivia)
            self._tts(trivia, casey_path)

if __name__ == "__main__":
    main = AIGenerateAllCasey()
    raise SystemExit(main.go() or 0)
