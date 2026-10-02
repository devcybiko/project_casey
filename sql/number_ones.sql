with b as (
    select *, extract(year from b.chart_date) as year
    from music.billboard b
),
bt as (
    select * from music.billboard_tracks
),
t as (
    select * from music.tracks
),
x as (
    select min(t.id) id, b.year, b.artist, b.song, min(substr(t.filename,1,10)) filename
    from b, t, bt
    where true
    and t.id = bt.track_id
    and b.id = bt.billboard_id
    and b.ranking <= 1
    -- and b.year = 1970
    group by b.year, b.artist, b.song
    order by b.year, b.artist, b.song
)
-- select distinct x.year, count(*) as cnt
select *
from x
group by x.id, x.year, x.artist, x.song, x.filename
order by x.year, x.artist, x.song
