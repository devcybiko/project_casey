CREATE SCHEMA IF NOT EXISTS music AUTHORIZATION ai_app;

CREATE TABLE IF NOT EXISTS music.tracks (
    id BIGSERIAL PRIMARY KEY,

    filename TEXT NOT NULL UNIQUE,

    artist TEXT,
    album TEXT,
    song TEXT,
    release_year INTEGER,

    track_number INTEGER,
    disc_number INTEGER,
    genre TEXT,

    file_type TEXT,
    file_size BIGINT,
    duration_seconds DOUBLE PRECISION,

    artist_source TEXT,
    album_source TEXT,
    song_source TEXT,
    year_source TEXT,

    scanned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    modified_at DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS tracks_artist_idx
    ON music.tracks (artist);

CREATE INDEX IF NOT EXISTS tracks_album_idx
    ON music.tracks (album);

CREATE INDEX IF NOT EXISTS tracks_release_year_idx
    ON music.tracks (release_year);

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX tracks_song_trgm_idx
ON music.tracks
USING gin (song gin_trgm_ops);