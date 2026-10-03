#!/usr/bin/env python3

import os
from pathlib import Path
import re
import urllib.request
from datetime import date
from unidecode import unidecode

from glslib import Application, GJSON
from jinja2 import StrictUndefined, Template
from munch import DefaultMunch

from dotenv import load_dotenv

class AIGenerateAllTrivia(Application):
    def __init__(self):
        super().__init__("Generate trivia for Billboard number-one songs.")
        dotenv_path = os.path.expandvars(os.path.expanduser(self.config.secrets))
        load_dotenv(dotenv_path)

    def _arg_parse(self, parser):
        super()._arg_parse(parser)
        parser.add_argument("--hits_file", required=True, help="JSON file containing chart rows")
        parser.add_argument("--output_dir", required=True, help="Output dir for generated trivia")
        return parser

    def _clean_prompt(self, trivia):
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
        prompt_template = Path(self.config.trivia.prompt_template).read_text(encoding="utf-8")
        today = date.today()
        prompt = Template(prompt_template, undefined=StrictUndefined).render(
            ARTIST=hit.artist,
            SONG=hit.song,
            RANKING=hit.ranking or 1,
            CHART_DATE=f"{hit.year}-{today.month}-{today.day}",
        )
        payload_template = Path(self.config.trivia.payload_template).read_text(encoding="utf-8")
        payload_text = Template(payload_template, undefined=StrictUndefined).render(
            MODEL=self.config.trivia.model,
            PROMPT="",
        )
        payload = DefaultMunch.fromDict(GJSON.loads(payload_text))
        payload.messages[0].content = self._clean_prompt(prompt)
        return payload

    def _generate_trivia(self, hit):
        api_key = os.environ.get("OPEN_WEBUI_API_KEY")
        if not api_key:
            raise RuntimeError("OPEN_WEBUI_API_KEY is not set")
        
        payload = self._render_payload(hit)
        request = urllib.request.Request(
            self.config.trivia.url,
            data=GJSON.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=300) as response:
            result = DefaultMunch.fromDict(GJSON.loads(response.read().decode("utf-8")))

        return result.choices[0].message.content

    def go(self):
        hits = DefaultMunch.fromDict(GJSON.loads(Path(self.args.hits_file).read_text(encoding="utf-8")))
        results = []

        for index, hit in enumerate(hits, start=1):
            if not hit.ranking:
                hit.ranking = index
            hit_path = Path(self.args.output_dir, f"HIT_{index:03}.json")
            # if hit_path exists, move on to the next
            if hit_path.exists():
                self.logger.print("Skipping", hit.song)
                continue
            self.logger.print("Generating trivia for", hit.song, hit.artist, index, "/", len(hits))
            hit.trivia = self._generate_trivia(hit)
            results.append(hit)
            # write the hit to a single record HIT_001.json, HIT_002.json, etc.
            hit_path.write_text(GJSON.dumps(hit, indent=2))
            GJSON.print(hit.trivia)

if __name__ == "__main__":
    main = AIGenerateAllTrivia()
    raise SystemExit(main.go() or 0)
