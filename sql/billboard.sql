CREATE SCHEMA IF NOT EXISTS music;

DROP TABLE IF EXISTS music.billboard;

CREATE TABLE music.billboard
(
    id          bigserial   PRIMARY KEY,
    chart_date  date        NOT NULL,
    song       text        NOT NULL,
    artist      text        NOT NULL,
    ranking     smallint    NOT NULL,

    CONSTRAINT billboard_ranking_check
        CHECK (ranking BETWEEN 1 AND 100)
);

CREATE INDEX billboard_chart_date_ranking_idx
    ON music.billboard (chart_date, ranking);

CREATE INDEX billboard_song_idx
    ON music.billboard (song);

CREATE INDEX billboard_artist_idx
    ON music.billboard (artist);