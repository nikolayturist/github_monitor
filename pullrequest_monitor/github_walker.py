import json
import common
import logging
import dto_requests_objects as dto
import github_loader
import time
from datetime import datetime


class GitHubWalker:

    # def __init__(self, db_session, loader_config, connection_config):
    def __init__(self, db_session, **args):
        self.rate_limits_url = "https://api.github.com/rate_limit"
        self.repositiry_url = "https://api.github.com/repos/{repo}"
        self.pull_request_url = "https://api.github.com/repos/{repo}/pulls"
        self.pull_files_url = "https://api.github.com/repos/{repo}/pulls/{pull_number}/files"

        # set some defaults
        batch_size = 100
        log_level = "INFO"
        request_status = "all"
        self.repository_list = []
        self.request_timeout = 0.5
        self.rate_limit_timeout = 3600

        if "loader" in args.keys():
            loader_config_file = args["loader"]
            with open(loader_config_file) as json_file:
                self.loader_config = json.load(json_file)

            log_level = self.loader_config["log_level"]
            batch_size = self.loader_config["batch_size"]
            request_status = self.loader_config["request_params"]["request_status"]
            self.repository_list = self.loader_config["repositories"]
            self.request_timeout = self.loader_config["request_params"]["timeout"]

        self._logger = logging.getLogger("GitHubWalker")
        self._logger.addHandler(common.get_file_handler())
        self._logger.addHandler(common.get_console_handler())
        self._logger.setLevel(log_level)
        self._logger.info("Configured log level is: " + logging.getLevelName(self._logger.getEffectiveLevel()))
        self._logger.info("Repositories list is: " + str(self.repository_list))

        github_key = ""
        if "connections" in args.keys():
            sec_config_file = args["connections"]
            with open(sec_config_file) as json_file:
                self.security_config = json.load(json_file)

            github_key = self.security_config["github"]["github_token"]

        self.pull_request_parameters = {
            "page": 1,
            "per_page": batch_size,
            "state": request_status
        }
        self._logger.info("Pull Requests parameters are: " + str(self.pull_request_parameters))

        self.files_request_parameters = {
            "page": 1,
            "per_page": batch_size
        }
        self._logger.info("Files Request parameters are: " + str(self.files_request_parameters))

        self.request_session = common.configure_http_session(github_key)
        self.rate_limit, self.reset_period = self._get_rate_limits()
        self.ghl = github_loader.GitHubLoader(db_session, log_level=log_level)

    def _get_rate_limits(self):
        rsp = self.request_session.get(self.rate_limits_url)
        remaining = 0
        reset = time.time()
        if rsp.status_code == 200:
            rsp = rsp.json()
            remaining = rsp["resources"]["core"]["remaining"]
            reset = rsp["resources"]["core"]["reset"]
            self._logger.info("Remaining rate limit for CORE is: " + str(remaining))

        return remaining, reset

    def _make_request(self, url, params=None):
        result = {}
        try:
            response = self.request_session.get(url, params=params)
            if response.status_code == 200:
                result = response.json()
            elif response.status_code == 404:
                self._logger.error("Object Not Found:  " + url + " with params :" + str(params) + ". Status code: " +
                                   str(response.status_code))
            else:
                self._logger.error("Error occurred for:  " + url + " with params :" + str(params) + ". Status code: " +
                                   str(response.status_code))

        except self.request_session.exceptions.HTTPError or self.request_session.exceptions.ConnectionError or \
                self.request_session.exceptions.Timeout or self.request_session.exceptions.RequestException as errh:
            self._logger.error("Error occurred while sending requests to " + url + " with params :" + str(params) +
                               ". Error :" + str(errh))

        return result

    def repository_walk(self):
        loaded_count = 0
        for repo in self.repository_list:
            if self.rate_limit <= 0:
                self._logger.info("Rate limits exceeded")
                self.rate_limit, self.reset_period = self._get_rate_limits()
                time.sleep(self.reset_period - round(time.time()))
                self._logger.info("Rate limits refreshed")

            self._logger.info("Current repository is: " + repo)
            rr = self._make_request(url=self.repositiry_url.format(repo=repo))

            # consider correct answer if we have "id" field
            if "id" in rr.keys():

                gr = dto.GitRepository(id=rr["id"], full_name=rr["full_name"], repository_url=rr["html_url"])
                gr.description = rr["description"]
                gr.private = rr["private"]

                gr_owner = rr["owner"]
                owner = dto.GitUser(id=gr_owner["id"], login=gr_owner["login"])
                owner.user_url = gr_owner["html_url"]
                owner.user_type = gr_owner["type"]

                gr.owner_id = owner.id
                gr.owner = owner

                self._logger.info("Repository object created: " + str(gr))
                self._logger.info("Repository owner object created: " + str(owner))

                if self.ghl.add_repository(gr):
                    loaded_count += 1

                self.rate_limit -= 1
            else:
                self._logger.error("Repository not found: " + repo)

            time.sleep(self.request_timeout)

        return loaded_count

    def pull_requests_walk(self, collect_files=True):
        loaded_count = 0
        dt_fmt = "%Y-%m-%dT%H:%M:%SZ"
        for repo in self.repository_list:
            result = self.ghl.get_repositoryid_by_name(repo)
            self._logger.info("Get pull requests info. Current repository is: " + repo)

            if result:
                repository_id = result[0]
                while True:
                    if self.rate_limit <= 0:
                        self._logger.info("Rate limits exceeded")
                        self.rate_limit, self.reset_period = self._get_rate_limits()
                        time.sleep(self.reset_period - round(time.time()))
                        self._logger.info("Rate limits refreshed")

                    pulls = self._make_request(url=self.pull_request_url.format(repo=repo),
                                               params=self.pull_request_parameters)
                    self.rate_limit -= 1

                    self._logger.info("Pulls count received for page " + str(self.pull_request_parameters["page"])
                                      + " is :" + str(len(pulls)))

                    if len(pulls) > 0:
                        self.pull_request_parameters["page"] += 1

                        for pull in pulls:
                            pull_id = pull["id"]
                            pull_number = pull["number"]
                            self._logger.info("   --> Starting processing pull with ID=" + str(pull_id))
                            gu = pull["user"]
                            if gu["id"] not in self.ghl.users:
                                self._logger.debug("   --> User " + gu["login"] + " doesn't exist in git_user table.")
                                git_user = dto.GitUser(id=gu["id"], login=gu["login"])
                                git_user.user_url = gu["html_url"]
                                git_user.user_type = gu["type"]
                                self._logger.debug("   --> User " + gu["login"] + " added to git_user table.")

                                self.ghl.add_user(git_user)

                            if pull["id"] not in self.ghl.pulls:

                                self._logger.debug("   --> Pull request " + str(pull_id) +
                                                   " doesn't exist in git_pullrequest table.")

                                gpr = dto.GitPullRequest(url=pull["url"], id=pull_id)
                                gpr.user_id = gu["id"]
                                gpr.state = pull["state"]
                                gpr.created_at = datetime.strptime(pull["created_at"], dt_fmt)
                                gpr.merge_commit_sha = pull["merge_commit_sha"]
                                gpr.title = pull["title"]
                                gpr.repository_id = repository_id
                                gpr.pull_number = pull_number
                                # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> " + str(pull["updated_at"]))

                                if pull["updated_at"]:
                                    gpr.updated_at = datetime.strptime(pull["updated_at"], dt_fmt)
                                if pull["closed_at"]:
                                    gpr.closed_at = datetime.strptime(pull["closed_at"], dt_fmt)
                                if pull["merged_at"]:
                                    gpr.merged_at = datetime.strptime(pull["merged_at"], dt_fmt)

                                if self.ghl.add_pull_request(gpr):
                                    loaded_count += 1
                                    self._logger.info("Pull request with ID=" + str(pull["id"]) + " added")
                            else:
                                self._logger.warning("   --> Pull request with ID=" + str(pull["id"]) + " skipped")

                            if collect_files:
                                self.pull_request_files_walk(repo, pull_id, pull_number)

                    else:
                        break
            else:
                self._logger.warning("Unable to get repository id for repository name = " + repo)
            self.pull_request_parameters["page"] = 1

        return loaded_count

    def pull_request_files_walk(self, repository, pull_id, pull_number):
        self._logger.info("    --> Starting pull request files processing for request number: " + str(pull_number))
        while True:
            self._logger.info("    --> Processing page : " + str(self.files_request_parameters["page"]))
            if self.rate_limit <= 0:
                self._logger.warning("Rate limits exceeded")
                self.rate_limit, self.reset_period = self._get_rate_limits()
                time.sleep(self.reset_period - round(time.time()))
                self._logger.info("Rate limits refreshed")

            files = self._make_request(url=self.pull_files_url.format(repo=repository, pull_number=pull_number),
                                       params=self.files_request_parameters)
            received_files = []
            for f in files:
                self._logger.debug("    --> Filename is :" + f["filename"])
                # github_logger.info("File recieved: " + str(f))
                ghf = dto.PullRequestFile(pull_id=pull_id, sha=f["sha"], filename=f["filename"])
                ghf.status = f["status"]
                ghf.additions = f["additions"]
                ghf.changes = f["changes"]
                ghf.deletions = f["deletions"]
                ghf.contents_url = f["contents_url"]

                received_files.append(ghf)

            self.ghl.add_pull_request_files(received_files)
            self.rate_limit -= 1
            time.sleep(self.request_timeout)

            if len(received_files) < self.files_request_parameters["per_page"]:
                break
            else:
                self.files_request_parameters["page"] += 1

        self.files_request_parameters["page"] = 1
