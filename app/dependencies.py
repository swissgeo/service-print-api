from typing import Annotated

import aioboto3

from fastapi import Depends, Request


async def get_session(request: Request) -> aioboto3.Session:
    return request.app.state.session


SessionDep = Annotated[aioboto3.Session, Depends(get_session)]
