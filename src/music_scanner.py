#!/usr/bin/env python3

from datetime import datetime, timezone
from pathlib import Path

from glslib import Application
from mutagen import File as MutagenFile
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, create_engine, func, select

class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = {"schema": "music"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    filename: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    artist: Mapped[str | None] = mapped_column(Text)
    album: Mapped[str | None] = mapped_column(Text)
    song: Mapped[str | None] = mapped_column(Text)
    release_year: Mapped[int | None] = mapped_column(Integer)
    track_number: Mapped[int | None] = mapped_column(Integer)
    disc_number: Mapped[int | None] = mapped_column(Integer)
    genre: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str | None] = mapped_column(String(32))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    artist_source: Mapped[str | None] = mapped_column(String(32))
    album_source: Mapped[str | None] = mapped_column(String(32))
    song_source: Mapped[str | None] = mapped_column(String(32))
    year_source: Mapped[str | None] = mapped_column(String(32))
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_at: Mapped[float | None] = mapped_column(Float)


class MusicScanner(Application):
    AUDIO_EXTENSIONS = {
        ".aac",
        ".aiff",
        ".ape",
        ".flac",
        ".m4a",
        ".mp3",
        ".mp4",
        ".ogg",
        ".opus",
        ".wav",
        ".wma",
    }

    def __init__(self):
        super().__init__("Scan a music library into PostgreSQL.")
        self.music_root = Path(self.args.music_root).resolve()
        self.engine = self._create_engine()

    def _arg_parse(self, parser):
        super()._arg_parse(parser)
        parser.add_argument("--music_root", default="/mnt/plex/Music", help="Root directory containing music files")
        parser.add_argument("--host", default="127.0.0.1", help="PostgreSQL host")
        parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
        parser.add_argument("--database", default="ai_workstation", help="PostgreSQL database")
        parser.add_argument("--user", default="ai_app", help="PostgreSQL user")
        parser.add_argument("--commit_every", type=int, default=25, help="Commit after this many new or changed files")
        parser.add_argument("--progress_every", type=int, default=25, help="Display progress after this many files")
        return parser

    def _show_catalog_summary(self):
        with Session(self.engine) as session:
            total = session.scalar(select(func.count()).select_from(Track))
            missing_artist = session.scalar(select(func.count()).select_from(Track).where(Track.artist.is_(None)))
            missing_album = session.scalar(select(func.count()).select_from(Track).where(Track.album.is_(None)))
            missing_song = session.scalar(select(func.count()).select_from(Track).where(Track.song.is_(None)))
            missing_year = session.scalar(select(func.count()).select_from(Track).where(Track.release_year.is_(None)))

        print("Catalog summary:", flush=True)
        print(f"  tracks:         {total:,}", flush=True)
        print(f"  missing artist: {missing_artist:,}", flush=True)
        print(f"  missing album:  {missing_album:,}", flush=True)
        print(f"  missing song:   {missing_song:,}", flush=True)
        print(f"  missing year:   {missing_year:,}", flush=True)

    def _create_engine(self):
        url = f"postgresql+psycopg://{self.args.user}@{self.args.host}:{self.args.port}/{self.args.database}"
        return create_engine(url, echo=False, pool_pre_ping=True)

    def _tag_value(self, tags, names):
        if not tags:
            return None

        for name in names:
            value = tags.get(name)

            if not value:
                continue

            if isinstance(value, (list, tuple)):
                value = value[0]

            value = str(value).strip()

            if value:
                return value

        return None

    def _parse_number(self, value):
        if not value:
            return None

        try:
            return int(str(value).split("/")[0])
        except (TypeError, ValueError):
            return None

    def _parse_year(self, value):
        if not value:
            return None

        text = str(value).strip()

        for token in text.replace("/", "-").split("-"):
            token = token.strip()

            if len(token) < 4:
                continue

            if not token[:4].isdigit():
                continue

            year = int(token[:4])

            if 1800 <= year <= 2100:
                return year

        return None

    def _read_metadata(self, path):
        metadata = {
            "artist": None,
            "album": None,
            "song": None,
            "release_year": None,
            "track_number": None,
            "disc_number": None,
            "genre": None,
            "duration_seconds": None,
            "artist_source": None,
            "album_source": None,
            "song_source": None,
            "year_source": None,
        }

        try:
            audio = MutagenFile(path, easy=True)

            if audio is None:
                return metadata

            tags = audio.tags

            metadata["artist"] = self._tag_value(tags, ["artist", "albumartist"])
            metadata["album"] = self._tag_value(tags, ["album"])
            metadata["song"] = self._tag_value(tags, ["title"])
            metadata["release_year"] = self._parse_year(self._tag_value(tags, ["originaldate", "date", "year"]))
            metadata["track_number"] = self._parse_number(self._tag_value(tags, ["tracknumber"]))
            metadata["disc_number"] = self._parse_number(self._tag_value(tags, ["discnumber"]))
            metadata["genre"] = self._tag_value(tags, ["genre"])

            if getattr(audio, "info", None):
                metadata["duration_seconds"] = getattr(audio.info, "length", None)

            if metadata["artist"]:
                metadata["artist_source"] = "tag"

            if metadata["album"]:
                metadata["album_source"] = "tag"

            if metadata["song"]:
                metadata["song_source"] = "tag"

            if metadata["release_year"]:
                metadata["year_source"] = "tag"

        except Exception as exc:
            self.logger.warning(f"Unable to read tags: {path}: {exc}")

        return metadata

    def _clean_filename_song(self, path):
        song = path.stem.strip()

        if " - " not in song:
            return song

        first, remainder = song.split(" - ", 1)

        if first.strip().isdigit():
            return remainder.strip()

        return song

    def _infer_from_path(self, path, metadata):
        parts = path.relative_to(self.music_root).parts

        if not metadata["song"]:
            metadata["song"] = self._clean_filename_song(path)
            metadata["song_source"] = "filename"

        if len(parts) < 3:
            return metadata

        if not metadata["artist"]:
            metadata["artist"] = parts[-3]
            metadata["artist_source"] = "directory"

        if not metadata["album"]:
            metadata["album"] = parts[-2]
            metadata["album_source"] = "directory"

        return metadata

    def _is_current(self, session, path, stat):
        statement = select(Track.file_size, Track.modified_at).where(Track.filename == str(path))
        row = session.execute(statement).one_or_none()

        if row is None:
            return False

        return row.file_size == stat.st_size and row.modified_at == stat.st_mtime

    def _build_row(self, path, stat):
        metadata = self._read_metadata(path)
        metadata = self._infer_from_path(path, metadata)

        return {
            "filename": str(path),
            "artist": metadata["artist"],
            "album": metadata["album"],
            "song": metadata["song"],
            "release_year": metadata["release_year"],
            "track_number": metadata["track_number"],
            "disc_number": metadata["disc_number"],
            "genre": metadata["genre"],
            "file_type": path.suffix.lower().lstrip("."),
            "file_size": stat.st_size,
            "duration_seconds": metadata["duration_seconds"],
            "artist_source": metadata["artist_source"],
            "album_source": metadata["album_source"],
            "song_source": metadata["song_source"],
            "year_source": metadata["year_source"],
            "scanned_at": datetime.now(timezone.utc),
            "modified_at": stat.st_mtime,
        }

    def _upsert_track(self, session, row):
        statement = insert(Track).values(**row)

        statement = statement.on_conflict_do_update(
            index_elements=[Track.filename],
            set_={
                "artist": statement.excluded.artist,
                "album": statement.excluded.album,
                "song": statement.excluded.song,
                "release_year": statement.excluded.release_year,
                "track_number": statement.excluded.track_number,
                "disc_number": statement.excluded.disc_number,
                "genre": statement.excluded.genre,
                "file_type": statement.excluded.file_type,
                "file_size": statement.excluded.file_size,
                "duration_seconds": statement.excluded.duration_seconds,
                "artist_source": statement.excluded.artist_source,
                "album_source": statement.excluded.album_source,
                "song_source": statement.excluded.song_source,
                "year_source": statement.excluded.year_source,
                "scanned_at": statement.excluded.scanned_at,
                "modified_at": statement.excluded.modified_at,
            },
        )

        session.execute(statement)

    def _find_audio_files(self):
        import os

        for root, dirs, files in os.walk(self.music_root):
            dirs.sort(key=str.lower)
            files.sort(key=str.lower)

            root_path = Path(root)

            for filename in files:
                path = root_path / filename

                if path.suffix.lower() not in self.AUDIO_EXTENSIONS:
                    continue

                yield path

    def _show_progress(self, total, scanned, skipped, failed):
        print(f"files={total:,} scanned={scanned:,} skipped={skipped:,} failed={failed:,}", flush=True)

    def _scan(self):
        total = 0
        scanned = 0
        skipped = 0
        failed = 0
        pending = 0
        interrupted = False

        with Session(self.engine) as session:
            try:
                for path in self._find_audio_files():
                    total += 1

                    try:
                        stat = path.stat()

                        if self._is_current(session, path, stat):
                            skipped += 1

                            if self.args.debug:
                                print(f"SKIP {path}", flush=True)

                            if total % self.args.progress_every == 0:
                                self._show_progress(total, scanned, skipped, failed)

                            continue

                        if self.args.debug:
                            print(f"SCAN {path}", flush=True)

                        row = self._build_row(path, stat)
                        self._upsert_track(session, row)

                        scanned += 1
                        pending += 1

                        if pending >= self.args.commit_every:
                            session.commit()
                            pending = 0

                        if total % self.args.progress_every == 0:
                            self._show_progress(total, scanned, skipped, failed)

                    except Exception as exc:
                        session.rollback()
                        pending = 0
                        failed += 1
                        self.logger.error(f"{path}: {exc}")

            except KeyboardInterrupt:
                interrupted = True
                print("\nInterrupted. Saving completed work...", flush=True)

            session.commit()

        return total, scanned, skipped, failed, interrupted

    def go(self):
        if not self.music_root.is_dir():
            self.logger.error(f"Music directory does not exist: {self.music_root}")
            return 1

        print(f"Music root: {self.music_root}", flush=True)
        print(f"PostgreSQL: {self.args.user}@{self.args.host}:{self.args.port}/{self.args.database}", flush=True)

        total, scanned, skipped, failed, interrupted = self._scan()

        self._show_progress(total, scanned, skipped, failed)
        self._show_catalog_summary()

        if interrupted:
            print("Scan interrupted. Run the same command to resume.", flush=True)
            return 130

        return 1 if failed else 0


if __name__ == "__main__":
    main = MusicScanner()
    raise SystemExit(main.go())