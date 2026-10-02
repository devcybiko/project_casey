with n1 as (
    select
        b.id,
        extract(year from b.chart_date)::integer as year,
        b.artist,
        b.song,
        b.ranking
    from music.billboard b
    where b.ranking <=10 and extract(year from b.chart_date) between 1960 and 1980
),
bt as (
    select 
        bt.track_id,
        bt.accepted
    from music.billboard_tracks bt
)
select 
    bt.accepted,
    n1.year,
    n1.artist,
    n1.song,
    min(t.filename)
from n1, bt, music.tracks t
where n1.id = bt.track_id
and bt.accepted = true
and t.id = bt.track_id
group by 
    bt.accepted,
    n1.year,
    n1.artist,
    n1.song
order by n1.year, n1.artist, n1.song