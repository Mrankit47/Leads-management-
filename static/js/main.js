// Main JavaScript file for LeadGen Tracker

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Form UX enhancement:
    // - Don't block submission with custom JS validation (let browser + server handle it)
    // - Only show "Processing..." after a valid submit attempt
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // Highlight empty required fields if browser says invalid
            if (!form.checkValidity()) {
                const requiredFields = form.querySelectorAll('[required]');
                requiredFields.forEach(function(field) {
                    if (!String(field.value || '').trim()) {
                        field.style.borderColor = '#ef4444';
                    } else {
                        field.style.borderColor = '';
                    }
                });
                return; // allow browser to show validation UI; don't disable button
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.textContent;
                submitBtn.textContent = 'Processing...';
            }
        });
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Note: submit button loading state is handled in the form submit handler above.

    // WhatsApp-like Chatbot (public inquiry)
    const fab = document.getElementById('chatbot-fab');
    const win = document.getElementById('chatbot-window');
    const closeBtn = document.getElementById('chatbot-close');
    const msgs = document.getElementById('chatbot-messages');
    const input = document.getElementById('chatbot-input');
    const send = document.getElementById('chatbot-send');

    if (fab && win && closeBtn && msgs && input && send) {
        const state = {
            step: 0,
            data: {
                name: '',
                email: '',
                phone: '',
                company: '',
                product_name: '',
                message: '',
            },
            busy: false,
        };

        const steps = [
            { key: null, prompt: "Hi! I can help you submit an inquiry.\nWhat’s your full name?" },
            { key: 'name', prompt: "Great. What’s your email?" },
            { key: 'email', prompt: "Thanks. What’s your phone number?" },
            { key: 'phone', prompt: "Company name? (optional — type '-' to skip)" },
            { key: 'company', prompt: "Which product/service are you interested in?" },
            { key: 'product_name', prompt: "Tell me your requirements / inquiry details." },
            { key: 'message', prompt: "Perfect — submit now? Type 'yes' to submit or 'no' to cancel." },
        ];

        function addBubble(text, who) {
            const div = document.createElement('div');
            div.className = 'chatbot-bubble ' + who;
            div.textContent = text;
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        }

        function getCookie(name) {
            const value = '; ' + document.cookie;
            const parts = value.split('; ' + name + '=');
            if (parts.length === 2) return parts.pop().split(';').shift();
            return '';
        }

        function openChat() {
            win.classList.remove('chatbot-hidden');
            if (!msgs.dataset.started) {
                msgs.dataset.started = '1';
                addBubble(steps[0].prompt, 'bot');
            }
            setTimeout(() => input.focus(), 50);
        }

        function closeChat() {
            win.classList.add('chatbot-hidden');
        }

        async function submitChatbot() {
            const url = window.LEADGEN_CHATBOT_SUBMIT_URL || '/chatbot/submit/';
            const csrf = getCookie('csrftoken');
            state.busy = true;
            send.disabled = true;
            input.disabled = true;

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrf,
                    },
                    body: JSON.stringify(state.data),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok || !data.ok) {
                    addBubble("Sorry — I couldn’t submit that. " + (data.error || 'Please try again.'), 'bot');
                    return;
                }
                addBubble(`Done! Your inquiry is submitted.\nTicket #${data.ticket_id} created.`, 'bot');
            } catch (e) {
                addBubble("Network error while submitting. Please try again.", 'bot');
            } finally {
                state.busy = false;
                send.disabled = false;
                input.disabled = false;
            }
        }

        function handleUserMessage(text) {
            if (state.busy) return;
            const t = (text || '').trim();
            if (!t) return;

            addBubble(t, 'user');

            // Step 0 just asked name (stored on next step definition)
            if (state.step < steps.length - 1) {
                const nextStep = steps[state.step + 1];
                const currentKey = nextStep.key;
                if (currentKey) {
                    if (currentKey === 'company' && t === '-') {
                        state.data.company = '';
                    } else {
                        state.data[currentKey] = t;
                    }
                }
                state.step += 1;
                addBubble(steps[state.step].prompt, 'bot');
                return;
            }

            // Confirmation step
            if (state.step === steps.length - 1) {
                const ans = t.toLowerCase();
                if (ans === 'yes' || ans === 'y') {
                    submitChatbot();
                } else if (ans === 'no' || ans === 'n') {
                    addBubble("No problem. If you want, you can type 'restart' to start over.", 'bot');
                } else if (ans === 'restart') {
                    msgs.innerHTML = '';
                    msgs.dataset.started = '';
                    state.step = 0;
                    state.data = { name: '', email: '', phone: '', company: '', product_name: '', message: '' };
                    addBubble(steps[0].prompt, 'bot');
                } else {
                    addBubble("Please type 'yes' to submit or 'no' to cancel.", 'bot');
                }
            }
        }

        fab.addEventListener('click', openChat);
        closeBtn.addEventListener('click', closeChat);
        send.addEventListener('click', function() {
            const value = input.value;
            input.value = '';
            handleUserMessage(value);
        });
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                send.click();
            }
        });
    }
});
