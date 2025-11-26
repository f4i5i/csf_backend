# Milestone 1: Foundation, Auth & Class Browsing

## Overview
- **Duration**: Week 1 (Days 1-7)
- **Estimated Hours**: 50-55 hours
- **Focus**: Project setup, authentication, and class browsing APIs

## Patterns to Follow

### Database Model Pattern
```python
import enum
from typing import Optional, Sequence
from sqlalchemy import ForeignKey, String, Enum, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from core.db import Base
from core.db.mixins import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column("id", String(36), primary_key=True)
    email: Mapped[str] = mapped_column("email", String(255), unique=True, index=True)

    @classmethod
    async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["User"]:
        result = await db_session.execute(select(cls).where(cls.id == id))
        return result.scalars().first()

    @classmethod
    async def get_by_email(cls, db_session: AsyncSession, email: str) -> Optional["User"]:
        result = await db_session.execute(select(cls).where(cls.email == email))
        return result.scalars().first()
```

### Directory Structure Pattern
```
csf_backend/
├── core/                    # Infrastructure layer
│   ├── __init__.py
│   ├── config.py            # Settings (pydantic-settings)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py       # DB connection, engines, get_db
│   │   ├── mixins.py        # TimestampMixin, etc.
│   │   └── base.py          # Base declarative class
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── base.py          # CustomException
│   └── fastapi/
│       ├── __init__.py
│       └── middlewares/
│           └── __init__.py
├── app/
│   ├── __init__.py
│   ├── models/              # SQLAlchemy models with class methods
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── utils/
│       ├── security.py      # Password hashing, JWT
│       └── encryption.py    # PII encryption
├── api/
│   ├── __init__.py
│   ├── router.py            # Main router
│   ├── deps.py              # Dependencies (get_current_user)
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       └── classes.py
├── tests/
├── alembic/
├── main.py                  # FastAPI app with lifespan
└── pyproject.toml
```

---

## Task Breakdown

### Task 1: Core Infrastructure Setup
**Estimated Time**: 4-5 hours

#### User Story
As a developer, I want a well-organized project structure following the established patterns so that the codebase is maintainable.

#### Acceptance Criteria
- [ ] `core/` directory created with config, db, exceptions
- [ ] Environment variables loaded via pydantic-settings
- [ ] Custom logger configured
- [ ] Base exception class created

#### Implementation Steps
1. Create directory structure:
   ```
   core/
   ├── __init__.py
   ├── config.py
   ├── db/
   │   ├── __init__.py
   │   ├── session.py
   │   ├── mixins.py
   │   └── base.py
   ├── exceptions/
   │   ├── __init__.py
   │   └── base.py
   └── fastapi/
       └── middlewares/
   ```

2. Install dependencies:
   ```bash
   uv add fastapi uvicorn[standard] pydantic-settings python-dotenv
   ```

3. Create `core/config.py`:
   ```python
   from pydantic_settings import BaseSettings
   from functools import lru_cache

   class Settings(BaseSettings):
       APP_NAME: str = "csf-backend"
       APP_ENV: str = "development"
       DEBUG: bool = True

       # Database
       DATABASE_URL: str
       DATABASE_POOL_SIZE: int = 20
       DATABASE_MAX_OVERFLOW: int = 10

       # Auth
       SECRET_KEY: str
       JWT_ALGORITHM: str = "HS256"
       JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
       JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

       # Google OAuth
       GOOGLE_CLIENT_ID: str = ""
       GOOGLE_CLIENT_SECRET: str = ""

       # CORS
       CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

       class Config:
           env_file = ".env"
           case_sensitive = True

   @lru_cache
   def get_settings() -> Settings:
       return Settings()

   config = get_settings()
   ```

4. Create `core/exceptions/base.py`:
   ```python
   from typing import Any, Dict, Optional

   class CustomException(Exception):
       code: int = 500
       error_code: str = "BASE__SERVER_ERROR"
       message: str = "Server error"
       data: Optional[Dict[str, Any]] = None

       def __init__(
           self,
           message: str = None,
           code: int = None,
           error_code: str = None,
           data: Dict[str, Any] = None
       ):
           self.message = message or self.message
           self.code = code or self.code
           self.error_code = error_code or self.error_code
           self.data = data or {}
           super().__init__(self.message)

   class BadRequestException(CustomException):
       code = 400
       error_code = "BAD_REQUEST"
       message = "Bad request"

   class UnauthorizedException(CustomException):
       code = 401
       error_code = "UNAUTHORIZED"
       message = "Unauthorized"

   class ForbiddenException(CustomException):
       code = 403
       error_code = "FORBIDDEN"
       message = "Forbidden"

   class NotFoundException(CustomException):
       code = 404
       error_code = "NOT_FOUND"
       message = "Resource not found"
   ```

5. Create `.env.example`

#### Dependencies
- None (first task)

---

### Task 2: Database Connection Setup
**Estimated Time**: 5-6 hours

#### User Story
As a developer, I want async PostgreSQL connection with proper session management following the existing pattern.

