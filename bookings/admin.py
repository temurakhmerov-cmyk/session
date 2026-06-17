from django.contrib import admin
from .models import Movie, Hall, Seat, Session, Booking, Ticket

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'duration', 'rating', 'release_date')
    search_fields = ('title', 'genre', 'director')
    list_filter = ('genre', 'release_date')
    ordering = ('-release_date',)

@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'screen_type', 'rows', 'cols', 'get_seat_count')
    
    def get_seat_count(self, obj):
        return obj.seats.count()
    get_seat_count.short_description = "Количество мест"

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('hall', 'row', 'number', 'category')
    list_filter = ('hall', 'category', 'row')
    search_fields = ('hall__name',)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'base_price')
    list_filter = ('hall', 'movie', 'start_time')
    ordering = ('start_time',)

class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ('session', 'seat', 'price')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_phone', 'customer_email', 'session', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'session__movie', 'created_at')
    search_fields = ('customer_name', 'customer_email', 'customer_phone')
    inlines = [TicketInline]
    ordering = ('-created_at',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'session', 'seat', 'price')
    list_filter = ('session__movie', 'session__hall')
