SELECT
    id,
    artist,
    album,
    song,
    filename,
    similarity(song, 'Indian Giver') AS score
FROM music.tracks
WHERE song % 'Indian Giver'
ORDER BY score DESC
LIMIT 10;