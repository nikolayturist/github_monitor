import pandas as pd
import numpy as np
import json


CONNECTIONS_CONFIG = "config/connections_config_local.json"

with open(CONNECTIONS_CONFIG) as f:
    conn_cfg = json.load(f)

cluster_machines = conn_cfg["machines_cluster"]

# load and build the same data as in single machine case
repositories = pd.read_csv("analysis/python/raw/git_repository.csv")
pulls = pd.read_csv("analysis/python/raw/git_pullrequest.csv",
                    parse_dates=["created_at", "merged_at", "closed_at"])
pull_files = pd.read_csv("analysis/python/raw/git_pullrequest_file.csv")

pulls = pulls[
            ~np.isnat(pulls["merged_at"]) & ~np.isnat(pulls["merged_at"])
        ].loc[:, ["id", "repository_id", "created_at", "merged_at"]]

pulls["diff"] = pulls["merged_at"] - pulls["created_at"]


def analyze_data(data):
    import socket
    data["cnt"] = 1
    x = data.loc[:, ["repo_name", "filename", "cnt"]] \
        .groupby(["repo_name", "filename"], sort=False).count()
    x["rank"] = x.groupby(["repo_name"])["cnt"].rank(ascending=False)
    most_used_files = x.loc[x["rank"] <= 3.0].sort_values(by=["repo_name", "rank"])

    return socket.gethostname(), most_used_files


if __name__ == '__main__':
    import dispy
    cluster = dispy.JobCluster(analyze_data, nodes=cluster_machines)
    jobs = []

    jobs_count = len(repositories.index)

    for indx in repositories.index:

        repo = repositories.loc[indx, ["id", "full_name"]]
        one_repo_pulls = pulls[pulls["repository_id"] == repo["id"]]
        one_repo_files = pull_files[pull_files["pull_id"].isin(one_repo_pulls["id"])]
        one_repo_files.loc[:, "repo_id"] = repo["id"]
        one_repo_files.loc[:, "repo_name"] = repo["full_name"]

        job = cluster.submit(one_repo_files)
        job.id = indx
        jobs.append(job)

    for job in jobs:
        # waits for job to finish and returns results
        host, res = job()
        print('%s executed job %s at %s with %s' % (host, job.id, job.start_time, res))

    cluster.print_status()
    cluster.close()
