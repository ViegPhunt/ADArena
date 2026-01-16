from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.models.base import Base

if TYPE_CHECKING:
    from lib.models.flag import Flag
    from lib.models.teamtask import TeamTask



class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    checker: Mapped[str] = mapped_column(String(1024))
    env_path: Mapped[str] = mapped_column(String(1024))
    gets: Mapped[int] = mapped_column(Integer, CheckConstraint("gets >= 0"))
    puts: Mapped[int] = mapped_column(Integer, CheckConstraint("puts >= 0"))
    places: Mapped[int] = mapped_column(Integer, CheckConstraint("places > 0"))
    checker_timeout: Mapped[int] = mapped_column(Integer, CheckConstraint("checker_timeout > 0"))
    checker_type: Mapped[str] = mapped_column(String(32), default='hackerdom')
    default_score: Mapped[int] = mapped_column(Integer, CheckConstraint("default_score >= 0"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    flags: Mapped[list["Flag"]] = relationship(back_populates="task")
    team_tasks: Mapped[list["TeamTask"]] = relationship(back_populates="task")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "checker": self.checker,
            "env_path": self.env_path,
            "gets": self.gets,
            "puts": self.puts,
            "places": self.places,
            "checker_timeout": self.checker_timeout,
            "checker_type": self.checker_type,
            "default_score": self.default_score,
            "active": self.active,
        }
    
    def to_dict_for_participants(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }
    
    @property
    def checker_tags(self) -> list[str]:
        return self.checker_type.split('_')
    
    @property
    def checker_returns_flag_id(self) -> bool:
        return 'nfr' not in self.checker_tags
    
    @property
    def checker_provides_public_flag_data(self) -> bool:
        return 'pfr' in self.checker_tags