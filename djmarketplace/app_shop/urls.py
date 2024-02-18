from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .views import register_view, CustomLoginView, CustomLogoutView, MainView, UserUpdateView, CartView, add_good_to_cart, RefillBalanceView,\
    pay
from .views import delete_cart



urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),
    path('', MainView.as_view(), name='main'),
    path('profile/<int:pk>/', UserUpdateView.as_view(), name='profile'),
    path('cart/', CartView.as_view(), name='cart'),
    path('add_good/<int:pk>/', add_good_to_cart, name='add_good'),
    path('refill/', RefillBalanceView.as_view(), name='refill'),
    path('cart/pay/<int:pk>/', pay, name='pay'),
    path('delete-from-cart/<int:item_id>/', delete_cart, name='delete_cart'),
    path('cart/pay/<int:pk>/', pay, name='pay'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

