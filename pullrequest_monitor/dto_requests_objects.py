from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

# Base = automap_base() # declarative_base()
Base = declarative_base()

class GitUser(Base):
    __tablename__ = "git_user"

    id = Column(Integer, primary_key=True)
    login = Column(String(200), nullable=False)
    user_url = Column(String(2000), nullable=True)
    user_type = Column(String(20), nullable=True)

    def __repr__(self):
        return str(self.id) + ":" + self.login


class GitRepository(Base):
    __tablename__ = "git_repository"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(200), nullable=False)
    private = Column(Integer, default=0)
    repository_url = Column(String(500), nullable=False)
    description = Column(String(1000))

    owner_id = Column(Integer, ForeignKey("git_user.id"))
    owner = relationship("GitUser", back_populates="repositories")

    def __repr__(self):
        return str(self.id) + ":" + self.full_name


class GitPullRequest(Base):
    __tablename__ = "git_pullrequest"

    id = Column(Integer, primary_key=True)
    pull_number = Column(Integer, nullable=False)

    url = Column(String(2000), nullable=False)
    state = Column(String(20))
    title = Column(String(2000))

    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    merged_at = Column(DateTime)
    closed_at = Column(DateTime)
    merge_commit_sha = Column(String(100))

    user_id = Column(Integer, ForeignKey("git_user.id"))
    user = relationship("GitUser", back_populates="pulls")

    repository_id = Column(Integer, ForeignKey("git_repository.id"))
    repository = relationship("GitRepository", back_populates="pulls")

    def __repr__(self):
        return "PullRequest ID: " + str(self.id)


class PullRequestFile(Base):
    __tablename__ = "git_pullrequest_file"

    pull_id = Column(Integer, ForeignKey('git_pullrequest.id'), primary_key=True)
    filename = Column(String(2000), nullable=False, primary_key=True)
    sha = Column(String(100))
    # pull_number = Column(Integer, ForeignKey('git_pullrequest.pull_number'), primary_key=True)

    status = Column(String(20))
    additions = Column(Integer)
    deletions = Column(Integer)
    changes = Column(Integer)
    contents_url = Column(String(2000), nullable=False)

    pullrequest = relationship("GitPullRequest", back_populates="files")

    def __repr__(self):
        return str(self.pull_id) + ":" + self.filename


GitRepository.pulls = relationship("GitPullRequest", order_by=GitPullRequest.pull_number, back_populates="repository")
GitUser.repositories = relationship("GitRepository", order_by=GitRepository.id, back_populates="owner")
GitUser.pulls = relationship("GitPullRequest", order_by=GitPullRequest.pull_number, back_populates="user")
GitPullRequest.files = relationship("PullRequestFile", order_by=PullRequestFile.filename, back_populates="pullrequest")

# Base.prepare()


# GitUser.__table__.create(bind=engine, checkfirst=True)
# GitPullRequest.__table__.create(bind=engine, checkfirst=True)
# PullRequestFile.__table__.create(bind=engine, checkfirst=True)
