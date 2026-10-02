#!/bin/bash

function score_histogram() {
psql.sh "
with match_bins as (
    select
        case
            when accepted = false then 'unmatched'
            when match_score >= 0.95 then '0.95-1.00'
            when match_score >= 0.90 then '0.90-0.95'
            when match_score >= 0.85 then '0.85-0.90'
            when match_score >= 0.80 then '0.80-0.85'
            when match_score >= 0.75 then '0.75-0.80'
            else 'accepted <0.75'
        end as score_range
    from music.billboard_tracks
    where candidate_rank = 1
)
select
    score_range,
    count(*) as billboard_rows
from match_bins
group by score_range
order by
    case score_range
        when '0.95-1.00' then 1
        when '0.90-0.95' then 2
        when '0.85-0.90' then 3
        when '0.80-0.85' then 4
        when '0.75-0.80' then 5
        when 'accepted <0.75' then 6
        when 'unmatched' then 7
    end;
"
}
function matched_report() {
psql.sh "
with billboard_distinct as (
    select distinct song, artist
    from music.billboard
),
matched_distinct as (
    select distinct billboard_song as song, billboard_artist as artist
    from music.billboard_tracks
    where accepted = true
      and match_score >= 0.75
)
select
    count(*) as distinct_billboard_songs,
    count(*) filter (where m.song is not null) as matched_at_75,
    count(*) filter (where m.song is null) as unmatched_at_75,
    round(
        100.0 * count(*) filter (where m.song is not null) / count(*),
        2
    ) as matched_pct
from billboard_distinct b
left join matched_distinct m
    on m.song = b.song
   and m.artist = b.artist;
"
}
function top_hits_before_1980() {
psql.sh "
select *
from (
    select distinct on (bt.billboard_artist, bt.billboard_song)
        bt.billboard_artist,
        bt.billboard_song,
        bt.track_artist,
        bt.track_song,
        round(bt.song_score::numeric * 100, 1) as song_match_pct,
        round(bt.artist_score::numeric * 100, 1) as artist_match_pct,
        round(bt.match_score::numeric * 100, 1) as match_pct,
        bt.accepted
    from music.billboard_tracks bt
    where exists (
        select 1
        from music.billboard b
        where b.id = bt.billboard_id
          and b.chart_date < date '1980-01-01'
          and b.ranking <= 10
    )
    order by
        bt.billboard_artist,
        bt.billboard_song,
        bt.match_score desc nulls last,
        bt.candidate_rank
) x
order by
    match_pct desc nulls last,
    billboard_artist,
    billboard_song;
"
}
function yearly_top_10() {
#GregsHPZ8
psql.sh "
with yearly_top_10 as (
    select distinct
        extract(year from b.chart_date)::integer as year,
        b.artist,
        b.song
    from music.billboard b
    where b.ranking <= 10
),
matched as (
    select distinct
        bt.billboard_artist as artist,
        bt.billboard_song as song
    from music.billboard_tracks bt
    where bt.accepted = true
)
select
    y.year,
    count(*) as top_10_hits,
    count(*) filter (where m.song is not null) as have,
    count(*) filter (where m.song is null) as missing,
    round(
        100.0 * count(*) filter (where m.song is not null) / count(*),
        1
    ) as have_pct
from yearly_top_10 y
left join matched m
    on m.artist = y.artist
   and m.song = y.song
group by y.year
order by y.year;
"
}

function top_hits_before_1980_detail() {
psql.sh "
with yearly_top_10 as (
    select
        extract(year from b.chart_date)::integer as year,
        b.artist,
        b.song,
        min(b.ranking) as peak
    from music.billboard b
    where b.ranking <= 10 and extract(year from b.chart_date) < 1980
    group by
        extract(year from b.chart_date)::integer,
        b.artist,
        b.song
),
matched as (
    select distinct
        bt.billboard_artist as artist,
        bt.billboard_song as song
    from music.billboard_tracks bt
    where bt.accepted = true
)
select
    y.year,
    y.peak,
    case when m.song is not null then 'HAVE' else 'MISSING' end as status,
    y.artist,
    y.song
from yearly_top_10 y
left join matched m
    on m.artist = y.artist
   and m.song = y.song
order by
    y.year,
    y.peak,
    y.artist,
    y.song;
"
}

# score_histogram
# matched_report
# yearly_top_10
# top_hits_before_1980
top_hits_before_1980_detail
