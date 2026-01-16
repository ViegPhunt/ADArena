import secrets
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.models.base import Base

if TYPE_CHECKING:
    from lib.models.flag import Flag, StolenFlag
    from lib.models.teamtask import TeamTask



class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    ip: Mapped[str] = mapped_column(String(32), nullable=False)
    token: Mapped[str] = mapped_column(String(16), nullable=False, default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    flags: Mapped[list["Flag"]] = relationship(back_populates="team")
    team_tasks: Mapped[list["TeamTask"]] = relationship(back_populates="team")
    stolen_flags: Mapped[list["StolenFlag"]] = relationship(back_populates="attacker_team")
    
    @staticmethod
    def generate_token() -> str:
        return secrets.token_hex(8)