from rest_framework.routers import SimpleRouter

from .views import VerificationRunViewSet

router = SimpleRouter()
router.register('verifications', VerificationRunViewSet, basename='verification')

urlpatterns = router.urls
