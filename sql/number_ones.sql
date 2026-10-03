with b as (
    select *, extract(year from b.chart_date) as year
    from music.billboard b
),
bt as (
    select *
    from (
        select bt.*,
               rank() over (
                   partition by bt.billboard_id
                   order by bt.match_score desc nulls last
               ) as score_rank
        from music.billboard_tracks bt
    ) ranked_bt
    where score_rank = 1
),
t as (
    select * from music.tracks
),
x as (
        select min(t.id) id, b.year, b.artist, b.song, min(t.filename) as filename,
            max(bt.match_score) as match_score
    from b, t, bt
    where true
    and t.id = bt.track_id
    and b.id = bt.billboard_id
    and b.ranking <= 1
    and b.year = {{YEAR}}
    group by b.year, b.artist, b.song
    order by b.year, b.artist, b.song
)
-- select distinct x.year, count(*) as cnt
select x.id, x.year, x.artist, x.song, x.filename, x.match_score
from x
group by x.id, x.year, x.artist, x.song, x.filename, x.match_score
order by x.id, x.year, x.artist, x.song
