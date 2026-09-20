from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, MenuItemViewSet, DealViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("menu-items", MenuItemViewSet, basename="menu-item")
router.register("deals", DealViewSet, basename="deal")

urlpatterns = router.urls
