#!/usr/bin/env python3

import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher

from glslib import Application
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, SmallInteger, Text, create_engine, delete, func, insert, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Billboard(Base):
    __tablename__ = "billboard"
    __table_args__ = {"schema": "music"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chart_date: Mapped[date] = mapped_column(Date, nullable=False)
    song: Mapped[str] = mapped_column(Text, nullable=False)
    artist: Mapped[str] = mapped_column(Text, nullable=False)
    ranking: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = {"schema": "music"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    song: Mapped[str | None] = mapped_column(Text)
    artist: Mapped[str | None] = mapped_column(Text)


class BillboardTrack(Base):
    __tablename__ = "billboard_tracks"
    __table_args__ = {"schema": "music"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    billboard_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    track_id: Mapped[int | None] = mapped_column(BigInteger)

    candidate_rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)

    billboard_song: Mapped[str] = mapped_column(Text, nullable=False)
    billboard_artist: Mapped[str] = mapped_column(Text, nullable=False)

    track_song: Mapped[str | None] = mapped_column(Text)
    track_artist: Mapped[str | None] = mapped_column(Text)

    song_score: Mapped[float | None] = mapped_column(Float)
    artist_score: Mapped[float | None] = mapped_column(Float)
    match_score: Mapped[float | None] = mapped_column(Float)

    match_method: Mapped[str | None] = mapped_column(Text)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BillboardTracksLinker(Application):
    def __init__(self):
        super().__init__("Link Billboard chart entries to music tracks.")

        self.database_config = self.config.database
        self.matching_config = self.config.matching
        self.processing_config = self.config.processing

        self.match_cache = {}
        self.engine = self._create_engine()

    def _arg_parse(self, parser):
        return super()._arg_parse(parser)

    def _create_engine(self):
        url = f"postgresql+psycopg://{self.database_config.user}@{self.database_config.host}:{self.database_config.port}/{self.database_config.database}"
        return create_engine(url, echo=False, pool_pre_ping=True)

    def _normalize(self, value):
        if not value:
            return ""

        value = unicodedata.normalize("NFKD", value)
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value.lower()
        value = value.replace("&", " and ")
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def _similarity(self, left, right):
        left = self._normalize(left)
        right = self._normalize(right)

        if not left or not right:
            return 0.0

        if left == right:
            return 1.0

        return SequenceMatcher(None, left, right).ratio()

    def _candidate_statement(self, billboard):
        song_similarity = func.similarity(Track.song, billboard.song)

        return (
            select(Track.id, Track.song, Track.artist, song_similarity.label("pg_song_score"))
            .where(Track.song.is_not(None))
            .where(Track.song.op("%")(billboard.song))
            .order_by(song_similarity.desc())
            .limit(self.matching_config.candidate_limit)
        )

    def _get_candidates(self, session, billboard):
        statement = self._candidate_statement(billboard)
        return session.execute(statement).all()

    def _score_candidate(self, billboard, candidate):
        song_score = self._similarity(billboard.song, candidate.song)
        artist_score = self._similarity(billboard.artist, candidate.artist)
        match_score = song_score * artist_score

        return {
            "track_id": candidate.id,
            "track_song": candidate.song,
            "track_artist": candidate.artist,
            "song_score": song_score,
            "artist_score": artist_score,
            "match_score": match_score,
        }

    def _score_candidates(self, session, billboard):
        matches = []

        for candidate in self._get_candidates(session, billboard):
            matches.append(self._score_candidate(billboard, candidate))

        matches.sort(key=lambda match: match["match_score"], reverse=True)

        return matches[:self.matching_config.max_candidates_to_store]

    def _get_matches(self, session, billboard):
        key = (self._normalize(billboard.song), self._normalize(billboard.artist))

        if key not in self.match_cache:
            self.match_cache[key] = self._score_candidates(session, billboard)

        return self.match_cache[key]

    def _accepted(self, match):
        if match is None:
            return False

        if match["song_score"] < self.matching_config.min_song_score:
            return False

        if match["artist_score"] < self.matching_config.min_artist_score:
            return False

        if match["match_score"] < self.matching_config.min_match_score:
            return False

        return True

    def _match_method(self, match, accepted):
        if not accepted:
            return "candidate"

        if match["song_score"] == 1.0 and match["artist_score"] == 1.0:
            return "exact"

        return "fuzzy"

    def _build_candidate_rows(self, billboard, matches):
        rows = []

        if not matches:
            rows.append(
                {
                    "billboard_id": billboard.id,
                    "track_id": None,
                    "candidate_rank": 1,
                    "accepted": False,
                    "billboard_song": billboard.song,
                    "billboard_artist": billboard.artist,
                    "track_song": None,
                    "track_artist": None,
                    "song_score": None,
                    "artist_score": None,
                    "match_score": None,
                    "match_method": "unmatched",
                }
            )

            return rows

        for rank, match in enumerate(matches, start=1):
            accepted = rank == 1 and self._accepted(match)

            rows.append(
                {
                    "billboard_id": billboard.id,
                    "track_id": match["track_id"],
                    "candidate_rank": rank,
                    "accepted": accepted,
                    "billboard_song": billboard.song,
                    "billboard_artist": billboard.artist,
                    "track_song": match["track_song"],
                    "track_artist": match["track_artist"],
                    "song_score": match["song_score"],
                    "artist_score": match["artist_score"],
                    "match_score": match["match_score"],
                    "match_method": self._match_method(match, accepted),
                }
            )

        return rows

    def _flush_batch(self, session, rows, billboard_ids):
        if not rows:
            return

        if self.processing_config.rematch:
            statement = delete(BillboardTrack).where(BillboardTrack.billboard_id.in_(billboard_ids))
            session.execute(statement)

        session.execute(insert(BillboardTrack), rows)
        session.commit()

    def _billboard_statement(self):
        statement = select(Billboard)

        if not self.processing_config.rematch:
            linked = select(BillboardTrack.billboard_id).where(BillboardTrack.billboard_id == Billboard.id)
            statement = statement.where(~linked.exists())

        return statement.order_by(Billboard.chart_date, Billboard.ranking)

    def _show_match(self, billboard, rows):
        first = rows[0]
        score = first["match_score"]
        score_text = "-" if score is None else f"{score:.3f}"

        print(
            f"{billboard.chart_date} #{billboard.ranking:3d} "
            f"{billboard.artist} - {billboard.song} -> "
            f"{first['track_artist'] or '-'} - {first['track_song'] or '-'} "
            f"[{first['match_method']} {score_text}] candidates={len(rows)}",
            flush=True,
        )

    def _show_progress(self, processed, matched, unmatched):
        print(f"processed={processed:,} matched={matched:,} unmatched={unmatched:,} cache={len(self.match_cache):,}", flush=True)

    def _link(self):
        processed = 0
        matched = 0
        unmatched = 0
        pending_billboards = 0
        pending_rows = []
        pending_billboard_ids = []
        interrupted = False

        with Session(self.engine) as session:
            try:
                statement = self._billboard_statement()

                for billboard in session.scalars(statement).yield_per(500):
                    matches = self._get_matches(session, billboard)
                    rows = self._build_candidate_rows(billboard, matches)

                    pending_rows.extend(rows)
                    pending_billboard_ids.append(billboard.id)
                    pending_billboards += 1

                    processed += 1

                    if rows[0]["accepted"]:
                        matched += 1
                    else:
                        unmatched += 1

                    if self.args.debug:
                        self._show_match(billboard, rows)

                    if pending_billboards >= self.processing_config.commit_every:
                        self._flush_batch(session, pending_rows, pending_billboard_ids)
                        pending_rows = []
                        pending_billboard_ids = []
                        pending_billboards = 0

                    if processed % self.processing_config.progress_every == 0:
                        self._show_progress(processed, matched, unmatched)

            except KeyboardInterrupt:
                interrupted = True
                session.rollback()
                print("\nInterrupted. Current uncommitted batch discarded.", flush=True)

            if not interrupted:
                self._flush_batch(session, pending_rows, pending_billboard_ids)

        return processed, matched, unmatched, interrupted

    def _show_summary(self):
        with Session(self.engine) as session:
            billboard_rows = session.scalar(select(func.count()).select_from(Billboard))
            candidate_rows = session.scalar(select(func.count()).select_from(BillboardTrack))
            processed_rows = session.scalar(select(func.count(func.distinct(BillboardTrack.billboard_id))))
            matched_rows = session.scalar(select(func.count()).select_from(BillboardTrack).where(BillboardTrack.accepted.is_(True)))

        print("Linkage summary:", flush=True)
        print(f"  billboard rows:  {billboard_rows:,}", flush=True)
        print(f"  processed rows:  {processed_rows:,}", flush=True)
        print(f"  candidate rows:  {candidate_rows:,}", flush=True)
        print(f"  accepted rows:   {matched_rows:,}", flush=True)
        print(f"  unmatched rows:  {processed_rows - matched_rows:,}", flush=True)
        print(f"  cache entries:   {len(self.match_cache):,}", flush=True)

    def go(self):
        print(f"PostgreSQL: {self.database_config.user}@{self.database_config.host}:{self.database_config.port}/{self.database_config.database}", flush=True)
        print(f"Thresholds: song={self.matching_config.min_song_score:.2f} artist={self.matching_config.min_artist_score:.2f} combined={self.matching_config.min_match_score:.2f}", flush=True)
        print(f"Candidates: evaluate={self.matching_config.candidate_limit} store={self.matching_config.max_candidates_to_store}", flush=True)

        processed, matched, unmatched, interrupted = self._link()

        self._show_progress(processed, matched, unmatched)
        self._show_summary()

        if interrupted:
            return 130

        return 0


if __name__ == "__main__":
    main = BillboardTracksLinker()
    raise SystemExit(main.go())