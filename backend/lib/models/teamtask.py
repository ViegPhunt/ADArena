from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Float, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.models.base import Base

if TYPE_CHECKING:
    from lib.models.team import Team
    from lib.models.task import Task



class TeamTask(Base):
    """Service status and score for each team-task pair.
    
    Composite primary key (team_id, task_id) ensures one record per pair.
    
    Fields:
    - status: Overall service health code (101=UP, 102=CORRUPT, 103=MUMBLE, 104=DOWN, 110=CHECK_FAILED, -1=not checked)
    - check_status/put_status/get_status: Individual action status codes (-1=not run, 101=OK, 110=FAILED)
    - check_message/put_message/get_message: Per-action messages for debugging
    - check_attempts/put_attempts/get_attempts: Count of attempts for each action
    - stolen: Count of flags this team captured from this service
    - lost: Count of flags other teams captured from this team's service
    - score: Current score for this service (dynamic, affected by attacks)
    - checks/checks_passed: Used to calculate SLA percentage
    - public_message: Shown to team (computed from action messages)
    - private_message: Shown only to admins (debug info)
    """
    __tablename__ = "teamtasks"
    __table_args__ = (
        CheckConstraint("stolen >= 0"),
        CheckConstraint("lost >= 0"),
        CheckConstraint("score >= 0"),
        # SLA constraint: checks_passed cannot exceed checks
        CheckConstraint("checks >= 0 AND checks_passed >= 0 AND checks_passed <= checks", name="sla_valid"),
        # Action status constraints
        CheckConstraint("check_status IN (-1, 101, 102, 103, 104, 110)", name="check_status_valid"),
        CheckConstraint("put_status IN (-1, 101, 102, 103, 104, 110)", name="put_status_valid"),
        CheckConstraint("get_status IN (-1, 101, 102, 103, 104, 110)", name="get_status_valid"),
        CheckConstraint("check_attempts >= 0 AND put_attempts >= 0 AND get_attempts >= 0", name="attempts_valid"),
    )

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    
    # Overall computed status
    status: Mapped[int] = mapped_column(Integer, default=-1)
    
    # Per-action status tracking
    check_status: Mapped[int] = mapped_column(Integer, default=-1)
    check_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    check_private: Mapped[str] = mapped_column(Text, nullable=False, default='')
    check_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    put_status: Mapped[int] = mapped_column(Integer, default=-1)
    put_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    put_private: Mapped[str] = mapped_column(Text, nullable=False, default='')
    put_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    get_status: Mapped[int] = mapped_column(Integer, default=-1)
    get_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    get_private: Mapped[str] = mapped_column(Text, nullable=False, default='')
    get_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Scoring and counters
    stolen: Mapped[int] = mapped_column(Integer, default=0)
    lost: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    checks: Mapped[int] = mapped_column(Integer, default=0)
    checks_passed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Legacy fields (for backward compatibility and aggregated display)
    public_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    private_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    command: Mapped[str] = mapped_column(Text, nullable=False, default='')

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="team_tasks")
    task: Mapped["Task"] = relationship(back_populates="team_tasks")


class TeamTaskLog(Base):
    """Historical log of TeamTask snapshots at end of each round.
    
    Ticker calls log_teamtask_to_history() at the end of each round
    to preserve state for historical charts and analysis.
    """
    __tablename__ = "teamtaskslog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[int] = mapped_column(Integer)
    team_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[int] = mapped_column(Integer)
    stolen: Mapped[int] = mapped_column(Integer, default=0)
    lost: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    checks: Mapped[int] = mapped_column(Integer, default=0)
    checks_passed: Mapped[int] = mapped_column(Integer, default=0)
    public_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    private_message: Mapped[str] = mapped_column(Text, nullable=False, default='')
    command: Mapped[str] = mapped_column(Text, nullable=False, default='')
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ScheduleHistory(Base):
    __tablename__ = "schedulehistory"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_run: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
