DROP TABLE IF EXISTS music.billboard_tracks;

CREATE TABLE music.billboard_tracks
(
    id                  bigserial PRIMARY KEY,

    billboard_id        bigint NOT NULL,
    track_id            bigint,

    candidate_rank      smallint NOT NULL,
    accepted            boolean NOT NULL DEFAULT false,

    billboard_song      text NOT NULL,
    billboard_artist    text NOT NULL,

    track_song          text,
    track_artist        text,

    song_score          double precision,
    artist_score        double precision,
    match_score         double precision,

    match_method        text,
    matched_at          timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT billboard_tracks_billboard_fk
        FOREIGN KEY (billboard_id)
        REFERENCES music.billboard(id)
        ON DELETE CASCADE,

    CONSTRAINT billboard_tracks_track_fk
        FOREIGN KEY (track_id)
        REFERENCES music.tracks(id)
        ON DELETE SET NULL,

    CONSTRAINT billboard_tracks_candidate_unique
        UNIQUE (billboard_id, candidate_rank)
);

CREATE INDEX billboard_tracks_track_idx
    ON music.billboard_tracks (track_id);

CREATE INDEX billboard_tracks_match_score_idx
    ON music.billboard_tracks (match_score);

CREATE INDEX billboard_tracks_billboard_idx
    ON music.billboard_tracks (billboard_id);