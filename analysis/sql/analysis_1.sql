-- min time to merge pullrequest (minutes)
select round(min(merged_at - created_at) * 24 * 60, 3) merged_time from git_pullrequest
    where merged_at is not null and closed_at is not null;

-- find this pull request for min time pull request
select * from git_pullrequest where (merged_at - created_at) =
    (select min(merged_at - created_at) merged_time from git_pullrequest
        where merged_at is not null and closed_at is not null);

-- avg time to merge pullrequest (hours)
select round(avg(merged_at - created_at) * 24, 2) merged_time from git_pullrequest
    where merged_at is not null and closed_at is not null;

-- max time to merge pullrequest (days)
select round(max(merged_at - created_at), 2) merged_time from git_pullrequest
    where merged_at is not null and closed_at is not null;

-- top 3 changed files in pull requests for each repository
select * from (
    select tt.*, rank() over (partition by repository order by use_count desc) use_rank from (
    select filename, full_name repository, count(*) use_count
        from git_pullrequest_file prf, git_pullrequest pr, git_repository r
        where r.id = pr.repository_id and pr.id = prf.pull_id
        and merged_at is not null and closed_at is not null
        group by filename, full_name ) tt
) where use_rank <= 3;