document.addEventListener('DOMContentLoaded', () => {
    const checkoutForm = document.getElementById('checkout-form');
    const itemQuantityInput = document.getElementById('item-quantity');
    const promoCodeInput = document.getElementById('promo-code');
    const claimPromoBtn = document.getElementById('claim-promo-btn');
    const statusMessage = document.getElementById('status-message');

    // Seeded Hard Bug 1: Uncaught JS Exception on boundary values (<= 0, negative, empty submit)
    checkoutForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const quantityRaw = itemQuantityInput.value.trim();
        const quantity = Number(quantityRaw);

        // Edge case failure: if quantity is empty, negative, or zero, throw uncaught exception
        if (!quantityRaw || isNaN(quantity) || quantity <= 0) {
            // Intentional uncaught runtime exception for fuzzing detection
            throw new Error(`Uncaught TypeError: Cannot calculate inventory tax for invalid quantity '${quantityRaw}'`);
        }

        // Normal success flow
        statusMessage.style.display = 'block';
        statusMessage.className = 'status-msg success';
        statusMessage.textContent = `Order placed successfully for ${quantity} item(s)!`;
    });

    // Seeded Hard Bug 2: Failed Network Request (HTTP 404)
    claimPromoBtn.addEventListener('click', async () => {
        statusMessage.style.display = 'block';
        statusMessage.className = 'status-msg';
        statusMessage.textContent = 'Fetching promo code...';

        try {
            // Hits an invalid 404 endpoint
            const res = await fetch('/api/claim-promo-discount?code=' + encodeURIComponent(promoCodeInput.value));
            if (!res.ok) {
                statusMessage.className = 'status-msg error';
                statusMessage.textContent = `Failed to fetch promo: HTTP ${res.status}`;
            } else {
                const data = await res.json();
                statusMessage.textContent = `Promo applied: ${data.discount}% OFF`;
            }
        } catch (err) {
            statusMessage.className = 'status-msg error';
            statusMessage.textContent = `Network Error: ${err.message}`;
        }
    });
});
