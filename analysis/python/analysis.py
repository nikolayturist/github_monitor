import pandas as pd
import numpy as np


# 1 Display Pull Request with min/avg/max time between open and merge
pulls = pd.read_csv("analysis/python/raw/git_pullrequest.csv", parse_dates=["created_at", "merged_at", "closed_at"])
pulls = pulls[
            ~np.isnat(pulls["merged_at"]) & ~np.isnat(pulls["merged_at"])
        ].loc[:, ["id", "repository_id", "created_at", "merged_at"]]

pulls["diff"] = pulls["merged_at"] - pulls["created_at"]
d = pulls["diff"].describe()
print("Minimum / Average /  Maximum time between Pull Request open and merge: \n" + str(d[["min", "mean", "max"]]))

# 2. Top 3 frequently changed files for each repository
pull_files = pd.read_csv("analysis/python/raw/git_pullrequest_file.csv")
repositories = pd.read_csv("analysis/python/raw/git_repository.csv")

pulls_repo = pulls.add_suffix("_pulls")\
     .merge(repositories.add_suffix("_repo"), left_on="repository_id_pulls", right_on="id_repo", sort=False)

files_pulls_repo = pull_files.add_suffix("_files").merge(pulls_repo, left_on="pull_id_files", right_on="id_pulls")
files_pulls_repo["cnt"] = 1
x = files_pulls_repo.loc[:, ["full_name_repo", "filename_files", "cnt"]]\
    .groupby(["full_name_repo", "filename_files"], sort=False).count()

x["rank"] = x.groupby(["full_name_repo"])["cnt"].rank(ascending=False)
print(x.loc[x["rank"] <= 3.0].sort_values(by=["full_name_repo", "rank"]))



