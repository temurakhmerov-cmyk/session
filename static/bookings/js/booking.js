// State variables
let sessionInfo = null;
let seatsData = [];
let selectedSeats = [];

// DOM Elements - Main Page
const sessionId = document.getElementById('sessionId').value;
const seatsGrid = document.getElementById('seatsGrid');
const selectedSeatsCart = document.getElementById('selectedSeatsCart');
const totalPriceVal = document.getElementById('totalPriceVal');
const checkoutBtn = document.getElementById('checkoutBtn');
const errorBanner = document.getElementById('errorBanner');
const errorMessage = document.getElementById('errorMessage');

// DOM Elements - Payment Modal
const paymentModalOverlay = document.getElementById('paymentModalOverlay');
const creditCardGraphic = document.getElementById('creditCardGraphic');
const cardNumberInput = document.getElementById('cardNumber');
const cardExpiryInput = document.getElementById('cardExpiry');
const cardCvvInput = document.getElementById('cardCvv');
const cardHolderInput = document.getElementById('cardHolder');

const cardNumberDisplay = document.getElementById('cardNumberDisplay');
const cardHolderDisplay = document.getElementById('cardHolderDisplay');
const cardExpiryDisplay = document.getElementById('cardExpiryDisplay');
const cardCvvDisplay = document.getElementById('cardCvvDisplay');
const payTotalAmount = document.getElementById('payTotalAmount');
const paymentLoader = document.getElementById('paymentLoader');
const paySubmitBtn = document.getElementById('paySubmitBtn');

// Seat price multipliers
const multipliers = {
    'STANDARD': 1.0,
    'VIP': 1.5,
    'LOVESEAT': 2.0
};

// Category text in Russian
const categoryLabels = {
    'STANDARD': 'Стандарт',
    'VIP': 'VIP',
    'LOVESEAT': 'Love Seat (двойное)'
};

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    fetchSessionSeats();
    setupCardFormListeners();
});

// Fetch seating grid from backend API
async function fetchSessionSeats() {
    try {
        const response = await fetch(`/api/session/${sessionId}/seats/`);
        if (!response.ok) {
            throw new Error('Не удалось загрузить схему зала.');
        }
        
        const data = await response.json();
        sessionInfo = data.session;
        seatsData = data.seats;
        
        renderSeatGrid();
    } catch (err) {
        showError(err.message);
    }
}

// Render the visual cinema hall seat grid
function renderSeatGrid() {
    seatsGrid.innerHTML = '';
    
    // Group seats by row
    const rowsMap = {};
    seatsData.forEach(seat => {
        if (!rowsMap[seat.row]) {
            rowsMap[seat.row] = [];
        }
        rowsMap[seat.row].push(seat);
    });
    
    // Render row by row
    Object.keys(rowsMap).sort((a, b) => a - b).forEach(rowNum => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'seats-row';
        
        // Left row label
        const leftLabel = document.createElement('div');
        leftLabel.className = 'row-label';
        leftLabel.innerText = rowNum;
        rowDiv.appendChild(leftLabel);
        
        // Seats in this row
        const rowSeats = rowsMap[rowNum].sort((a, b) => a.number - b.number);
        rowSeats.forEach(seat => {
            const seatDiv = document.createElement('div');
            
            // Base seat classes
            seatDiv.className = `seat ${seat.category}`;
            seatDiv.innerText = seat.number;
            seatDiv.title = `Ряд ${seat.row}, Место ${seat.number} (${categoryLabels[seat.category]} - ${calculateSeatPrice(seat.category)} ₽)`;
            
            if (seat.is_booked) {
                seatDiv.classList.add('booked');
                seatDiv.title += ' (Занято)';
            } else {
                // Click handler for available seats
                seatDiv.addEventListener('click', () => toggleSeatSelection(seat, seatDiv));
            }
            
            rowDiv.appendChild(seatDiv);
        });
        
        // Right row label
        const rightLabel = document.createElement('div');
        rightLabel.className = 'row-label';
        rightLabel.innerText = rowNum;
        rowDiv.appendChild(rightLabel);
        
        seatsGrid.appendChild(rowDiv);
    });
}

// Toggle selection state of a seat
function toggleSeatSelection(seat, element) {
    const index = selectedSeats.findIndex(s => s.id === seat.id);
    
    if (index > -1) {
        // Remove from selection
        selectedSeats.splice(index, 1);
        element.classList.remove('selected');
    } else {
        // Add to selection
        selectedSeats.push(seat);
        element.classList.add('selected');
    }
    
    updateCart();
}

// Compute seat price based on base price and modifier multiplier
function calculateSeatPrice(category) {
    if (!sessionInfo) return 0;
    return Math.round(sessionInfo.base_price * (multipliers[category] || 1.0));
}

// Get total price of currently selected seats
function getCartTotal() {
    let total = 0;
    selectedSeats.forEach(seat => {
        total += calculateSeatPrice(seat.category);
    });
    return total;
}

