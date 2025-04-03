import pytest
from django.core.cache import cache

# إعداد Django قبل الاختبارات
@pytest.fixture(autouse=True)
def setup_django(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        yield

# إفراغ الكاش قبل كل اختبار
@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()

# إعداد جلسة aiohttp للاختبارات الغير متزامنة
@pytest.fixture
async def aiohttp_session():
    from aiohttp import ClientSession
    async with ClientSession() as session:
        yield session