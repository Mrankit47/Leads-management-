"""leadgen URL Configuration"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('leads.urls')),
    path('subscription/', include('subscriptions.urls')),
]

handler404 = 'leadgen.views.error_404'
handler500 = 'leadgen.views.error_500'
