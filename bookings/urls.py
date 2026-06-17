from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('movie/<int:movie_id>/', views.movie_detail_view, name='movie_detail'),
    path('booking/<int:session_id>/', views.booking_view, name='booking'),
    path('ticket/<int:booking_id>/', views.ticket_confirmation_view, name='ticket_confirmation'),
    
    # API endpoints
    path('api/session/<int:session_id>/seats/', views.api_session_seats, name='api_session_seats'),
    path('api/booking/create/', views.api_create_booking, name='api_create_booking'),
]
