from django.urls import path, include
from .views import (
                    HomeView,
                    ItemDetailView,
                    add_to_cart,
                    remove_from_cart,
                    ShopView,
                    OrderSummaryView,
                    remove_single_item_from_cart,
                    CheckoutView,
                    PaymentView,
                    AddCouponView,
                    RequestRefundView
                    )
app_name='core'

urlpatterns = [
    # path('',item_list,name='item-list'),
    path('',HomeView.as_view(),name='home'),
    path('product/<slug>/',ItemDetailView.as_view(),name='product'),
    path('checkout/',CheckoutView.as_view(),name='checkout'),
    path('order-summary/',OrderSummaryView.as_view(),name='order-summary'),
    path('add-to-cart/<slug>/',add_to_cart,name='add-to-cart'),
    path('add-coupon/',AddCouponView.as_view(),name='add-coupon'),
    path('remove-from-cart/<slug>/',remove_from_cart,name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/',remove_single_item_from_cart,name='remove-single-item-from-cart'),
    path('shop',ShopView.as_view(),name='shop'),
    path('payment/<payment_option>/',PaymentView.as_view(),name='payment'),
    path('request-refund/',RequestRefundView.as_view(),name='request-refund')
]