#### Acceptance Criteria
- [ ] Async engine with connection pooling
- [ ] `get_db()` async generator for dependency injection
- [ ] `TimestampMixin` with created_at, updated_at
- [ ] Base declarative class configured
- [ ] Alembic configured for async migrations

#### Implementation Steps
1. Install database dependencies:
   ```bash
   uv add sqlalchemy[asyncio] asyncpg alembic greenlet
   ```

2. Create `core/db/base.py`:
   ```python
   from sqlalchemy.orm import declarative_base
   Base = declarative_base()
   ```

3. Create `core/db/mixins.py`:
   ```python
   from datetime import datetime
   from sqlalchemy import DateTime, func
   from sqlalchemy.orm import Mapped, mapped_column

   class TimestampMixin:
       created_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True),
           server_default=func.now(),
           nullable=False
       )
       updated_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True),
           server_default=func.now(),
           onupdate=func.now(),
           nullable=False
       )
   ```

4. Create `core/db/session.py`:
   ```python
   from typing import AsyncGenerator
   from sqlalchemy.ext.asyncio import (
       AsyncSession,
       create_async_engine,
       async_sessionmaker,
   )
   from core.config import config
   from core.db.base import Base

   engine = create_async_engine(
       config.DATABASE_URL,
       pool_size=config.DATABASE_POOL_SIZE,
       max_overflow=config.DATABASE_MAX_OVERFLOW,
       pool_recycle=3600,
       pool_pre_ping=True,
       echo=config.DEBUG,
   )

   async_session_factory = async_sessionmaker(
       bind=engine,
       class_=AsyncSession,
       expire_on_commit=False,
       autoflush=False,
   )

   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       async with async_session_factory() as session:
           try:
               yield session
           finally:
               await session.close()
   ```

5. Create `core/db/__init__.py`:
   ```python
   from core.db.base import Base
   from core.db.session import get_db, engine, async_session_factory
   from core.db.mixins import TimestampMixin

   __all__ = ["Base", "get_db", "engine", "async_session_factory", "TimestampMixin"]
   ```

6. Initialize Alembic:
   ```bash
   uv run alembic init alembic
   ```

7. Configure `alembic/env.py` for async

#### Dependencies
- Task 1 (Core Infrastructure)

---

### Task 3: User Model
**Estimated Time**: 4-5 hours

#### User Story
As a system, I need a User model with class methods for database queries following the established pattern.

#### Acceptance Criteria
- [ ] User model with all required fields
- [ ] Class methods: `get_by_id`, `get_by_email`, `create_user`
- [ ] Role enum (OWNER, ADMIN, STAFF, PARENT)
- [ ] Password stored as hash
- [ ] Migration creates table successfully

#### Implementation Steps
1. Install security dependencies:
   ```bash
   uv add passlib[bcrypt] python-jose[cryptography]
   ```

2. Create `app/utils/security.py`:
   ```python
   from passlib.context import CryptContext

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def hash_password(password: str) -> str:
       return pwd_context.hash(password)

   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)
   ```

3. Create `app/models/user.py`:
   ```python
   import enum
   from uuid import uuid4
   from typing import Optional, Sequence
   from sqlalchemy import String, Enum, Boolean, DateTime, select
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy.orm import Mapped, mapped_column
   from core.db import Base, TimestampMixin

   class Role(str, enum.Enum):
       OWNER = "owner"
       ADMIN = "admin"
       STAFF = "staff"
       PARENT = "parent"

   class User(Base, TimestampMixin):
       __tablename__ = 'users'

       id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
       email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
       hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
       first_name: Mapped[str] = mapped_column(String(100), nullable=False)
       last_name: Mapped[str] = mapped_column(String(100), nullable=False)
       phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
       role: Mapped[Role] = mapped_column(Enum(Role), default=Role.PARENT, nullable=False)
       is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
       is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
       google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
       stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
       last_login: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

       @classmethod
       async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["User"]:
           result = await db_session.execute(select(cls).where(cls.id == id))
           return result.scalars().first()

       @classmethod
       async def get_by_email(cls, db_session: AsyncSession, email: str) -> Optional["User"]:
           result = await db_session.execute(select(cls).where(cls.email == email))
           return result.scalars().first()

       @classmethod
       async def get_by_google_id(cls, db_session: AsyncSession, google_id: str) -> Optional["User"]:
           result = await db_session.execute(select(cls).where(cls.google_id == google_id))
           return result.scalars().first()

       @classmethod
       async def create_user(
           cls,
           db_session: AsyncSession,
           email: str,
           first_name: str,
           last_name: str,
           hashed_password: Optional[str] = None,
           google_id: Optional[str] = None,
           role: Role = Role.PARENT
       ) -> "User":
           user = cls(
               email=email,
               first_name=first_name,
               last_name=last_name,
               hashed_password=hashed_password,
               google_id=google_id,
               role=role
           )
           db_session.add(user)
           await db_session.commit()
           await db_session.refresh(user)
           return user

       @classmethod
       async def get_all(cls, db_session: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence["User"]:
           result = await db_session.execute(
               select(cls).offset(skip).limit(limit).order_by(cls.created_at.desc())
           )
           return result.scalars().all()
   ```

