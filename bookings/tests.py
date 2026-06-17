import json
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from .models import Movie, Hall, Seat, Session, Booking, Ticket

class CinemaBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Create Movie
        self.movie = Movie.objects.create(
            title="Тестовый фильм",
            description="Описание тестового фильма",
            duration=120,
            poster="http://example.com/poster.jpg",
            genre="Драма",
            rating=8.0,
            release_date=timezone.now().date()
        )
        
        # 2. Create Hall (this triggers auto seat generation: 5 rows * 6 cols = 30 seats)
        self.hall = Hall.objects.create(
            name="Тестовый зал",
            screen_type="2D",
            rows=5,
            cols=6
        )
        
        # 3. Create Session
        self.session = Session.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timezone.timedelta(hours=2),
            base_price=300.00
        )

    def test_seat_generation(self):
        """
        Check that creating a Hall auto-generates seats with correct categories.
        """
        seats = Seat.objects.filter(hall=self.hall)
        self.assertEqual(seats.count(), 27)  # 4 rows of 6 seats + 1 row of 3 Loveseats = 27
        
        # Last row (row 5) seats should be LOVESEATs (cols // 2 = 6 // 2 = 3)
        loveseats = seats.filter(row=5)
        self.assertEqual(loveseats.count(), 3)
        for seat in loveseats:
            self.assertEqual(seat.category, 'LOVESEAT')
            
        # Rows 4 and 3 should be VIP seats (since rows = 5 > 3)
        vip_seats = seats.filter(row__in=[3, 4])
        self.assertEqual(vip_seats.count(), 12)
        for seat in vip_seats:
            self.assertEqual(seat.category, 'VIP')
            
        # Rows 1 and 2 should be STANDARD seats
        standard_seats = seats.filter(row__in=[1, 2])
        self.assertEqual(standard_seats.count(), 12)
        for seat in standard_seats:
            self.assertEqual(seat.category, 'STANDARD')

    def test_get_session_seats_api(self):
        """
        Check retrieving seat map state for a session.
        """
        url = reverse('bookings:api_session_seats', args=[self.session.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('session', data)
        self.assertIn('seats', data)
        self.assertEqual(len(data['seats']), 27)
        
        # Verify specific seat structure
        first_seat = data['seats'][0]
        self.assertIn('id', first_seat)
        self.assertIn('row', first_seat)
        self.assertIn('number', first_seat)
        self.assertIn('category', first_seat)
        self.assertIn('is_booked', first_seat)
        self.assertFalse(first_seat['is_booked'])

    def test_successful_booking_via_api(self):
        """
        Check successfully booking standard seats via API.
        """
        seat1 = Seat.objects.get(hall=self.hall, row=2, number=3)
        seat2 = Seat.objects.get(hall=self.hall, row=2, number=4)
        
        payload = {
            'session_id': self.session.id,
            'name': 'Алексей Иванов',
            'phone': '+79997776655',
            'email': 'alex@example.com',
            'seat_ids': [seat1.id, seat2.id]
        }
        
        url = reverse('bookings:api_create_booking')
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('booking_id', data)
        
        # Check database records
        booking_id = data['booking_id']
        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.customer_name, 'Алексей Иванов')
        self.assertEqual(booking.tickets.count(), 2)
        
        # Standard seat base price is 300, total for 2 should be 600
        self.assertEqual(float(booking.total_price), 600.00)

    def test_double_booking_prevention(self):
        """
        Check that trying to book already booked seats returns an error and prevents duplicates.
        """
        seat = Seat.objects.get(hall=self.hall, row=3, number=3)  # VIP seat
        
        # First booking
        payload1 = {
            'session_id': self.session.id,
            'name': 'Клиент 1',
            'phone': '+79001112233',
            'email': 'client1@example.com',
            'seat_ids': [seat.id]
        }
        
        url = reverse('bookings:api_create_booking')
        response1 = self.client.post(
            url,
            data=json.dumps(payload1),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        
        # Second booking trying to book the exact same seat
        payload2 = {
            'session_id': self.session.id,
            'name': 'Клиент 2',
            'phone': '+79004445566',
            'email': 'client2@example.com',
            'seat_ids': [seat.id]
        }
        
        response2 = self.client.post(
            url,
            data=json.dumps(payload2),
            content_type='application/json'
        )
        
        # Assert it fails with 400 Bad Request and error details
        self.assertEqual(response2.status_code, 400)
        data2 = response2.json()
        self.assertIn('error', data2)
        self.assertTrue('уже забронированы' in data2['error'])
        
        # Verify tickets count is still 1
        tickets = Ticket.objects.filter(session=self.session, seat=seat)
        self.assertEqual(tickets.count(), 1)
        self.assertEqual(tickets.first().booking.customer_name, 'Клиент 1')
