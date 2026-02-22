/**
 * DogeQuest - Main JavaScript
 * Pixel Retro Interactions & Animations
 */

// ============================================
// APP INITIALIZATION
// ============================================

const DogeQuest = {
    init() {
        this.initMenu();
        this.initAnimations();
        this.initToasts();
        this.hideLoading();
        console.log('🐕 DogeQuest initialized!');
    },

    // ============================================
    // SIDE MENU
    // ============================================
    
    initMenu() {
        const menuToggle = document.querySelector('.menu-toggle');
        const sideMenu = document.querySelector('.side-menu');
        const menuOverlay = document.querySelector('.menu-overlay');
        const mainContent = document.querySelector('.main-content');

        if (!menuToggle || !sideMenu) return;

        menuToggle.addEventListener('click', () => {
            this.toggleMenu();
        });

        if (menuOverlay) {
            menuOverlay.addEventListener('click', () => {
                this.closeMenu();
            });
        }

        // Close menu on link click
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', () => {
                this.playSound('click');
            });
        });
    },

    toggleMenu() {
        const sideMenu = document.querySelector('.side-menu');
        const menuToggle = document.querySelector('.menu-toggle');
        const menuOverlay = document.querySelector('.menu-overlay');
        const mainContent = document.querySelector('.main-content');

        const isOpen = sideMenu.classList.contains('open');

        if (isOpen) {
            this.closeMenu();
        } else {
            sideMenu.classList.add('open');
            menuToggle.classList.add('active');
            menuOverlay?.classList.add('visible');
            mainContent?.classList.add('menu-open');
            this.playSound('menuOpen');
        }
    },

    closeMenu() {
        const sideMenu = document.querySelector('.side-menu');
        const menuToggle = document.querySelector('.menu-toggle');
        const menuOverlay = document.querySelector('.menu-overlay');
        const mainContent = document.querySelector('.main-content');

        sideMenu?.classList.remove('open');
        menuToggle?.classList.remove('active');
        menuOverlay?.classList.remove('visible');
        mainContent?.classList.remove('menu-open');
    },

    // ============================================
    // LOADING SCREEN
    // ============================================

    hideLoading() {
        const loadingScreen = document.querySelector('.loading-screen');
        if (loadingScreen) {
            setTimeout(() => {
                loadingScreen.style.opacity = '0';
                setTimeout(() => {
                    loadingScreen.style.display = 'none';
                    this.animatePageIn();
                }, 300);
            }, 1500);
        } else {
            this.animatePageIn();
        }
    },

    animatePageIn() {
        const elements = document.querySelectorAll('.card, .task-item, .referral-item');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            setTimeout(() => {
                el.style.transition = 'all 0.1s steps(4)';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 50);
        });
    },

    // ============================================
    // ANIMATIONS
    // ============================================

    initAnimations() {
        // Button click animations
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (!btn.disabled) {
                    btn.classList.add('pixel-pop');
                    this.playSound('click');
                    setTimeout(() => btn.classList.remove('pixel-pop'), 200);
                }
            });
        });

        // Card hover effects
        document.querySelectorAll('.card, .task-item').forEach(card => {
            card.addEventListener('mouseenter', () => {
                this.playSound('hover');
            });
        });
    },

    // Pixel explosion effect
    createPixelExplosion(x, y, color = '#00aaff') {
        const container = document.createElement('div');
        container.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            pointer-events: none;
            z-index: 9999;
        `;

        for (let i = 0; i < 12; i++) {
            const pixel = document.createElement('div');
            const angle = (i / 12) * Math.PI * 2;
            const velocity = 50 + Math.random() * 50;
            const size = 4 + Math.random() * 4;

            pixel.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: ${color};
                animation: pixelExplode 0.4s steps(8) forwards;
                --dx: ${Math.cos(angle) * velocity}px;
                --dy: ${Math.sin(angle) * velocity}px;
            `;

            container.appendChild(pixel);
        }

        document.body.appendChild(container);

        // Add keyframes if not exists
        if (!document.querySelector('#pixel-explosion-styles')) {
            const style = document.createElement('style');
            style.id = 'pixel-explosion-styles';
            style.textContent = `
                @keyframes pixelExplode {
                    0% { transform: translate(0, 0); opacity: 1; }
                    100% { transform: translate(var(--dx), var(--dy)); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        setTimeout(() => container.remove(), 500);
    },

    // Coin rain effect
    createCoinRain(count = 10) {
        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                const coin = document.createElement('div');
                coin.innerHTML = '🪙';
                coin.style.cssText = `
                    position: fixed;
                    left: ${Math.random() * 100}vw;
                    top: -30px;
                    font-size: 24px;
                    z-index: 9999;
                    pointer-events: none;
                    animation: coinFall 1s steps(20) forwards;
                `;
                document.body.appendChild(coin);

                setTimeout(() => coin.remove(), 1000);
            }, i * 100);
        }

        // Add keyframes
        if (!document.querySelector('#coin-rain-styles')) {
            const style = document.createElement('style');
            style.id = 'coin-rain-styles';
            style.textContent = `
                @keyframes coinFall {
                    0% { transform: translateY(0) rotate(0deg); opacity: 1; }
                    100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    },

    // ============================================
    // TOAST NOTIFICATIONS
    // ============================================

    initToasts() {
        if (!document.querySelector('.toast-container')) {
            const container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
    },

    showToast(message, type = 'info', duration = 3000) {
        const container = document.querySelector('.toast-container');
        if (!container) return;

        const icons = {
            success: '✓',
            error: '✗',
            info: 'ℹ',
            warning: '⚠'
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
        `;

        container.appendChild(toast);
        this.playSound(type === 'success' ? 'success' : type === 'error' ? 'error' : 'notification');

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    // ============================================
    // SOUND EFFECTS (Optional)
    // ============================================

    sounds: {},
    soundEnabled: true,

    playSound(name) {
        if (!this.soundEnabled) return;
        
        // Placeholder for actual sound implementation
        // You can add Web Audio API sounds here
    },

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        return this.soundEnabled;
    },

    // ============================================
    // API CALLS
    // ============================================

    async api(endpoint, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(endpoint, options);
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('API Error:', error);
            this.showToast('Connection error', 'error');
            return { success: false, error: error.message };
        }
    },

    // ============================================
    // DAILY CHECK-IN
    // ============================================

    async claimCheckin() {
        const btn = document.querySelector('.checkin-btn');
        if (!btn || btn.disabled) return;

        btn.disabled = true;
        btn.innerHTML = '<span class="loading-dots">CLAIMING</span>';

        const result = await this.api('/api/checkin', 'POST');

        if (result.success) {
            // Success animation
            const rect = btn.getBoundingClientRect();
            this.createPixelExplosion(
                rect.left + rect.width / 2,
                rect.top + rect.height / 2,
                '#c9a227'
            );
            this.createCoinRain(8);

            btn.classList.add('claimed');
            btn.innerHTML = `✓ DAY ${result.streak} COMPLETE!`;

            this.showToast(`+${result.reward} DOGE earned!`, 'success');

            // Update balance display
            this.updateBalance(result.reward);

            // Update streak display
            const streakNum = document.querySelector('.streak-badge .number');
            if (streakNum) {
                streakNum.textContent = result.streak;
                streakNum.classList.add('pixel-pop');
            }
        } else {
            btn.disabled = false;
            btn.innerHTML = 'CLAIM REWARD';
            this.showToast(result.message || 'Already claimed today!', 'error');
        }
    },

    // ============================================
    // TASKS
    // ============================================

    async completeTask(taskId, url = null) {
        if (url) {
            // Open URL first
            window.open(url, '_blank');
            
            // Show verification message
            this.showToast('Verifying completion...', 'info');
            
            // Wait a bit before verifying
            await new Promise(resolve => setTimeout(resolve, 3000));
        }

        const result = await this.api('/api/task/complete', 'POST', { task_id: taskId });

        if (result.success) {
            const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
            if (taskItem) {
                taskItem.classList.add('completed');
                const status = taskItem.querySelector('.task-status');
                if (status) {
                    status.className = 'task-status completed';
                    status.textContent = 'DONE';
                }

                // Explosion effect
                const rect = taskItem.getBoundingClientRect();
                this.createPixelExplosion(
                    rect.left + rect.width / 2,
                    rect.top + rect.height / 2,
                    '#00ff66'
                );
            }

            this.showToast(result.message, 'success');
            this.updateBalance(result.reward);
        } else {
            if (result.requires_join) {
                this.showChannelModal(result.channel, taskId);
            } else {
                this.showToast(result.message || 'Could not complete task', 'error');
            }
        }
    },

    showChannelModal(channel, taskId) {
        const modal = document.querySelector('#channel-modal');
        if (modal) {
            modal.querySelector('.channel-name').textContent = channel;
            modal.dataset.taskId = taskId;
            this.openModal('channel-modal');
        }
    },

    // ============================================
    // REFERRALS
    // ============================================

    copyReferralLink() {
        const input = document.querySelector('.referral-link input');
        if (!input) return;

        input.select();
        document.execCommand('copy');

        // Create copy effect
        this.createPixelExplosion(
            window.innerWidth / 2,
            window.innerHeight / 2,
            '#00aaff'
        );

        this.showToast('Link copied!', 'success');
    },

    shareReferralLink() {
        const input = document.querySelector('.referral-link input');
        if (!input) return;

        const link = input.value;
        const text = '🐕 Join DogeQuest and earn free DOGE! Use my link:';

        if (navigator.share) {
            navigator.share({
                title: 'DogeQuest',
                text: text,
                url: link
            }).catch(() => {});
        } else if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.openTelegramLink(
                `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`
            );
        } else {
            window.open(
                `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`,
                '_blank'
            );
        }
    },

    // ============================================
    // WALLET / WITHDRAWAL
    // ============================================

    async requestWithdrawal() {
        const amountInput = document.querySelector('#withdraw-amount');
        const walletInput = document.querySelector('#withdraw-wallet');

        if (!amountInput || !walletInput) return;

        const amount = parseFloat(amountInput.value);
        const wallet = walletInput.value.trim();

        if (!amount || amount <= 0) {
            this.showToast('Enter a valid amount', 'error');
            return;
        }

        if (!wallet || !wallet.startsWith('D') || wallet.length < 30) {
            this.showToast('Enter a valid DOGE wallet address', 'error');
            return;
        }

        const result = await this.api('/api/withdraw', 'POST', {
            amount: amount,
            wallet_address: wallet
        });

        if (result.success) {
            this.closeModal('withdraw-modal');
            this.showToast('Withdrawal request submitted!', 'success');
            
            // Refresh page to show updated balance
            setTimeout(() => location.reload(), 1500);
        } else {
            this.showToast(result.message || 'Withdrawal failed', 'error');
        }
    },

    // ============================================
    // PROMO CODE
    // ============================================

    async redeemPromo() {
        const input = document.querySelector('#promo-code');
        if (!input) return;

        const code = input.value.trim();
        if (!code) {
            this.showToast('Enter a promo code', 'error');
            return;
        }

        const btn = document.querySelector('.promo-submit');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'REDEEMING...';
        }

        const result = await this.api('/api/promo/redeem', 'POST', { code });

        if (result.success) {
            this.createCoinRain(15);
            this.showToast(result.message, 'success');
            input.value = '';
            this.updateBalance(result.reward);
        } else {
            this.showToast(result.message || 'Invalid code', 'error');
        }

        if (btn) {
            btn.disabled = false;
            btn.textContent = 'REDEEM';
        }
    },

    // ============================================
    // MODALS
    // ============================================

    openModal(modalId) {
        const modal = document.querySelector(`#${modalId}`);
        if (modal) {
            modal.classList.add('active');
            this.playSound('modalOpen');
        }
    },

    closeModal(modalId) {
        const modal = document.querySelector(`#${modalId}`);
        if (modal) {
            modal.classList.remove('active');
        }
    },

    // ============================================
    // BALANCE UPDATE
    // ============================================

    updateBalance(addAmount) {
        const balanceEl = document.querySelector('.balance-amount');
        const headerBalance = document.querySelector('.header-balance .amount');

        [balanceEl, headerBalance].forEach(el => {
            if (el) {
                const current = parseFloat(el.textContent) || 0;
                const newBalance = current + parseFloat(addAmount);
                el.textContent = newBalance.toFixed(8).replace(/\.?0+$/, '');
                el.classList.add('pixel-pop');
                setTimeout(() => el.classList.remove('pixel-pop'), 200);
            }
        });
    },

    // ============================================
    // LEADERBOARD TABS
    // ============================================

    switchLeaderboard(tab) {
        // Update tab buttons
        document.querySelectorAll('.leaderboard-tab').forEach(t => {
            t.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');

        // Update content
        document.querySelectorAll('.leaderboard-content').forEach(c => {
            c.classList.add('hidden');
        });
        document.querySelector(`#leaderboard-${tab}`)?.classList.remove('hidden');

        this.playSound('click');
    }
};

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    DogeQuest.init();
});

// Expose to window for inline handlers
window.DogeQuest = DogeQuest;

// Telegram WebApp integration
if (window.Telegram?.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    
    // Apply Telegram theme colors if available
    if (tg.themeParams) {
        document.documentElement.style.setProperty('--tg-theme-bg', tg.themeParams.bg_color || '#0a0a0a');
    }
}
