from django.urls import path
from .views import (
    ItemDetailView,
    CheckoutView,
    HomeView,
    OrderSummaryView,
    category,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView,
    SellerHome,
    sales,
    Notification,
    ItemEditView,
    editproduct,
    product_update,
    product_delete,
    BestSelling,
    PurchaseHistory,
    NotificationReceipt
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('category/<hierarchy>/', category, name='category'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('seller/home/', SellerHome.as_view(), name='sellerhome'),
    path('seller/edit/', editproduct, name='editproduct'),
    path('seller/report/', sales, name='sales'),
    path('seller/notification/', Notification.as_view(), name='notification'),
    path('seller/notificationreceipt/<id>', NotificationReceipt.as_view(), name='notificationreceipt'),
    path('editsingleproduct/<slug>/', ItemEditView.as_view(), name='editsingleproduct'),
    path('editsingleproduct/<slug>/edit/<int:pk>', product_update, name='product_update'),
    path('editsingleproduct/<slug>/delete/<int:pk>', product_delete, name='product_delete'),
    path('bestseller/', BestSelling.as_view(), name='bestselling'),
    path('purchasehistory/', PurchaseHistory.as_view(), name='purchasehistory')
]
