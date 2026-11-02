from rest_framework.routers import SimpleRouter

from .views import HypothesisViewSet

router = SimpleRouter()
router.register('hypotheses', HypothesisViewSet, basename='hypothesis')

urlpatterns = router.urls
