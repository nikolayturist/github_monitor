import logging
import common
import dto_requests_objects as dto
from sqlalchemy.exc import SQLAlchemyError
import csv
import os


class GitHubLoader:

    def __init__(self, session, **args):
        log_level = "INFO"
        if "log_level" in args.keys():
            log_level = args["log_level"]

        self._logger = logging.getLogger("GitHubLoader")
        self._logger.addHandler(common.get_file_handler())
        self._logger.addHandler(common.get_console_handler())
        self._logger.setLevel(log_level)
        self._logger.info("Configured log level is: " + logging.getLevelName(self._logger.getEffectiveLevel()))

        self.session = session

        self.repositories = set()
        self.users = set()
        self.pulls = set()
        self.files = set()

        self._get_existed_data()

        # if self.loader_config["augmented_load"] == "Y":
        #     self._logger.info("--- Augmented load was used. Load all existing users from database. ---")
        #     self.users.extend([e[0] for e in self.session.query(dto.GitUser.login).all()])
        #     self._logger.info("Users loaded count: " + str(len(self.users)))

    def _get_existed_data(self):
        if self.session:
            self.repositories.add(r for r in self.session.query(dto.GitRepository.id).all())
            self.users.add(u for u in self.session.query(dto.GitUser.id).all())
            self.pulls.add(r for r in self.session.query(dto.GitPullRequest.id).all())

    def _load_data(self, values):
        if values:
            try:
                self.session.add_all(values)
                self.session.commit()

                self._logger.debug("Values were loaded to database: " + str(len(values)))
                return True

            except SQLAlchemyError as err:
                self._logger.error("Values were not loaded to database:\n" +
                                   "    --> Values:" + str(values) + "\n" +
                                   "    --> Error text:" + str(err))
                return False

    def add_repository(self, repository):
        if not repository or not isinstance(repository, dto.GitRepository):
            self._logger.error("Repository value is None or wrong type argument: " + str(type(repository)))
            raise ValueError("Repository value is None or wrong type argument: " + str(type(repository)))

        if repository.owner_id is None:
            self._logger.error("Repository owner is empty: " + str(repository))
            raise ValueError("Repository owner is empty: " + str(repository))

        if repository.id in self.repositories:
            self._logger.warning(">> SKIP: Repository was already loaded: " + str(repository))
            return True

        if self._load_data([repository]):
            self.users.add(repository.owner_id)
            self.repositories.add(repository.id)

            self._logger.info("Repository was loaded to database: " + str(repository))
        else:
            self.session.rollback()
            self._logger.error("Repository was not loaded: " + str(repository))
            return False

        return True

    def add_user(self, user):
        if not user or not isinstance(user, dto.GitUser):
            self._logger.error("User value is None or wrong type argument: " + str(type(user)))
            raise ValueError("User value is None or wrong type argument: " + str(type(user)))

        if user.id in self.users:
            self._logger.warning(">> SKIP: User was already loaded: " + str(user))
            return True

        if self._load_data([user]):
            self.users.add(user.id)
            self._logger.info("User was loaded to database: " + str(user))
        else:
            self.session.rollback()
            self._logger.error("User was not added to user list: " + str(user))
            return False

        return True

    def add_pull_request(self, pull):
        if not pull or not isinstance(pull, dto.GitPullRequest):
            self._logger.error("User value is None or wrong type argument: " + str(type(pull)))
            raise ValueError("User value is None or wrong type argument: " + str(type(pull)))

        if pull.user_id is None or pull.repository_id is None:
            self._logger.error("Pull request user or repository are empty: " + str(pull))
            raise ValueError("Pull request user or repository are empty: " + str(pull))

        if pull.id in self.pulls:
            self._logger.warning(">> SKIP: Pull Request was already loaded: " + str(pull))
            return True

        if self._load_data([pull]):
            self.users.add(pull.user_id)
            self.pulls.add(pull.id)
            self._logger.info("Pull Request was loaded to database: " + str(pull))
        else:
            self._logger.error("Pull Request was not added to user list: " + str(pull))
            return False

        return True

    def add_pull_request_files(self, files):
        if self._load_data(files):
            self._logger.info("Pull Request files were loaded to database. Count: " + str(len(files)))
            return True
        else:
            self.session.rollback()
            self._logger.error("Pull Request files were not loaded to database. Count: " + str(len(files)))
            return False

    def get_repositoryid_by_name(self, name):
        repo_id = self.session.query(dto.GitRepository.id).filter(dto.GitRepository.full_name == name).first()
        return repo_id

    def _read_table(self, cls):
        for row in self.session.query(cls):
            yield row

    def dump_to_file(self, outdir):

        for cls in dto.Base.__subclasses__():

            filename = os.path.join(outdir, cls.__tablename__ + ".csv")

            outfile = open(filename, 'w', newline="\n", encoding="utf-8")
            outcsv = csv.writer(outfile)
            outcsv.writerow([column.name for column in cls.__mapper__.columns])
            [outcsv.writerow([getattr(curr, column.name) for column in cls.__mapper__.columns])
             for curr in self._read_table(cls)]
            # outcsv.writerows(records)
            outfile.close()