4. Create `app/models/__init__.py`:
   ```python
   from app.models.user import User, Role
   __all__ = ["User", "Role"]
   ```

5. Create migration:
   ```bash
   uv run alembic revision --autogenerate -m "create_users_table"
   uv run alembic upgrade head
   ```

#### Dependencies
- Task 2 (Database Connection)

---

### Task 4: Authentication Schemas
**Estimated Time**: 2-3 hours

#### User Story
As a developer, I want Pydantic V2 schemas for authentication validation.

#### Acceptance Criteria
- [ ] UserCreate, UserLogin, UserResponse schemas
- [ ] TokenResponse schema
- [ ] All schemas use Pydantic V2 syntax
- [ ] Proper validation rules

#### Implementation Steps
1. Create `app/schemas/base.py`:
   ```python
   from pydantic import BaseModel, ConfigDict

   class BaseSchema(BaseModel):
       model_config = ConfigDict(
           from_attributes=True,
           populate_by_name=True,
           str_strip_whitespace=True
       )
   ```

2. Create `app/schemas/user.py`:
   ```python
   from datetime import datetime
   from typing import Optional
   from pydantic import EmailStr, Field, field_validator
   from app.schemas.base import BaseSchema
   from app.models.user import Role

   class UserCreate(BaseSchema):
       email: EmailStr
       password: str = Field(..., min_length=8, max_length=100)
       first_name: str = Field(..., min_length=1, max_length=100)
       last_name: str = Field(..., min_length=1, max_length=100)
       phone: Optional[str] = Field(None, max_length=20)

       @field_validator('password')
       @classmethod
       def validate_password(cls, v: str) -> str:
           if not any(c.isupper() for c in v):
               raise ValueError('Password must contain at least one uppercase letter')
           if not any(c.islower() for c in v):
               raise ValueError('Password must contain at least one lowercase letter')
           if not any(c.isdigit() for c in v):
               raise ValueError('Password must contain at least one digit')
           return v

   class UserLogin(BaseSchema):
       email: EmailStr
       password: str

   class UserUpdate(BaseSchema):
       first_name: Optional[str] = Field(None, min_length=1, max_length=100)
       last_name: Optional[str] = Field(None, min_length=1, max_length=100)
       phone: Optional[str] = Field(None, max_length=20)

   class UserResponse(BaseSchema):
       id: str
       email: str
       first_name: str
       last_name: str
       phone: Optional[str]
       role: Role
       is_active: bool
       is_verified: bool
       created_at: datetime

   class TokenResponse(BaseSchema):
       access_token: str
       refresh_token: str
       token_type: str = "bearer"

   class TokenPayload(BaseSchema):
       sub: str  # user_id
       role: str
       exp: int
       type: str  # "access" or "refresh"

   class GoogleAuthRequest(BaseSchema):
       token: str
   ```

3. Create `app/schemas/__init__.py`

#### Dependencies
- Task 3 (User Model)

---

### Task 5: JWT Token System
**Estimated Time**: 4-5 hours

#### User Story
As a user, I want JWT tokens for authentication so I can make authenticated API calls.

#### Acceptance Criteria
- [ ] Access token (30 min expiry)
- [ ] Refresh token (7 days expiry)
- [ ] Token contains user_id, role, type
- [ ] Token verification works
- [ ] Invalid tokens raise UnauthorizedException

#### Implementation Steps
1. Update `app/utils/security.py`:
   ```python
   from datetime import datetime, timedelta, timezone
   from typing import Optional
   from jose import jwt, JWTError
   from passlib.context import CryptContext
   from core.config import config
   from core.exceptions.base import UnauthorizedException

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def hash_password(password: str) -> str:
       return pwd_context.hash(password)

   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)

   def create_access_token(user_id: str, role: str) -> str:
       expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
       payload = {
           "sub": user_id,
           "role": role,
           "exp": expire,
           "type": "access"
       }
       return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)

   def create_refresh_token(user_id: str) -> str:
       expire = datetime.now(timezone.utc) + timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
       payload = {
           "sub": user_id,
           "exp": expire,
           "type": "refresh"
       }
       return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)

   def decode_token(token: str) -> dict:
       try:
           payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
           return payload
       except JWTError as e:
           raise UnauthorizedException(message="Invalid or expired token")

   def create_tokens(user_id: str, role: str) -> tuple[str, str]:
       access_token = create_access_token(user_id, role)
       refresh_token = create_refresh_token(user_id)
       return access_token, refresh_token
   ```

