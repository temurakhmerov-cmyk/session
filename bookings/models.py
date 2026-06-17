from django.db import models
from django.core.exceptions import ValidationError

class Movie(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    duration = models.IntegerField(verbose_name="Длительность (мин)")
    poster = models.CharField(max_length=500, verbose_name="Ссылка на постер")
    banner = models.CharField(max_length=500, verbose_name="Ссылка на баннер", blank=True, null=True)
    genre = models.CharField(max_length=100, verbose_name="Жанр")
    rating = models.DecimalField(max_digits=3, decimal_places=1, verbose_name="Рейтинг Кинопоиск/IMDb")
    director = models.CharField(max_length=255, verbose_name="Режиссер", blank=True, null=True)
    release_date = models.DateField(verbose_name="Дата премьеры")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"


class Hall(models.Model):
    SCREEN_TYPES = (
        ('2D', 'Standard 2D'),
        ('3D', 'Standard 3D'),
        ('IMAX', 'IMAX 3D'),
    )
    name = models.CharField(max_length=100, verbose_name="Название зала")
    screen_type = models.CharField(max_length=10, choices=SCREEN_TYPES, default='2D', verbose_name="Тип экрана")
    rows = models.IntegerField(verbose_name="Количество рядов")
    cols = models.IntegerField(verbose_name="Количество мест в ряду")

    def __str__(self):
        return f"{self.name} ({self.screen_type})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_seats()

    def generate_seats(self):
        seats_to_create = []
        for r in range(1, self.rows + 1):
            if r == self.rows:
                # Loveseats span 2 columns, so we generate cols // 2 seats
                loveseats_count = self.cols // 2
                for c in range(1, loveseats_count + 1):
                    seats_to_create.append(Seat(hall=self, row=r, number=c, category='LOVESEAT'))
            else:
                for c in range(1, self.cols + 1):
                    # Second and third to last rows: VIP (if total rows > 3)
                    if self.rows > 3 and r in [self.rows - 1, self.rows - 2]:
                        cat = 'VIP'
                    else:
                        cat = 'STANDARD'
                    seats_to_create.append(Seat(hall=self, row=r, number=c, category=cat))
        Seat.objects.bulk_create(seats_to_create)

    class Meta:
        verbose_name = "Кинозал"
        verbose_name_plural = "Кинозалы"


class Seat(models.Model):
    CATEGORIES = (
        ('STANDARD', 'Стандартное'),
        ('VIP', 'VIP (Комфорт)'),
        ('LOVESEAT', 'Love Seat (Двойное)'),
    )
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats', verbose_name="Кинозал")
    row = models.IntegerField(verbose_name="Ряд")
    number = models.IntegerField(verbose_name="Место")
    category = models.CharField(max_length=20, choices=CATEGORIES, default='STANDARD', verbose_name="Категория")

    def __str__(self):
        return f"Ряд {self.row}, Место {self.number} ({self.get_category_display()})"

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"
        constraints = [
            models.UniqueConstraint(fields=['hall', 'row', 'number'], name='unique_hall_seat')
        ]


class Session(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='sessions', verbose_name="Фильм")
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='sessions', verbose_name="Кинозал")
    start_time = models.DateTimeField(verbose_name="Время начала")
    base_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Базовая цена")

    def __str__(self):
        formatted_time = self.start_time.strftime('%d.%m %H:%M')
        return f"{self.movie.title} - {self.hall.name} ({formatted_time})"

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ['start_time']


class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Ожидает оплаты'),
        ('CONFIRMED', 'Подтверждено'),
        ('CANCELLED', 'Отменено'),
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings', verbose_name="Сеанс")
    customer_name = models.CharField(max_length=100, verbose_name="Имя клиента")
    customer_email = models.EmailField(verbose_name="Email")
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Итоговая цена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Статус")

    def __str__(self):
        return f"Бронь #{self.id} - {self.customer_name} ({self.session.movie.title})"

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"


class Ticket(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='tickets', verbose_name="Бронирование")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='tickets', verbose_name="Сеанс")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='tickets', verbose_name="Место")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Цена билета")

    def __str__(self):
        return f"Билет #{self.id} (Ряд {self.seat.row}, Место {self.seat.number}) на {self.session}"

    def clean(self):
        # Enforce that seat belongs to the session's hall
        if self.seat.hall != self.session.hall:
            raise ValidationError("Выбранное место не принадлежит кинозалу этого сеанса.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        constraints = [
            models.UniqueConstraint(fields=['session', 'seat'], name='unique_session_seat')
        ]
