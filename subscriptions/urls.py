from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', views.plan_list, name='plan_list'),
    path('subscribe/<int:plan_id>/', views.subscribe, name='subscribe'),
    path('renew/', views.renew_subscription, name='renew'),
    path('register-company/', views.register_company, name='register_company'),
]