// Update the Cart sidebar and total price
function updateCart() {
    if (selectedSeats.length === 0) {
        selectedSeatsCart.innerHTML = `<p class="empty-cart-message">Места не выбраны. Кликните по схеме зала для выбора мест.</p>`;
        totalPriceVal.innerText = '0 ₽';
        checkoutBtn.disabled = true;
        return;
    }
    
    selectedSeatsCart.innerHTML = '';
    
    selectedSeats.forEach(seat => {
        const price = calculateSeatPrice(seat.category);
        
        const item = document.createElement('div');
        item.className = 'cart-item';
        item.innerHTML = `
            <div class="cart-item-label">
                <i class="fa-solid fa-chair" style="color: var(--color-${getCategoryColorClass(seat.category)});"></i> 
                Ряд ${seat.row}, Место ${seat.number} <span style="font-size: 11px; color: var(--color-muted);">(${categoryLabels[seat.category]})</span>
            </div>
            <div class="cart-item-price">${price} ₽</div>
        `;
        selectedSeatsCart.appendChild(item);
    });
    
    const total = getCartTotal();
    totalPriceVal.innerText = `${total} ₽`;
    checkoutBtn.disabled = false;
}

function getCategoryColorClass(category) {
    if (category === 'STANDARD') return 'std';
    if (category === 'VIP') return 'vip';
    if (category === 'LOVESEAT') return 'love';
    return 'std';
}

/* Payment Modal Logic */

function openPaymentModal() {
    const total = getCartTotal();
    payTotalAmount.innerText = `${total} ₽`;
    paymentModalOverlay.classList.add('active');
}

function closePaymentModal() {
    paymentModalOverlay.classList.remove('active');
    // Reset form and graphics
    document.getElementById('paymentForm').reset();
    cardNumberDisplay.innerText = '•••• •••• •••• ••••';
    cardExpiryDisplay.innerText = 'MM/YY';
    cardCvvDisplay.innerText = '•••';
    cardHolderDisplay.innerText = 'CARDHOLDER NAME';
    creditCardGraphic.classList.remove('flipped');
}

// Triggered when user clicks 'Забронировать билеты' form
function submitBooking(event) {
    event.preventDefault();
    hideError();
    
    if (selectedSeats.length === 0) {
        showError('Выберите хотя бы одно место для продолжения.');
        return;
    }
    
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const email = document.getElementById('customerEmail').value.trim();
    
    if (!name || !phone || !email) {
        showError('Заполните все контактные поля.');
        return;
    }
    
    // Form is valid - open the Payment Acquiring screen
    openPaymentModal();
}

// Setup real-time credit card sync visual listeners
function setupCardFormListeners() {
    // 1. Format and display card number
    cardNumberInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
        let formatted = '';
        for (let i = 0; i < value.length; i++) {
            if (i > 0 && i % 4 === 0) {
                formatted += ' ';
            }
            formatted += value[i];
        }
        e.target.value = formatted;
        cardNumberDisplay.innerText = formatted || '•••• •••• •••• ••••';
    });

    // 2. Format and display expiry date
    cardExpiryInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
        if (value.length > 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value;
        cardExpiryDisplay.innerText = value || 'MM/YY';
    });

    // 3. Focus CVV flips the card
    cardCvvInput.addEventListener('focus', () => {
        creditCardGraphic.classList.add('flipped');
    });
    
    cardCvvInput.addEventListener('blur', () => {
        creditCardGraphic.classList.remove('flipped');
    });

    cardCvvInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/[^0-9]/gi, '');
        e.target.value = value;
        cardCvvDisplay.innerText = value ? '•'.repeat(value.length) : '•••';
    });

    // 4. Name holder sync
    cardHolderInput.addEventListener('input', (e) => {
        let value = e.target.value.toUpperCase().replace(/[^a-zA-Z\s]/g, '');
        e.target.value = value;
        cardHolderDisplay.innerText = value || 'CARDHOLDER NAME';
    });
}

// Process the mock transaction with loading delay
async function processPayment(event) {
    event.preventDefault();
    
    const cardNum = cardNumberInput.value.replace(/\s/g, '');
    const expiry = cardExpiryInput.value;
    const cvv = cardCvvInput.value;
    const holder = cardHolderInput.value.trim();
    
    if (cardNum.length < 16) {
        alert('Введите корректный 16-значный номер карты.');
        return;
    }
    
    if (expiry.length < 5) {
        alert('Введите срок действия карты в формате ММ/ГГ.');
        return;
    }
    
    if (cvv.length < 3) {
        alert('Введите 3-значный код CVV.');
        return;
    }
    
    // Show visual payment processing loader
    paymentLoader.classList.add('active');
    
    // Simulate transaction processing delay (2 seconds)
    setTimeout(async () => {
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            const name = document.getElementById('customerName').value.trim();
            const phone = document.getElementById('customerPhone').value.trim();
            const email = document.getElementById('customerEmail').value.trim();
            
            const payload = {
                session_id: sessionId,
                name: name,
                phone: phone,
                email: email,
                seat_ids: selectedSeats.map(s => s.id)
            };
            
            const response = await fetch('/api/booking/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Произошла ошибка при бронировании.');
            }
            
            // Redirect to receipt confirmation screen
            window.location.href = `/ticket/${result.booking_id}/`;
            
        } catch (err) {
            paymentLoader.classList.remove('active');
            closePaymentModal();
            showError(err.message);
        }
    }, 2000);
}

// Help elements for showing/hiding error banners
function showError(message) {
    errorMessage.innerText = message;
    errorBanner.style.display = 'flex';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideError() {
    errorBanner.style.display = 'none';
}
