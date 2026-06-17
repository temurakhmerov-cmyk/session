import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Movie, Hall, Session, Seat, Booking, Ticket

class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми фильмами, залами и сеансами'

    def handle(self, *args, **options):
        self.stdout.write('Начало заполнения БД...')
        
        # Очистка старых данных
        Ticket.objects.all().delete()
        Booking.objects.all().delete()
        Session.objects.all().delete()
        Seat.objects.all().delete()
        Hall.objects.all().delete()
        Movie.objects.all().delete()

        # 1. Создаем фильмы
        movies_data = [
            {
                'title': 'Дюна: Часть вторая',
                'description': 'Пол Атрейдес объединяется с Чани и фрименами, чтобы отомстить заговорщикам, уничтожившим его семью. Между любовью всей своей жизни и судьбой известной вселенной он пытается предотвратить ужасное будущее, которое может предвидеть только он.',
                'duration': 166,
                'poster': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80',
                'banner': 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1600&q=80',
                'genre': 'Фантастика, Приключения',
                'rating': 8.5,
                'director': 'Дени Вильнёв',
                'release_date': timezone.datetime(2024, 2, 28).date()
            },
            {
                'title': 'Интерстеллар',
                'description': 'Наше время на Земле подошло к концу. Команда исследователей отправляется в самую важную миссию в истории человечества: путешествие за пределы нашей галактики, чтобы узнать, есть ли у человечества будущее среди звезд.',
                'duration': 169,
                'poster': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80',
                'banner': 'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1600&q=80',
                'genre': 'Фантастика, Драма',
                'rating': 8.6,
                'director': 'Кристофер Нолан',
                'release_date': timezone.datetime(2014, 11, 6).date()
            },
            {
                'title': 'Оппенгеймер',
                'description': 'История жизни американского физика Роберта Оппенгеймера, который стоял во главе первых разработок ядерного оружия во время Второй мировой войны.',
                'duration': 180,
                'poster': 'https://images.unsplash.com/photo-1440404653325-ab127d49abc1?auto=format&fit=crop&w=600&q=80',
                'banner': 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=1600&q=80',
                'genre': 'Биография, Драма, История',
                'rating': 8.4,
                'director': 'Кристофер Нолан',
                'release_date': timezone.datetime(2023, 7, 21).date()
            }
        ]

        movies = []
        for m_data in movies_data:
            movie = Movie.objects.create(**m_data)
            movies.append(movie)
            self.stdout.write(f'Создан фильм: {movie.title}')

        # 2. Создаем залы (места будут сгенерированы автоматически при вызове save())
        hall1 = Hall.objects.create(name='Зал IMAX', screen_type='IMAX', rows=8, cols=12)
        hall2 = Hall.objects.create(name='Синий зал', screen_type='3D', rows=6, cols=10)
        
        self.stdout.write(f'Создан зал: {hall1.name} (мест: {hall1.seats.count()})')
        self.stdout.write(f'Создан зал: {hall2.name} (мест: {hall2.seats.count()})')

        # 3. Создаем сеансы на ближайшие 3 дня
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        # Вспомогательная функция для генерации времени сеанса
        def get_time(days_offset, hour):
            # Задаем дату с сегодняшним днем + оффсет и конкретный час
            future_date = now + timezone.timedelta(days=days_offset)
            return future_date.replace(hour=hour)

        sessions_data = [
            # Сегодня
            {'movie': movies[0], 'hall': hall1, 'start_time': get_time(0, 12), 'base_price': 450.00},
            {'movie': movies[0], 'hall': hall1, 'start_time': get_time(0, 18), 'base_price': 550.00},
            {'movie': movies[1], 'hall': hall2, 'start_time': get_time(0, 15), 'base_price': 350.00},
            {'movie': movies[2], 'hall': hall2, 'start_time': get_time(0, 20), 'base_price': 400.00},
            
            # Завтра
            {'movie': movies[0], 'hall': hall1, 'start_time': get_time(1, 14), 'base_price': 450.00},
            {'movie': movies[1], 'hall': hall1, 'start_time': get_time(1, 19), 'base_price': 600.00},
            {'movie': movies[2], 'hall': hall2, 'start_time': get_time(1, 12), 'base_price': 350.00},
            {'movie': movies[0], 'hall': hall2, 'start_time': get_time(1, 17), 'base_price': 400.00},

            # Послезавтра
            {'movie': movies[2], 'hall': hall1, 'start_time': get_time(2, 13), 'base_price': 500.00},
            {'movie': movies[0], 'hall': hall1, 'start_time': get_time(2, 18), 'base_price': 550.00},
            {'movie': movies[1], 'hall': hall2, 'start_time': get_time(2, 16), 'base_price': 350.00},
        ]

        for s_data in sessions_data:
            session = Session.objects.create(**s_data)
            self.stdout.write(f'Создан сеанс: {session}')

        # 4. Создаем пару тестовых бронирований, чтобы были занятые места
        # Для первого сеанса Дюны (сегодня в 12:00) в Зале IMAX забронируем пару мест
        session1 = Session.objects.filter(movie=movies[0], hall=hall1).first()
        if session1:
            booking = Booking.objects.create(
                session=session1,
                customer_name='Иван Петров',
                customer_email='ivan@example.com',
                customer_phone='+79998887766',
                total_price=900.00,
                status='CONFIRMED'
            )
            
            # Забронируем ряд 4, места 5 и 6 (это стандартные места)
            seat1 = Seat.objects.get(hall=hall1, row=4, number=5)
            seat2 = Seat.objects.get(hall=hall1, row=4, number=6)
            
            Ticket.objects.create(booking=booking, session=session1, seat=seat1, price=450.00)
            Ticket.objects.create(booking=booking, session=session1, seat=seat2, price=450.00)
            self.stdout.write(f'Создано тестовое бронирование для {booking.customer_name} на места Ряд 4 Место 5, 6')

        self.stdout.write('Заполнение БД завершено успешно!')
