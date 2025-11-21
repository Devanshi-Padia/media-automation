import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from fastcrud import FastCRUD

from ..models.user import User
from ..schemas.user import UserCreateInternal, UserDelete, UserRead, UserUpdate, UserUpdateInternal

CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdate, UserUpdateInternal, UserDelete, UserRead]
crud_users = CRUDUser(User)