2. Create `api/deps.py`:
   ```python
   from typing import Optional
   from fastapi import Depends, Header
   from fastapi.security import OAuth2PasswordBearer
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.db import get_db
   from core.exceptions.base import UnauthorizedException, ForbiddenException
   from app.models.user import User, Role
   from app.utils.security import decode_token

   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

   async def get_current_user(
       token: Optional[str] = Depends(oauth2_scheme),
       db_session: AsyncSession = Depends(get_db)
   ) -> User:
       if not token:
           raise UnauthorizedException(message="Not authenticated")

       payload = decode_token(token)

       if payload.get("type") != "access":
           raise UnauthorizedException(message="Invalid token type")

       user_id = payload.get("sub")
       user = await User.get_by_id(db_session, user_id)

       if not user:
           raise UnauthorizedException(message="User not found")

       if not user.is_active:
           raise UnauthorizedException(message="User is inactive")

       return user

   async def get_current_active_user(
       current_user: User = Depends(get_current_user)
   ) -> User:
       if not current_user.is_active:
           raise UnauthorizedException(message="User is inactive")
       return current_user

   async def get_current_admin(
       current_user: User = Depends(get_current_user)
   ) -> User:
       if current_user.role not in [Role.ADMIN, Role.OWNER]:
           raise ForbiddenException(message="Admin access required")
       return current_user

   async def get_current_owner(
       current_user: User = Depends(get_current_user)
   ) -> User:
       if current_user.role != Role.OWNER:
           raise ForbiddenException(message="Owner access required")
       return current_user
   ```

#### Dependencies
- Task 3 (User Model)
- Task 4 (Auth Schemas)

---

### Task 6: Authentication APIs
**Estimated Time**: 5-6 hours

#### User Story
As a user, I want to register and login so I can access the platform.

#### Acceptance Criteria
- [ ] POST `/api/v1/auth/register` - creates user, returns tokens
- [ ] POST `/api/v1/auth/login` - validates credentials, returns tokens
- [ ] POST `/api/v1/auth/refresh` - returns new access token
- [ ] Duplicate email returns 400
- [ ] Invalid credentials returns 401

#### Implementation Steps
1. Create `app/services/auth_service.py`:
   ```python
   from datetime import datetime, timezone
   from typing import Optional
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.exceptions.base import BadRequestException, UnauthorizedException
   from app.models.user import User, Role
   from app.schemas.user import UserCreate, TokenResponse
   from app.utils.security import (
       hash_password, verify_password, create_tokens, decode_token
   )

   class AuthService:
       def __init__(self, db_session: AsyncSession):
           self.db_session = db_session

       async def register(self, data: UserCreate) -> tuple[User, TokenResponse]:
           # Check if email exists
           existing_user = await User.get_by_email(self.db_session, data.email)
           if existing_user:
               raise BadRequestException(message="Email already registered")

           # Create user
           user = await User.create_user(
               db_session=self.db_session,
               email=data.email,
               first_name=data.first_name,
               last_name=data.last_name,
               hashed_password=hash_password(data.password)
           )

           # Generate tokens
           access_token, refresh_token = create_tokens(user.id, user.role.value)

           return user, TokenResponse(
               access_token=access_token,
               refresh_token=refresh_token
           )

       async def login(self, email: str, password: str) -> tuple[User, TokenResponse]:
           user = await User.get_by_email(self.db_session, email)

           if not user or not user.hashed_password:
               raise UnauthorizedException(message="Invalid email or password")

           if not verify_password(password, user.hashed_password):
               raise UnauthorizedException(message="Invalid email or password")

           if not user.is_active:
               raise UnauthorizedException(message="Account is deactivated")

           # Update last login
           user.last_login = datetime.now(timezone.utc)
           await self.db_session.commit()

           # Generate tokens
           access_token, refresh_token = create_tokens(user.id, user.role.value)

           return user, TokenResponse(
               access_token=access_token,
               refresh_token=refresh_token
           )

       async def refresh_token(self, refresh_token: str) -> TokenResponse:
           payload = decode_token(refresh_token)

           if payload.get("type") != "refresh":
               raise UnauthorizedException(message="Invalid token type")

           user_id = payload.get("sub")
           user = await User.get_by_id(self.db_session, user_id)

           if not user or not user.is_active:
               raise UnauthorizedException(message="User not found or inactive")

           access_token, new_refresh_token = create_tokens(user.id, user.role.value)

           return TokenResponse(
               access_token=access_token,
               refresh_token=new_refresh_token
           )
   ```

2. Create `api/v1/auth.py`:
   ```python
   from fastapi import APIRouter, Depends
   from fastapi.security import OAuth2PasswordRequestForm
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.db import get_db
   from app.schemas.user import UserCreate, UserResponse, TokenResponse
   from app.services.auth_service import AuthService

   router = APIRouter(prefix="/auth", tags=["Authentication"])

   @router.post("/register", response_model=dict)
   async def register(
       data: UserCreate,
       db_session: AsyncSession = Depends(get_db)
   ):
       service = AuthService(db_session)
       user, tokens = await service.register(data)
       return {
           "user": UserResponse.model_validate(user),
           "tokens": tokens
       }

   @router.post("/login", response_model=TokenResponse)
   async def login(
       form_data: OAuth2PasswordRequestForm = Depends(),
       db_session: AsyncSession = Depends(get_db)
   ):
       service = AuthService(db_session)
       user, tokens = await service.login(form_data.username, form_data.password)
       return tokens

   @router.post("/refresh", response_model=TokenResponse)
   async def refresh_token(
       refresh_token: str,
       db_session: AsyncSession = Depends(get_db)
   ):
       service = AuthService(db_session)
       return await service.refresh_token(refresh_token)
   ```

3. Create `api/v1/__init__.py` and `api/router.py`

4. Create main router

#### Dependencies
- Task 5 (JWT System)

---

### Task 7: Google OAuth Integration
**Estimated Time**: 4-5 hours

#### User Story
As a user, I want to login with Google for convenience.

#### Acceptance Criteria
- [ ] POST `/api/v1/auth/google` accepts Google ID token
- [ ] Creates new user on first login
- [ ] Links existing user by email
- [ ] Returns JWT tokens

#### Implementation Steps
1. Install Google auth:
   ```bash
   uv add google-auth
   ```

2. Create `app/services/google_auth_service.py`:
   ```python
   from google.oauth2 import id_token
   from google.auth.transport import requests
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.config import config
   from core.exceptions.base import UnauthorizedException
   from app.models.user import User
   from app.schemas.user import TokenResponse
   from app.utils.security import create_tokens

   class GoogleAuthService:
       def __init__(self, db_session: AsyncSession):
           self.db_session = db_session

       async def authenticate(self, token: str) -> tuple[User, TokenResponse]:
           try:
               idinfo = id_token.verify_oauth2_token(
                   token,
                   requests.Request(),
                   config.GOOGLE_CLIENT_ID
               )
           except ValueError:
               raise UnauthorizedException(message="Invalid Google token")

           google_id = idinfo["sub"]
           email = idinfo["email"]
           first_name = idinfo.get("given_name", "")
           last_name = idinfo.get("family_name", "")

           # Check if user exists by google_id
           user = await User.get_by_google_id(self.db_session, google_id)

           if not user:
               # Check by email
               user = await User.get_by_email(self.db_session, email)
               if user:
                   # Link Google account
                   user.google_id = google_id
                   await self.db_session.commit()
               else:
                   # Create new user
                   user = await User.create_user(
                       db_session=self.db_session,
                       email=email,
                       first_name=first_name,
                       last_name=last_name,
                       google_id=google_id
                   )
                   user.is_verified = True
                   await self.db_session.commit()

           access_token, refresh_token = create_tokens(user.id, user.role.value)

           return user, TokenResponse(
               access_token=access_token,
               refresh_token=refresh_token
           )
   ```

3. Add endpoint to `api/v1/auth.py`

#### Dependencies
- Task 6 (Auth APIs)

---

### Task 8: Main Application & Server
**Estimated Time**: 4-5 hours

#### User Story
As a developer, I want a FastAPI application with proper lifespan management following the established pattern.

#### Acceptance Criteria
- [ ] FastAPI app with lifespan context manager
- [ ] CORS middleware configured
- [ ] Exception handlers registered
- [ ] Health check endpoint
- [ ] All routers included

#### Implementation Steps
1. Create `main.py`:
   ```python
   import asyncio
   from contextlib import asynccontextmanager
   from fastapi import FastAPI, Request
   from fastapi.responses import JSONResponse
   from fastapi.middleware.cors import CORSMiddleware
   from core.config import config
   from core.exceptions.base import CustomException
   from core.db import engine
   from api.router import router as api_router

   shutdown_event = asyncio.Event()

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup
       print("🚀 Starting CSF Backend...")
       yield
       # Shutdown
       print("🛑 Shutting down CSF Backend...")
       await engine.dispose()
       print("✅ Database connections closed")

   def create_app() -> FastAPI:
       app = FastAPI(
           title="CSF Backend",
           description="CSF Youth Sports Registration Platform API",
           version="0.1.0",
           docs_url="/docs" if config.DEBUG else None,
           redoc_url="/redoc" if config.DEBUG else None,
           lifespan=lifespan,
       )

       # CORS
       app.add_middleware(
           CORSMiddleware,
           allow_origins=config.CORS_ALLOWED_ORIGINS,
           allow_credentials=True,
           allow_methods=["*"],
           allow_headers=["*"],
       )

       # Exception handlers
       @app.exception_handler(CustomException)
       async def custom_exception_handler(request: Request, exc: CustomException):
           return JSONResponse(
               status_code=exc.code,
               content={
                   "error_code": exc.error_code,
                   "message": exc.message,
                   "data": exc.data
               }
           )

       # Health check
       @app.get("/health")
       async def health_check():
           return {"status": "healthy", "version": "0.1.0"}

       # Include routers
       app.include_router(api_router, prefix="/api")

       return app

   app = create_app()
   ```

2. Create `api/router.py`:
   ```python
   from fastapi import APIRouter
   from api.v1.auth import router as auth_router

   router = APIRouter()
   router.include_router(auth_router, prefix="/v1")
   ```

#### Dependencies
- Task 6 (Auth APIs)

---

### Task 9: Program, Area, School Models
**Estimated Time**: 4-5 hours

#### User Story
As an admin, I need to organize classes by Program, Area, and School.

#### Acceptance Criteria
- [ ] Program model with class methods
- [ ] Area model with class methods
- [ ] School model with class methods
- [ ] Proper relationships
- [ ] Migrations run successfully

#### Implementation Steps
1. Create `app/models/program.py`:
   ```python
   from uuid import uuid4
   from typing import Optional, Sequence
   from sqlalchemy import String, Boolean, ForeignKey, Text, select
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy.orm import Mapped, mapped_column, relationship
   from core.db import Base, TimestampMixin

   class Program(Base, TimestampMixin):
       __tablename__ = 'programs'

       id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
       name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
       description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
       is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

       @classmethod
       async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Program"]:
           result = await db_session.execute(select(cls).where(cls.id == id))
           return result.scalars().first()

       @classmethod
       async def get_all_active(cls, db_session: AsyncSession) -> Sequence["Program"]:
           result = await db_session.execute(
               select(cls).where(cls.is_active == True).order_by(cls.name)
           )
           return result.scalars().all()

   class Area(Base, TimestampMixin):
       __tablename__ = 'areas'

       id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
       name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
       description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
       is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

       # Relationships
       schools: Mapped[list["School"]] = relationship("School", back_populates="area")

       @classmethod
       async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Area"]:
           result = await db_session.execute(select(cls).where(cls.id == id))
           return result.scalars().first()

       @classmethod
       async def get_all_active(cls, db_session: AsyncSession) -> Sequence["Area"]:
           result = await db_session.execute(
               select(cls).where(cls.is_active == True).order_by(cls.name)
           )
           return result.scalars().all()

   class School(Base, TimestampMixin):
       __tablename__ = 'schools'

       id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
       name: Mapped[str] = mapped_column(String(200), nullable=False)
       address: Mapped[str] = mapped_column(String(500), nullable=False)
       city: Mapped[str] = mapped_column(String(100), nullable=False)
       state: Mapped[str] = mapped_column(String(50), nullable=False)
       zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
       area_id: Mapped[str] = mapped_column(String(36), ForeignKey("areas.id"), nullable=False)
       is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

       # Relationships
       area: Mapped["Area"] = relationship("Area", back_populates="schools")

       @classmethod
       async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["School"]:
           result = await db_session.execute(select(cls).where(cls.id == id))
           return result.scalars().first()

       @classmethod
       async def get_by_area(cls, db_session: AsyncSession, area_id: str) -> Sequence["School"]:
           result = await db_session.execute(
               select(cls).where(cls.area_id == area_id, cls.is_active == True).order_by(cls.name)
           )
           return result.scalars().all()

       @classmethod
       async def get_all_active(cls, db_session: AsyncSession) -> Sequence["School"]:
           result = await db_session.execute(
               select(cls).where(cls.is_active == True).order_by(cls.name)
           )
           return result.scalars().all()
   ```

2. Create migration

#### Dependencies
- Task 2 (Database Connection)

---

### Task 10: Class Model
**Estimated Time**: 5-6 hours

#### User Story
As a system, I need a Class model to store class offerings with schedules and pricing.

#### Acceptance Criteria
- [ ] Class model with all fields
- [ ] Class methods for queries
- [ ] Support for weekday schedule (JSON array)
- [ ] Capacity tracking
- [ ] Relationships to Program, School

#### Implementation Steps
1. Create `app/models/class_.py`:
   ```python
   import enum
   from uuid import uuid4
   from decimal import Decimal
   from datetime import date, time
   from typing import Optional, Sequence, List
   from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, Numeric, Date, Time, JSON, Enum, select, and_
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy.orm import Mapped, mapped_column, relationship
   from core.db import Base, TimestampMixin

   class ClassType(str, enum.Enum):
       SHORT_TERM = "short_term"
       MEMBERSHIP = "membership"

   class Weekday(str, enum.Enum):
       MONDAY = "monday"
       TUESDAY = "tuesday"
       WEDNESDAY = "wednesday"
       THURSDAY = "thursday"
       FRIDAY = "friday"
       SATURDAY = "saturday"
       SUNDAY = "sunday"

   class Class(Base, TimestampMixin):
       __tablename__ = 'classes'

       id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
       name: Mapped[str] = mapped_column(String(200), nullable=False)
       description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
       program_id: Mapped[str] = mapped_column(String(36), ForeignKey("programs.id"), nullable=False)
       school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
       class_type: Mapped[ClassType] = mapped_column(Enum(ClassType), nullable=False)

       # Schedule
       weekdays: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ["monday", "wednesday"]
       start_time: Mapped[time] = mapped_column(Time, nullable=False)
       end_time: Mapped[time] = mapped_column(Time, nullable=False)
       start_date: Mapped[date] = mapped_column(Date, nullable=False)
       end_date: Mapped[date] = mapped_column(Date, nullable=False)

       # Capacity
       capacity: Mapped[int] = mapped_column(Integer, nullable=False)
       current_enrollment: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
       waitlist_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

       # Pricing
       price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
       membership_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
       installments_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

       # Age requirements
       min_age: Mapped[int] = mapped_column(Integer, nullable=False)
       max_age: Mapped[int] = mapped_column(Integer, nullable=False)

       is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

       # Relationships
       program: Mapped["Program"] = relationship("Program")
       school: Mapped["School"] = relationship("School")

       @property
       def has_capacity(self) -> bool:
           return self.current_enrollment < self.capacity

       @property
       def available_spots(self) -> int:
           return max(0, self.capacity - self.current_enrollment)

       @classmethod
       async def get_by_id(cls, db_session: AsyncSession, id: str) -> Optional["Class"]:
           result = await db_session.execute(select(cls).where(cls.id == id))
           return result.scalars().first()

       @classmethod
       async def get_filtered(
           cls,
           db_session: AsyncSession,
           program_id: Optional[str] = None,
           school_id: Optional[str] = None,
           has_capacity: Optional[bool] = None,
           min_age: Optional[int] = None,
           max_age: Optional[int] = None,
           skip: int = 0,
           limit: int = 20
       ) -> tuple[Sequence["Class"], int]:
           conditions = [cls.is_active == True]

           if program_id:
               conditions.append(cls.program_id == program_id)
           if school_id:
               conditions.append(cls.school_id == school_id)
           if has_capacity is True:
               conditions.append(cls.current_enrollment < cls.capacity)
           if min_age is not None:
               conditions.append(cls.max_age >= min_age)
           if max_age is not None:
               conditions.append(cls.min_age <= max_age)

           # Get total count
           count_result = await db_session.execute(
               select(func.count(cls.id)).where(and_(*conditions))
           )
           total = count_result.scalar() or 0

           # Get paginated results
           result = await db_session.execute(
               select(cls)
               .where(and_(*conditions))
               .order_by(cls.start_date, cls.start_time)
               .offset(skip)
               .limit(limit)
           )

           return result.scalars().all(), total

       @classmethod
       async def create_class(cls, db_session: AsyncSession, **kwargs) -> "Class":
           class_obj = cls(**kwargs)
           db_session.add(class_obj)
           await db_session.commit()
           await db_session.refresh(class_obj)
           return class_obj
   ```

2. Add `from sqlalchemy import func` import
3. Create migration

#### Dependencies
- Task 9 (Program, Area, School Models)

---

### Task 11: Class APIs
**Estimated Time**: 5-6 hours

#### User Story
As a parent, I want to browse classes. As an admin, I want to manage classes.

#### Acceptance Criteria
- [ ] GET `/api/v1/classes` - list with filters (public)
- [ ] GET `/api/v1/classes/{id}` - details (public)
- [ ] POST `/api/v1/classes` - create (admin)
- [ ] PUT `/api/v1/classes/{id}` - update (admin)
- [ ] DELETE `/api/v1/classes/{id}` - soft delete (admin)

#### Implementation Steps
1. Create `app/schemas/class_.py`
2. Create `app/services/class_service.py`
3. Create `api/v1/classes.py`:
   ```python
   from typing import Optional
   from fastapi import APIRouter, Depends, Query
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.db import get_db
   from api.deps import get_current_admin
   from app.models.user import User
   from app.models.class_ import Class
   from app.schemas.class_ import ClassCreate, ClassUpdate, ClassResponse, ClassListResponse

   router = APIRouter(prefix="/classes", tags=["Classes"])

   @router.get("/", response_model=ClassListResponse)
   async def list_classes(
       program_id: Optional[str] = None,
       school_id: Optional[str] = None,
       has_capacity: Optional[bool] = None,
       min_age: Optional[int] = None,
       max_age: Optional[int] = None,
       skip: int = Query(0, ge=0),
       limit: int = Query(20, ge=1, le=100),
       db_session: AsyncSession = Depends(get_db)
   ):
       classes, total = await Class.get_filtered(
           db_session,
           program_id=program_id,
           school_id=school_id,
           has_capacity=has_capacity,
           min_age=min_age,
           max_age=max_age,
           skip=skip,
           limit=limit
       )
       return ClassListResponse(
           items=[ClassResponse.model_validate(c) for c in classes],
           total=total,
           skip=skip,
           limit=limit
       )

   @router.get("/{class_id}", response_model=ClassResponse)
   async def get_class(
       class_id: str,
       db_session: AsyncSession = Depends(get_db)
   ):
       class_obj = await Class.get_by_id(db_session, class_id)
       if not class_obj:
           raise NotFoundException(message="Class not found")
       return ClassResponse.model_validate(class_obj)

   @router.post("/", response_model=ClassResponse)
   async def create_class(
       data: ClassCreate,
       db_session: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_admin)
   ):
       class_obj = await Class.create_class(db_session, **data.model_dump())
       return ClassResponse.model_validate(class_obj)

   @router.put("/{class_id}", response_model=ClassResponse)
   async def update_class(
       class_id: str,
       data: ClassUpdate,
       db_session: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_admin)
   ):
       class_obj = await Class.get_by_id(db_session, class_id)
       if not class_obj:
           raise NotFoundException(message="Class not found")

       for field, value in data.model_dump(exclude_unset=True).items():
           setattr(class_obj, field, value)

       await db_session.commit()
       await db_session.refresh(class_obj)
       return ClassResponse.model_validate(class_obj)

   @router.delete("/{class_id}")
   async def delete_class(
       class_id: str,
       db_session: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_admin)
   ):
       class_obj = await Class.get_by_id(db_session, class_id)
       if not class_obj:
           raise NotFoundException(message="Class not found")

       class_obj.is_active = False
       await db_session.commit()
       return {"message": "Class deleted successfully"}
   ```

4. Add router to `api/router.py`

#### Dependencies
- Task 10 (Class Model)
- Task 5 (JWT for admin auth)

---

### Task 12: User Profile APIs
**Estimated Time**: 2-3 hours

#### User Story
As a user, I want to view and update my profile.

#### Acceptance Criteria
- [ ] GET `/api/v1/users/me` - returns profile
- [ ] PUT `/api/v1/users/me` - updates profile
- [ ] Cannot change email or role

#### Implementation Steps
1. Create `api/v1/users.py`:
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from core.db import get_db
   from api.deps import get_current_user
   from app.models.user import User
   from app.schemas.user import UserResponse, UserUpdate

   router = APIRouter(prefix="/users", tags=["Users"])

   @router.get("/me", response_model=UserResponse)
   async def get_profile(
       current_user: User = Depends(get_current_user)
   ):
       return UserResponse.model_validate(current_user)

   @router.put("/me", response_model=UserResponse)
   async def update_profile(
       data: UserUpdate,
       current_user: User = Depends(get_current_user),
       db_session: AsyncSession = Depends(get_db)
   ):
       for field, value in data.model_dump(exclude_unset=True).items():
           setattr(current_user, field, value)

       await db_session.commit()
       await db_session.refresh(current_user)
       return UserResponse.model_validate(current_user)
   ```

2. Add router to `api/router.py`

#### Dependencies
- Task 6 (Auth APIs)

---

### Task 13: Unit Tests Setup & Auth Tests
**Estimated Time**: 5-6 hours

#### User Story
As a developer, I want comprehensive tests for authentication.

#### Acceptance Criteria
- [ ] Test fixtures configured
- [ ] Test database setup
- [ ] Auth registration tests
- [ ] Auth login tests
- [ ] Token refresh tests
- [ ] 80%+ coverage for auth

#### Implementation Steps
1. Install test dependencies:
   ```bash
   uv add --dev pytest pytest-asyncio pytest-cov httpx factory-boy
   ```

2. Create `tests/conftest.py`:
   ```python
   import asyncio
   import pytest
   from typing import AsyncGenerator
   from httpx import AsyncClient, ASGITransport
   from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
   from core.db import Base, get_db
   from main import app

   TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

   engine = create_async_engine(TEST_DATABASE_URL, echo=True)
   TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

   @pytest.fixture(scope="session")
   def event_loop():
       loop = asyncio.get_event_loop_policy().new_event_loop()
       yield loop
       loop.close()

   @pytest.fixture(autouse=True)
   async def setup_db():
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
       yield
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.drop_all)

   @pytest.fixture
   async def db_session() -> AsyncGenerator[AsyncSession, None]:
       async with TestSessionLocal() as session:
           yield session

   @pytest.fixture
   async def client() -> AsyncGenerator[AsyncClient, None]:
       async def override_get_db():
           async with TestSessionLocal() as session:
               yield session

       app.dependency_overrides[get_db] = override_get_db

       async with AsyncClient(
           transport=ASGITransport(app=app),
           base_url="http://test"
       ) as client:
           yield client

       app.dependency_overrides.clear()
   ```

3. Create `tests/test_auth.py`
4. Create `tests/test_classes.py`

#### Dependencies
- Task 8 (Main Application)
- Task 11 (Class APIs)

---

## Task Summary

| # | Task | Est. Hours | Dependencies |
|---|------|------------|--------------|
| 1 | Core Infrastructure Setup | 4-5h | None |
| 2 | Database Connection Setup | 5-6h | Task 1 |
| 3 | User Model | 4-5h | Task 2 |
| 4 | Authentication Schemas | 2-3h | Task 3 |
| 5 | JWT Token System | 4-5h | Task 3, 4 |
| 6 | Authentication APIs | 5-6h | Task 5 |
| 7 | Google OAuth Integration | 4-5h | Task 6 |
| 8 | Main Application & Server | 4-5h | Task 6 |
| 9 | Program, Area, School Models | 4-5h | Task 2 |
| 10 | Class Model | 5-6h | Task 9 |
| 11 | Class APIs | 5-6h | Task 5, 10 |
| 12 | User Profile APIs | 2-3h | Task 6 |
| 13 | Unit Tests | 5-6h | Task 8, 11 |
| **Total** | | **54-66h** | |

---

## Execution Order

```
Phase 1: Core (Tasks 1-2)
    └── Infrastructure & Database

Phase 2: Auth (Tasks 3-8)
    └── User → Schemas → JWT → APIs → OAuth → Server

Phase 3: Classes (Tasks 9-11)
    └── Program/Area/School → Class → APIs

Phase 4: Polish (Tasks 12-13)
    └── User Profile → Tests
```

---

## Success Criteria

- [ ] User can register/login with email
- [ ] User can login with Google
- [ ] JWT tokens work correctly
- [ ] Public can browse classes with filters
- [ ] Admin can CRUD classes
- [ ] All migrations run
- [ ] 75%+ test coverage
- [ ] All tests pass