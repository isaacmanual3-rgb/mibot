/* ══════════════════════════════════════════════
   APPLE FARM GAME — apple_game.js
   ══════════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── State ──────────────────────────────── */
    const state = {
        apples: 0,
        level: 1,
        applesPerSecond: 0,
        applesPerHour: 0,
        lastSync: Date.now(),
        trees: [],          // tree definitions from server
        userTrees: {},      // treeId -> count owned
        secondsToNext: 0,
    };

    let syncInterval = null;
    let tickInterval = null;
    let selectedTree = null;

    /* ── Island node positions (% of image W/H)  */
    // Positions mapped to the 5 islands in tavukaltlik.webp
    const NODE_POSITIONS = [
        { x: 22, y: 11 },   // island 1 – top left
        { x: 67, y: 18 },   // island 2 – top right
        { x: 20, y: 37 },   // island 3 – middle left
        { x: 73, y: 57 },   // island 4 – mid right
        { x: 22, y: 75 },   // island 5 – bottom left
    ];

    /* ── DOM refs ────────────────────────────── */
    const $appleCount     = document.getElementById('appleCount');
    const $applesPerHour  = document.getElementById('applesPerHour');
    const $userLevel      = document.getElementById('userLevel');
    const $nextTimer      = document.getElementById('nextAppleTimer');
    const $treeCards      = document.getElementById('treeCards');
    const $treeNodes      = document.getElementById('treeNodes');
    const $unlockModal    = document.getElementById('unlockModal');
    const $modalClose     = document.getElementById('modalClose');
    const $modalIcon      = document.getElementById('modalIcon');
    const $modalTitle     = document.getElementById('modalTitle');
    const $modalStats     = document.getElementById('modalStats');
    const $modalBuyBtn    = document.getElementById('modalBuyBtn');
    const $modalNote      = document.getElementById('modalNote');

    /* ── Toast helper (reuse base.html's or create own) ─ */
    function showToast(msg, type = 'info') {
        const tc = document.getElementById('toastContainer');
        if (!tc) return;
        const t = document.createElement('div');
        t.className = `toast toast-${type}`;
        t.textContent = msg;
        tc.appendChild(t);
        requestAnimationFrame(() => t.classList.add('visible'));
        setTimeout(() => {
            t.classList.remove('visible');
            setTimeout(() => t.remove(), 400);
        }, 3000);
    }

    /* ── Number formatting ─────────────────── */
    function fmt(n) {
        n = Math.floor(n);
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
        if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
        return n.toString();
    }

    /* ── Update display ──────────────────────── */
    function updateDisplay() {
        $appleCount.textContent    = fmt(state.apples);
        $applesPerHour.textContent = fmt(state.applesPerHour);
        $userLevel.textContent     = state.level;

        if (state.applesPerSecond > 0) {
            const secs = Math.max(0, Math.ceil(1 / state.applesPerSecond));
            if (secs < 60) {
                $nextTimer.textContent = `Siguiente manzana en: ${secs}s`;
            } else {
                const m = Math.floor(secs / 60), s = secs % 60;
                $nextTimer.textContent = `Siguiente manzana en: ${m}m ${s}s`;
            }
        } else {
            $nextTimer.textContent = '🌱 Compra un árbol para empezar';
        }
    }

    /* ── Local tick (smooth counter) ─────────── */
    function startTick() {
        if (tickInterval) clearInterval(tickInterval);
        tickInterval = setInterval(() => {
            if (state.applesPerSecond > 0) {
                state.apples += state.applesPerSecond;
                updateDisplay();
            }
        }, 1000);
    }

    /* ── Floating apple animation ─────────────── */
    function spawnAppleParticle() {
        const p = document.createElement('div');
        p.className = 'apple-float';
        p.textContent = '🍎';
        const x = Math.random() * (window.innerWidth * 0.6) + window.innerWidth * 0.2;
        p.style.left = x + 'px';
        p.style.top  = (window.innerHeight * 0.3) + 'px';
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 1300);
    }

    /* ── Build map node overlays ──────────────── */
    function buildMapNodes() {
        $treeNodes.innerHTML = '';
        state.trees.forEach((tree, idx) => {
            const pos = NODE_POSITIONS[idx] || { x: 50, y: 50 };
            const owned = state.userTrees[tree.id] || 0;
            const unlocked = state.level >= tree.level_required;

            const node = document.createElement('div');
            node.className = 'tree-node';
            node.style.left = pos.x + '%';
            node.style.top  = pos.y + '%';

            const badge = document.createElement('div');
            badge.className = 'tree-node-badge ' + (unlocked ? 'unlocked' : 'locked');
            badge.textContent = unlocked ? tree.emoji : '🔒';
            badge.title = tree.name;

            node.appendChild(badge);
            node.addEventListener('click', () => openModal(tree));
            $treeNodes.appendChild(node);
        });
    }

    /* ── Build tree cards ─────────────────────── */
    function buildTreeCards() {
        $treeCards.innerHTML = '';
        state.trees.forEach(tree => {
            const owned    = state.userTrees[tree.id] || 0;
            const unlocked = state.level >= tree.level_required;

            const card = document.createElement('div');
            card.className = 'tree-card ' + (unlocked ? 'unlocked' : 'locked');

            if (unlocked) {
                card.innerHTML = `
                    <div class="tree-card-icon">${tree.emoji}</div>
                    <div class="tree-card-info">
                        <div class="tree-card-name">${tree.name}</div>
                        <div class="tree-card-sub">
                            <span>🍎 ${tree.apples_per_hour}/h</span>
                            <span>💰 ${fmt(tree.cost)} manzanas</span>
                        </div>
                    </div>
                    <div class="tree-card-right">
                        <span class="tree-card-owned">Tienes: ${owned}</span>
                        <button class="btn-unlock" data-id="${tree.id}">Comprar</button>
                    </div>
                `;
                card.querySelector('.btn-unlock').addEventListener('click', (e) => {
                    e.stopPropagation();
                    openModal(tree);
                });
            } else {
                card.innerHTML = `
                    <div class="tree-card-icon" style="filter:grayscale(1)">${tree.emoji}</div>
                    <div class="tree-card-info">
                        <div class="tree-card-name" style="color:#666">${tree.name}</div>
                        <div class="tree-card-sub"><span style="color:#555">Nivel ${tree.level_required} requerido</span></div>
                    </div>
                    <div class="tree-card-right">
                        <span class="lock-badge">🔒</span>
                        <span class="level-req">Lv.${tree.level_required}</span>
                    </div>
                `;
            }

            card.addEventListener('click', () => openModal(tree));
            $treeCards.appendChild(card);
        });
    }

    /* ── Modal ────────────────────────────────── */
    function openModal(tree) {
        selectedTree = tree;
        const owned    = state.userTrees[tree.id] || 0;
        const unlocked = state.level >= tree.level_required;
        const canAfford = state.apples >= tree.cost;

        $modalIcon.textContent  = tree.emoji;
        $modalTitle.textContent = tree.name;

        $modalStats.innerHTML = `
            <div class="modal-stat">
                <span class="modal-stat-label">🍎 Por hora</span>
                <span class="modal-stat-val">${tree.apples_per_hour}</span>
            </div>
            <div class="modal-stat">
                <span class="modal-stat-label">💰 Costo</span>
                <span class="modal-stat-val">${fmt(tree.cost)}</span>
            </div>
            <div class="modal-stat">
                <span class="modal-stat-label">📦 Total comprados</span>
                <span class="modal-stat-val">${owned}</span>
            </div>
            <div class="modal-stat">
                <span class="modal-stat-label">🏅 Nivel req.</span>
                <span class="modal-stat-val">${tree.level_required}</span>
            </div>
        `;

        if (!unlocked) {
            $modalBuyBtn.disabled = true;
            $modalBuyBtn.textContent = `🔒 Nivel ${tree.level_required} requerido`;
            $modalNote.textContent = `Sube al nivel ${tree.level_required} para desbloquear.`;
        } else if (!canAfford) {
            $modalBuyBtn.disabled = true;
            $modalBuyBtn.textContent = `Necesitas ${fmt(tree.cost - state.apples)} más 🍎`;
            $modalNote.textContent = 'Sigue produciendo manzanas.';
        } else {
            $modalBuyBtn.disabled = false;
            $modalBuyBtn.textContent = `🌳 Comprar por ${fmt(tree.cost)} 🍎`;
            $modalNote.textContent = `+${tree.apples_per_hour} manzanas/h al comprar.`;
        }

        $unlockModal.style.display = 'flex';
    }

    function closeModal() {
        $unlockModal.style.display = 'none';
        selectedTree = null;
    }

    $modalClose.addEventListener('click', closeModal);
    $unlockModal.addEventListener('click', e => { if (e.target === $unlockModal) closeModal(); });

    /* ── Buy tree ─────────────────────────────── */
    $modalBuyBtn.addEventListener('click', async () => {
        if (!selectedTree || $modalBuyBtn.disabled) return;
        $modalBuyBtn.disabled = true;
        $modalBuyBtn.textContent = '⏳ Comprando...';

        try {
            const res = await fetch('/api/buy_tree', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ tree_id: selectedTree.id })
            });
            const data = await res.json();

            if (data.success) {
                state.apples = data.apples;
                state.level  = data.level;
                state.applesPerHour = data.apples_per_hour;
                state.applesPerSecond = data.apples_per_hour / 3600;
                state.userTrees[selectedTree.id] = (state.userTrees[selectedTree.id] || 0) + 1;
                updateDisplay();
                buildMapNodes();
                buildTreeCards();
                spawnAppleParticle();
                showToast(`¡${selectedTree.name} comprado! 🌳`, 'success');
                closeModal();
            } else {
                showToast(data.error || 'Error al comprar', 'error');
                openModal(selectedTree); // re-open to refresh state
            }
        } catch (err) {
            showToast('Error de conexión', 'error');
        }
    });

    /* ── Sync with server ─────────────────────── */
    async function syncWithServer() {
        try {
            const res = await fetch('/api/update_apples', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            });
            const data = await res.json();

            if (data.success) {
                state.apples         = data.apples;
                state.level          = data.level;
                state.applesPerHour  = data.apples_per_hour;
                state.applesPerSecond = data.apples_per_hour / 3600;

                if (data.trees) {
                    state.trees = data.trees;
                    buildMapNodes();
                    buildTreeCards();
                }
                if (data.user_trees) {
                    state.userTrees = data.user_trees;
                    buildMapNodes();
                    buildTreeCards();
                }

                updateDisplay();
                startTick();
            }
        } catch (e) {
            // silent fail – keep local tick running
        }
    }

    /* ── Init ────────────────────────────────── */
    function init() {
        // Initial values from template
        state.apples = parseInt($appleCount.textContent) || 0;
        state.level  = parseInt($userLevel.textContent) || 1;
        updateDisplay();
        syncWithServer();
        // Sync every 30s
        syncInterval = setInterval(syncWithServer, 30_000);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
