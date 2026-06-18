import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from .models import Movie, Hall, Seat, Session, Booking, Ticket

def index_view(request):
    movies = Movie.objects.all()
    # Featured movie for the hero banner (the one with the highest rating, or Dune if exists)
    featured_movie = Movie.objects.filter(title__icontains="Дюна").first() or movies.first()
    
    context = {
        'movies': movies,
        'featured_movie': featured_movie,
    }
    return render(request, 'bookings/index.html', context)

def movie_detail_view(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    # Fetch all upcoming sessions for this movie
    now = timezone.now()
    sessions = Session.objects.filter(movie=movie, start_time__gte=now).order_by('start_time')
    
    # Group sessions by date for cleaner display
    sessions_by_date = {}
    for s in sessions:
        # Format date as '17 июня, среда'
        # To avoid locale dependencies, we can do a simple formatted date
        date_str = s.start_time.strftime('%Y-%m-%d')
        if date_str not in sessions_by_date:
            sessions_by_date[date_str] = {
                'date': s.start_time,
                'sessions': []
            }
        sessions_by_date[date_str]['sessions'].append(s)

    context = {
        'movie': movie,
        'sessions_by_date': sessions_by_date.values(),
    }
    return render(request, 'bookings/movie_detail.html', context)

def booking_view(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    context = {
        'session': session,
    }
    return render(request, 'bookings/booking.html', context)

def ticket_confirmation_view(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    tickets = booking.tickets.all()
    context = {
        'booking': booking,
        'tickets': tickets,
    }
    return render(request, 'bookings/ticket.html', context)

# API Endpoints
def api_session_seats(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    
    # Get all seats for the hall
    seats = Seat.objects.filter(hall=session.hall).order_by('row', 'number')
    
    # Get already booked seats for this session
    booked_seat_ids = set(
        Ticket.objects.filter(session=session).values_list('seat_id', flat=True)
    )
    
    seats_list = []
    for seat in seats:
        seats_list.append({
            'id': seat.id,
            'row': seat.row,
            'number': seat.number,
            'category': seat.category,
            'category_display': seat.get_category_display(),
            'is_booked': seat.id in booked_seat_ids
        })
        
    session_data = {
        'movie_title': session.movie.title,
        'movie_duration': session.movie.duration,
        'hall_name': session.hall.name,
        'screen_type': session.hall.screen_type,
        'start_time': session.start_time.strftime('%d.%m.%Y %H:%M'),
        'base_price': float(session.base_price),
        'rows': session.hall.rows,
        'cols': session.hall.cols
    }
    
    return JsonResponse({
        'session': session_data,
        'seats': seats_list
    })

def api_create_booking(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
        
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        customer_name = data.get('name')
        customer_email = data.get('email')
        customer_phone = data.get('phone')
        seat_ids = data.get('seat_ids', [])
        
        if not all([session_id, customer_name, customer_email, customer_phone]) or not seat_ids:
            return JsonResponse({'error': 'Все поля формы обязательны для заполнения'}, status=400)
        session = get_object_or_404(Session, pk=session_id)
        from decimal import Decimal
        
        # Calculate seat pricing rules
        # - STANDARD: 1.0x base_price
        # - VIP: 1.5x base_price
        # - LOVESEAT: 2.0x base_price (covers two people)
        multiplier_map = {
            'STANDARD': Decimal('1.0'),
            'VIP': Decimal('1.5'),
            'LOVESEAT': Decimal('2.0')
        }
        
        # Enforce transaction to prevent double bookings
        with transaction.atomic():
            # Lock seats that we are trying to query/check
            # If any of these seats already has a ticket for this session, fail
            existing_tickets = Ticket.objects.filter(session=session, seat_id__in=seat_ids)
            if existing_tickets.exists():
                booked_numbers = [f"Ряд {t.seat.row} Место {t.seat.number}" for t in existing_tickets]
                return JsonResponse({
                    'error': f'Одно или несколько выбранных мест уже забронированы: {", ".join(booked_numbers)}. Выберите другие места.'
                }, status=400)
                
            # Fetch all selected seat objects to calculate total price
            seats = Seat.objects.filter(hall=session.hall, id__in=seat_ids)
            if len(seats) != len(seat_ids):
                return JsonResponse({'error': 'Некоторые выбранные места не найдены в зале.'}, status=400)
                
            total_price = 0
            ticket_items = []
            
            for seat in seats:
                price = session.base_price * multiplier_map.get(seat.category, Decimal('1.0'))
                total_price += price
                ticket_items.append((seat, price))
                
            # Create booking
            booking = Booking.objects.create(
                session=session,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                total_price=total_price,
                status='CONFIRMED' # Confirmed directly since booking acts as checkout success
            )
            
            # Create tickets
            for seat, price in ticket_items:
                Ticket.objects.create(
                    booking=booking,
                    session=session,
                    seat=seat,
                    price=price
                )
                
        return JsonResponse({
            'success': True,
            'booking_id': booking.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Произошла системная ошибка: {str(e)}'}, status=500)


from django.db.models import Q

def history_view(request):
    query = request.GET.get('query', '').strip()
    bookings = []
    searched = False
    
    if query:
        searched = True
        bookings = Booking.objects.filter(
            Q(customer_email__iexact=query) | Q(customer_phone=query)
        ).order_by('-created_at').prefetch_related('tickets__seat', 'session__movie', 'session__hall')
        
    context = {
        'query': query,
        'bookings': bookings,
        'searched': searched,
    }
    return render(request, 'bookings/history.html', context)
