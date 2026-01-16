from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Float, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from lib.models.base import Base



class GameConfig(Base):
    """Game configuration - single row table (id=1).
    
    Key fields:
    - game_hardness: Difficulty multiplier (>= 1, affects scoring)
    - round_time: Duration of each round in seconds
    - flag_lifetime: Number of rounds a flag remains valid for submission
    - volga_attacks_mode: If True, teams can only attack when their service is UP
    - inflation: If True, flag values increase over time
    """
    __tablename__ = "gameconfig"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_running: Mapped[bool] = mapped_column(Boolean, default=False)
    game_hardness: Mapped[float] = mapped_column(Float, CheckConstraint("game_hardness >= 1"))
    max_round: Mapped[int] = mapped_column(Integer, CheckConstraint("max_round > 0"))
    round_time: Mapped[int] = mapped_column(Integer, CheckConstraint("round_time > 0"))
    real_round: Mapped[int] = mapped_column(Integer, default=0)
    flag_prefix: Mapped[str] = mapped_column(String(10), default='FLAG')
    flag_lifetime: Mapped[int] = mapped_column(Integer, CheckConstraint("flag_lifetime > 0"))
    inflation: Mapped[bool] = mapped_column(Boolean)
    volga_attacks_mode: Mapped[bool] = mapped_column(Boolean)
    timezone: Mapped[str] = mapped_column(String(32), default='UTC')
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "game_running": self.game_running,
            "game_hardness": self.game_hardness,
            "max_round": self.max_round,
            "round_time": self.round_time,
            "real_round": self.real_round,
            "flag_prefix": self.flag_prefix,
            "flag_lifetime": self.flag_lifetime,
            "inflation": self.inflation,
            "volga_attacks_mode": self.volga_attacks_mode,
            "timezone": self.timezone,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }