from fastapi import APIRouter

from api.v1.admin import router as admin_router
from api.v1.announcements import router as announcements_router
from api.v1.areas import router as areas_router
from api.v1.attendance import router as attendance_router
from api.v1.auth import router as auth_router
from api.v1.badges import router as badges_router
from api.v1.checkin import router as checkin_router
from api.v1.children import router as children_router
from api.v1.classes import router as classes_router
from api.v1.discounts import router as discounts_router
from api.v1.enrollments import router as enrollments_router
from api.v1.events import router as events_router
from api.v1.installments import router as installments_router
from api.v1.orders import router as orders_router
from api.v1.payments import router as payments_router
from api.v1.photos import router as photos_router
from api.v1.programs import router as programs_router
from api.v1.users import router as users_router
from api.v1.waivers import router as waivers_router
from api.v1.webhooks import router as webhooks_router

router = APIRouter()

# Include v1 routers
router.include_router(auth_router, prefix="/v1")
router.include_router(programs_router, prefix="/v1")
router.include_router(areas_router, prefix="/v1")
router.include_router(classes_router, prefix="/v1")
router.include_router(users_router, prefix="/v1")
router.include_router(children_router, prefix="/v1")
router.include_router(waivers_router, prefix="/v1")
router.include_router(payments_router, prefix="/v1")
router.include_router(orders_router, prefix="/v1")
router.include_router(enrollments_router, prefix="/v1")
router.include_router(installments_router, prefix="/v1")
router.include_router(discounts_router, prefix="/v1")
router.include_router(webhooks_router, prefix="/v1")

# Engagement platform features
router.include_router(announcements_router, prefix="/v1")
router.include_router(attendance_router, prefix="/v1")
router.include_router(events_router, prefix="/v1")
router.include_router(photos_router, prefix="/v1")
router.include_router(badges_router, prefix="/v1")
router.include_router(checkin_router, prefix="/v1")

# Admin features
router.include_router(admin_router, prefix="/v1")
