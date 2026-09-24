document.addEventListener('DOMContentLoaded', () => {
    const checkoutForm = document.getElementById('checkout-form');
    const itemQuantityInput = document.getElementById('item-quantity');
    const promoCodeInput = document.getElementById('promo-code');
    const giftNoteInput = document.getElementById('gift-note');
    const shippingTierSelect = document.getElementById('shipping-tier');
    const claimPromoBtn = document.getElementById('claim-promo-btn');
    const calcShippingBtn = document.getElementById('calc-shipping-btn');
    const statusMessage = document.getElementById('status-message');

    // Form submission listener
    checkoutForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const quantityRaw = itemQuantityInput.value.trim();
        const quantity = Number(quantityRaw);
        const giftNote = giftNoteInput ? giftNoteInput.value : '';
        const shippingTier = shippingTierSelect ? shippingTierSelect.value : 'standard';

        // Seeded Hard Bug 1: Uncaught JS Exception on boundary values (<= 0, negative, empty submit)
        if (!quantityRaw || isNaN(quantity) || quantity <= 0) {
            throw new Error(`Uncaught TypeError: Cannot calculate inventory tax for invalid quantity '${quantityRaw}'`);
        }

        // Seeded Hard Bug 3: Script/HTML Injection syntax crash on gift note
        if (giftNote && (giftNote.includes('<') || giftNote.includes('>') || giftNote.includes(';') || giftNote.includes("'") || giftNote.includes('"'))) {
            throw new Error(`Uncaught DOMException: Failed to sanitize unsafe gift note payload: '${giftNote}'`);
        }

        // Seeded Hard Bug 5: Range/Capacity Overflow on express shipping
        if (quantity > 50 && shippingTier === 'express') {
            throw new Error(`Uncaught RangeError: Order quantity (${quantity}) exceeds maximum express courier cargo capacity (limit: 50)`);
        }

        // Normal success flow
        statusMessage.style.display = 'block';
        statusMessage.className = 'status-msg success';
        statusMessage.textContent = `Order placed successfully for ${quantity} item(s) via ${shippingTier}!`;
    });

    // Seeded Hard Bug 2: Failed Network Request (HTTP 404)
    claimPromoBtn.addEventListener('click', async () => {
        statusMessage.style.display = 'block';
        statusMessage.className = 'status-msg';
        statusMessage.textContent = 'Fetching promo code...';

        try {
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

    // Seeded Hard Bug 4: Broken Shipping Rate Service (HTTP 404/500)
    if (calcShippingBtn) {
        calcShippingBtn.addEventListener('click', async () => {
            statusMessage.style.display = 'block';
            statusMessage.className = 'status-msg';
            statusMessage.textContent = 'Calculating live courier rates...';

            try {
                const res = await fetch('/api/v1/shipping/rates?tier=' + encodeURIComponent(shippingTierSelect ? shippingTierSelect.value : 'standard'));
                if (!res.ok) {
                    statusMessage.className = 'status-msg error';
                    statusMessage.textContent = `Shipping service unavailable: HTTP ${res.status}`;
                }
            } catch (err) {
                statusMessage.className = 'status-msg error';
                statusMessage.textContent = `Service error: ${err.message}`;
            }
        });
    }
});
