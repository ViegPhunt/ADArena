#!/usr/bin/env python3

import asyncio
from sqlalchemy import select

from lib.models import Team, get_session_factory


async def run():
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            select(Team.name, Team.token).where(Team.active)
        )
        teams = result.all()
    
    print('\n'.join(f"{name}:{token}" for name, token in teams))


if __name__ == '__main__':
    asyncio.run(run())