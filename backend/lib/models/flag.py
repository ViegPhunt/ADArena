from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.models.base import Base

if TYPE_CHECKING:
    from lib.models.team import Team
    from lib.models.task import Task



class Flag(Base):
    """Flags placed on team services by checkers.
    
    Each flag is unique and tied to a specific team, task, and round.
    
    Fields:
    - public_flag_data: Shared with all teams (e.g., "place=3" for multi-place services)
    - private_flag_data: Known only to checker (e.g., session ID, used for GET action)
    - vuln_number: Which vulnerability this flag tests (for multi-vuln services)
    
    Flag lifecycle:
    1. Checker PUT action generates flag and places it on service
    2. Flag cached in Redis for fast lookup during submissions
    3. Other teams GET attack_data to learn public_flag_data
    4. Teams submit flag strings via /flags/ endpoint
    5. Flag expires after flag_lifetime rounds
    """
    __tablename__ = "flags"
    __table_args__ = (
        CheckConstraint("round >= 0"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default='')
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    public_flag_data: Mapped[str] = mapped_column(Text, nullable=False)
    private_flag_data: Mapped[str] = mapped_column(Text, nullable=False)
    vuln_number: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="flags")
    task: Mapped["Task"] = relationship(back_populates="flags")
    stolen_by: Mapped[list["StolenFlag"]] = relationship(back_populates="flag")


class StolenFlag(Base):
    """Record of successful flag captures.
    
    Composite primary key (flag_id, attacker_id) ensures:
    - Each team can only capture same flag once
    - Prevents duplicate scoring
    
    Created by recalculate_rating stored procedure when flag is accepted.
    """
    __tablename__ = "stolenflags"

    flag_id: Mapped[int] = mapped_column(Integer, ForeignKey("flags.id", ondelete="RESTRICT"), primary_key=True)
    attacker_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), primary_key=True)
    submit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    flag: Mapped["Flag"] = relationship(back_populates="stolen_by")
    attacker_team: Mapped["Team"] = relationship(back_populates="stolen_flags")