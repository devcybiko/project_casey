#!/usr/bin/env python3

import csv
from datetime import date, datetime
from pathlib import Path

from glslib import Application
from sqlalchemy import Date, Integer, Text, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Billboard(Base):
    __tablename__ = "billboard"
    __table_args__ = {"schema": "music"}

    id: Mapped[int] = mapped_column(primary_key=True)
    chart_date: Mapped[date] = mapped_column(Date, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    song: Mapped[str] = mapped_column(Text, nullable=False)
    artist: Mapped[str] = mapped_column(Text, nullable=False)


class BillboardIngest(Application):
    def __init__(self):
        super().__init__("Ingest Billboard Hot 100 CSV files into PostgreSQL.")
        self.csv_dir = Path(self.args.csv_dir).resolve()
        self.engine = self._create_engine()

    def _arg_parse(self, parser):
        super()._arg_parse(parser)
        parser.add_argument("--csv_dir", default="/data/shared/git/billboard-hot-100-web-scraper/hot100", help="Directory containing Billboard CSV files")
        parser.add_argument("--host", default="127.0.0.1", help="PostgreSQL host")
        parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
        parser.add_argument("--database", default="ai_workstation", help="PostgreSQL database")
        parser.add_argument("--user", default="ai_app", help="PostgreSQL user")
        parser.add_argument("--progress_every", type=int, default=5000, help="Display progress after this many rows")
        return parser

    def _get_args(self):
        return self.args

    def _create_engine(self):
        url = f"postgresql+psycopg://{self.args.user}@{self.args.host}:{self.args.port}/{self.args.database}"
        return create_engine(url, echo=False, pool_pre_ping=True)

    def _find_csv_files(self):
        return sorted(self.csv_dir.glob("*.csv"))

    def _read_rows(self, path):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)

            for row_number, row in enumerate(reader, start=1):
                if len(row) != 4:
                    raise ValueError(f"{path}:{row_number}: expected 4 columns, got {len(row)}: {row}")

                yield {
                    "chart_date": datetime.strptime(row[0], "%Y-%m-%d").date(),
                    "song": row[1].strip(),
                    "artist": row[2].strip(),
                    "ranking": int(row[3]),
                }

    def _insert_billboard(self, session, rows):
        session.execute(
            insert(Billboard),
            rows,
        )

    def _show_progress(self, files, rows, failed):
        print(f"files={files:,} rows={rows:,} failed={failed:,}", flush=True)

    def _validate_batch(self, path, offset, batch):
        keys = {}

        for index, row in enumerate(batch):
            key = (row["chart_date"], row["ranking"])

            if key in keys:
                previous = keys[key]

                raise RuntimeError(
                    f"{path.name}: duplicate key {key} "
                    f"at file rows {offset + previous + 1} and {offset + index + 1}"
                )

            keys[key] = index
            
    def _ingest(self):
        files = 0
        rows = 0
        failed = 0
        interrupted = False
        batch_size = 500

        with Session(self.engine) as session:
            try:
                for path in self._find_csv_files():
                    files += 1
                    if self.args.debug:
                        print(f"LOAD {path}", flush=True)

                    try:
                        file_rows = list(self._read_rows(path))
                        print(
                            f"{path.name}: "
                            f"rows={len(file_rows):,} "
                            f"first={file_rows[0]['chart_date']}/{file_rows[0]['ranking']} "
                            f"last={file_rows[-1]['chart_date']}/{file_rows[-1]['ranking']}",
                            flush=True,
                        )

                        for offset in range(0, len(file_rows), batch_size):
                            batch = file_rows[offset:offset + batch_size]
                            self._insert_billboard(session, batch)

                        session.commit()
                        rows += len(file_rows)

                        self._show_progress(files, rows, failed)

                    except Exception as exc:
                        session.rollback()
                        failed += 1
                        print(f"ERROR {path}: {type(exc).__name__}: {exc}", flush=True)

            except KeyboardInterrupt:
                interrupted = True
                print("\nInterrupted. Saving completed work...", flush=True)

        return files, rows, failed, interrupted
        
    def go(self):
        if not self.csv_dir.is_dir():
            self.logger.error(f"CSV directory does not exist: {self.csv_dir}")
            return 1

        paths = self._find_csv_files()

        if not paths:
            self.logger.error(f"No CSV files found in: {self.csv_dir}")
            return 1

        print(f"Billboard CSV root: {self.csv_dir}", flush=True)
        print(f"PostgreSQL: {self.args.user}@{self.args.host}:{self.args.port}/{self.args.database}", flush=True)

        files, rows, failed, interrupted = self._ingest()

        self._show_progress(files, rows, failed)

        if interrupted:
            print("Ingest interrupted. Run the same command to resume.", flush=True)
            return 130

        return 1 if failed else 0


if __name__ == "__main__":
    main = BillboardIngest()
    raise SystemExit(main.go())
